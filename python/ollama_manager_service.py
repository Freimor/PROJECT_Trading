"""Ollama model lifecycle — list, pull, delete, bootstrap on new host."""

from __future__ import annotations

import json
import threading
import time
import uuid
from pathlib import Path
from typing import Any

import httpx
import psutil

from config_loader import load_config
from llm_client import list_ollama_models, ollama_host
from runtime_settings import get_runtime_value, set_runtime_value

_PULL_JOBS: dict[str, dict[str, Any]] = {}
_PULL_LOCK = threading.Lock()
_BOOTSTRAP_KEY = "ollama_bootstrap_last"


def _cfg() -> dict[str, Any]:
    try:
        return load_config("ollama_models")
    except FileNotFoundError:
        return {"bootstrap_on_startup": True, "pull_timeout_sec": 7200}


def normalize_model_tag(name: str) -> str:
    return name.split("@")[0].strip().lower()


def model_is_installed(required: str, installed: set[str]) -> bool:
    req = normalize_model_tag(required)
    for name in installed:
        if normalize_model_tag(name) == req:
            return True
    return False


def collect_required_models() -> list[dict[str, Any]]:
    """Derive required models from trading configs + ollama_models.yaml."""
    seen: set[str] = set()
    out: list[dict[str, Any]] = []

    def add(name: str | None, role: str, *, optional: bool = False) -> None:
        if not name or not str(name).strip():
            return
        tag = str(name).strip()
        key = normalize_model_tag(tag)
        if key in seen:
            return
        seen.add(key)
        out.append({"name": tag, "role": role, "optional": optional})

    crypto = load_config("crypto_config")
    add(crypto.get("ollama_model"), "crypto_swing")

    try:
        scalp = load_config("crypto_scalp_hybrid")
        add(scalp.get("ollama_model_fast"), "scalp_fast")
        add(scalp.get("ollama_model_fallback"), "scalp_fallback", optional=True)
    except FileNotFoundError:
        pass

    sec = load_config("securities_config")
    swing = sec.get("swing_signals") or {}
    add(swing.get("ollama_model"), "moex_swing")

    try:
        news = load_config("news_alerts")
        add(news.get("ollama_model"), "news_alerts", optional=True)
    except FileNotFoundError:
        pass

    try:
        nt = load_config("neuratrade_config")
        for model in nt.get("models") or []:
            add(str(model), "neuratrade_benchmark", optional=True)
    except FileNotFoundError:
        pass

    cfg = _cfg()
    for item in cfg.get("extra_required") or []:
        if isinstance(item, str):
            add(item, "extra")
        elif isinstance(item, dict):
            add(item.get("name"), item.get("role", "extra"), optional=bool(item.get("optional")))

    return out


def get_models_status() -> dict[str, Any]:
    """Required vs installed models for UI and bootstrap."""
    required = collect_required_models()
    tags = list_ollama_models()
    installed_names = {
        str(m.get("name"))
        for m in (tags.get("models") or [])
        if m.get("name")
    }
    installed_by_norm = {normalize_model_tag(n): n for n in installed_names}

    rows: list[dict[str, Any]] = []
    missing_required: list[str] = []
    for req in required:
        norm = normalize_model_tag(req["name"])
        inst = installed_by_norm.get(norm)
        row = {
            **req,
            "installed": inst is not None,
            "installed_name": inst,
        }
        rows.append(row)
        if not row["installed"] and not req.get("optional"):
            missing_required.append(req["name"])

    protected = {normalize_model_tag(x) for x in (_cfg().get("protected") or [])}
    extra_installed = [
        n
        for n in sorted(installed_names)
        if normalize_model_tag(n) not in {normalize_model_tag(r["name"]) for r in required}
    ]

    disk = psutil.disk_usage("/")
    return {
        "status": "ok",
        "ollama_host": ollama_host(),
        "ollama": tags,
        "required": rows,
        "missing_required": missing_required,
        "extra_installed": extra_installed,
        "protected": sorted(protected),
        "disk_free_gb": round(disk.free / (1024**3), 2),
        "bootstrap_last": get_runtime_value(_BOOTSTRAP_KEY),
    }


def _update_pull_job(job_id: str, **fields: Any) -> None:
    with _PULL_LOCK:
        job = _PULL_JOBS.get(job_id, {})
        job.update(fields)
        _PULL_JOBS[job_id] = job
        set_runtime_value(f"ollama_pull:{job_id}", job, updated_by="ollama_manager")


def get_pull_job(job_id: str) -> dict[str, Any] | None:
    with _PULL_LOCK:
        if job_id in _PULL_JOBS:
            return dict(_PULL_JOBS[job_id])
    val = get_runtime_value(f"ollama_pull:{job_id}")
    return val if isinstance(val, dict) else None


def list_pull_jobs(limit: int = 10) -> list[dict[str, Any]]:
    with _PULL_LOCK:
        jobs = sorted(_PULL_JOBS.values(), key=lambda j: j.get("started_at", ""), reverse=True)
    return jobs[:limit]


def pull_ollama_model(
    model: str,
    *,
    operator: str = "api",
    background: bool = False,
) -> dict[str, Any]:
    """Download model via Ollama /api/pull (streaming progress)."""
    model = model.strip()
    if not model:
        raise ValueError("model_required")

    job_id = str(uuid.uuid4())
    job = {
        "job_id": job_id,
        "model": model,
        "status": "queued",
        "progress_pct": 0,
        "message": "",
        "operator": operator,
        "started_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "finished_at": None,
    }
    with _PULL_LOCK:
        _PULL_JOBS[job_id] = job

    if background:
        threading.Thread(
            target=_pull_worker,
            args=(job_id, model),
            daemon=True,
            name=f"ollama-pull-{normalize_model_tag(model)}",
        ).start()
        return {"status": "ok", "job_id": job_id, "model": model, "async": True}

    _pull_worker(job_id, model)
    result = get_pull_job(job_id) or job
    return {"status": "ok", "job_id": job_id, "model": model, "result": result}


