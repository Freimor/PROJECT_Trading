"""One-shot bootstrap after audit — import workflows, sync, ollama, harness, paper test."""

from __future__ import annotations

import json
import sys


def main() -> int:
    report: dict = {"steps": []}

    def step(name: str, fn):
        try:
            result = fn()
            report["steps"].append({"name": name, "status": "ok", "result": result})
            print(f"[ok] {name}")
        except Exception as exc:
            report["steps"].append({"name": name, "status": "error", "message": str(exc)})
            print(f"[err] {name}: {exc}")

    step("import_workflows", lambda: __import__("n8n_service", fromlist=["import_all_workflows"]).import_all_workflows())
    step("sync_crypto", lambda: __import__("automation_control_service", fromlist=["sync_market_workflows"]).sync_market_workflows("crypto"))
    step("sync_securities", lambda: __import__("automation_control_service", fromlist=["sync_market_workflows"]).sync_market_workflows("securities"))
    step(
        "ollama_ensure",
        lambda: __import__("ollama_manager_service", fromlist=["ensure_required_models"]).ensure_required_models(
            operator="bootstrap", background=True
        ),
    )
    step(
        "neuratrade_fixtures",
        lambda: __import__("neuratrade_harness", fromlist=["run_harness_cycle"]).run_harness_cycle(
            mode="fixtures", equity=10000.0
        ),
    )
    step(
        "paper_run_once",
        lambda: __import__("automation_control_service", fromlist=["run_workflow_once"]).run_workflow_once(
            "crypto", "crypto-signal-paper", operator="bootstrap"
        ),
    )

    print(json.dumps(report, ensure_ascii=False, indent=2, default=str))
    return 0


if __name__ == "__main__":
    sys.exit(main())