def _pull_worker(job_id: str, model: str) -> None:
    cfg = _cfg()
    timeout = float(cfg.get("pull_timeout_sec", 7200))
    _update_pull_job(job_id, status="pulling", message="pulling manifest")
    try:
        with httpx.Client(timeout=timeout) as client:
            with client.stream(
                "POST",
                f"{ollama_host()}/api/pull",
                json={"name": model, "stream": True},
            ) as resp:
                if resp.status_code != 200:
                    _update_pull_job(
                        job_id,
                        status="error",
                        message=resp.text[:300],
                        finished_at=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                    )
                    return
                for line in resp.iter_lines():
                    if not line:
                        continue
                    try:
                        chunk = json.loads(line)
                    except json.JSONDecodeError:
                        continue
                    status = str(chunk.get("status", ""))
                    total = int(chunk.get("total") or 0)
                    completed = int(chunk.get("completed") or 0)
                    pct = int(completed / total * 100) if total > 0 else None
                    fields: dict[str, Any] = {"message": status}
                    if pct is not None:
                        fields["progress_pct"] = pct
                    if status == "success":
                        fields["status"] = "success"
                        fields["progress_pct"] = 100
                        fields["finished_at"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
                    elif status.endswith("error") or chunk.get("error"):
                        fields["status"] = "error"
                        fields["message"] = str(chunk.get("error") or status)
                        fields["finished_at"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
                    else:
                        fields["status"] = "pulling"
                    _update_pull_job(job_id, **fields)
                    if fields.get("status") in ("success", "error"):
                        break
        job = get_pull_job(job_id) or {}
        if job.get("status") not in ("success", "error"):
            _update_pull_job(
                job_id,
                status="success",
                progress_pct=100,
                message="done",
                finished_at=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            )
        try:
            from activity_feed_service import log_system_activity

            final = get_pull_job(job_id) or {}
            level = "success" if final.get("status") == "success" else "warn"
            log_system_activity(
                f"Ollama pull {model}: {final.get('status', '?')}",
                category="system",
                level=level,
                payload={"model": model, "job_id": job_id},
            )
        except Exception:
            pass
    except Exception as exc:
        _update_pull_job(
            job_id,
            status="error",
            message=str(exc)[:300],
            finished_at=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        )


def delete_ollama_model(
    model: str,
    *,
    operator: str = "api",
    force: bool = False,
) -> dict[str, Any]:
    """Remove model from Ollama disk. Protected models need force=true."""
    model = model.strip()
    if not model:
        raise ValueError("model_required")

    protected = {normalize_model_tag(x) for x in (_cfg().get("protected") or [])}
    norm = normalize_model_tag(model)
    if norm in protected and not force:
        raise ValueError(f"model_protected: {model}")

    required_norms = {
        normalize_model_tag(r["name"])
        for r in collect_required_models()
        if not r.get("optional")
    }
    if norm in required_norms and not force:
        raise ValueError(f"model_required_by_config: {model}")

    try:
        with httpx.Client(timeout=120.0) as client:
            resp = client.post(
                f"{ollama_host()}/api/delete",
                json={"name": model},
            )
        if resp.status_code != 200:
            return {
                "status": "error",
                "model": model,
                "http_status": resp.status_code,
                "message": resp.text[:300],
            }
        try:
            from activity_feed_service import log_system_activity

            log_system_activity(
                f"Ollama delete: {model}",
                category="system",
                level="warn",
                payload={"model": model, "operator": operator, "force": force},
            )
        except Exception:
            pass
        return {"status": "ok", "model": model, "deleted": True}
    except httpx.HTTPError as exc:
        return {"status": "error", "model": model, "message": str(exc)}


def ensure_required_models(
    *,
    operator: str = "bootstrap",
    background: bool = True,
    include_optional: bool = False,
) -> dict[str, Any]:
    """Pull all missing required (and optionally optional) models."""
    cfg = _cfg()
    min_disk = float(cfg.get("min_disk_free_gb", 8))
    status = get_models_status()
    if status.get("disk_free_gb", 0) < min_disk:
        return {
            "status": "skipped",
            "reason": "low_disk",
            "disk_free_gb": status.get("disk_free_gb"),
            "min_disk_free_gb": min_disk,
        }

    to_pull: list[str] = list(status.get("missing_required") or [])
    if include_optional:
        for row in status.get("required") or []:
            if row.get("optional") and not row.get("installed"):
                to_pull.append(row["name"])

    if not to_pull:
        return {"status": "ok", "message": "all_required_present", "jobs": []}

    jobs: list[dict[str, Any]] = []
    for model in to_pull:
        result = pull_ollama_model(model, operator=operator, background=background)
        jobs.append(result)

    set_runtime_value(
        _BOOTSTRAP_KEY,
        {"at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "models": to_pull},
        updated_by=operator,
    )
    return {"status": "ok", "pulled": to_pull, "jobs": jobs}


def bootstrap_ollama_models_background() -> None:
    """Called from API lifespan — non-blocking pull of missing models."""
    cfg = _cfg()
    if not cfg.get("bootstrap_on_startup", True):
        return

    def _run() -> None:
        time.sleep(3)
        try:
            ensure_required_models(operator="startup", background=True)
        except Exception as exc:
            try:
                from activity_feed_service import log_system_activity

                log_system_activity(
                    f"Ollama bootstrap: {exc}",
                    category="system",
                    level="warn",
                )
            except Exception:
                pass

    threading.Thread(target=_run, daemon=True, name="ollama-bootstrap").start()
