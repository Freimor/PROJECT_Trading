"""One-off wiki URL checker (HEAD requests)."""
from __future__ import annotations

import re
import ssl
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2] / "trading_wiki"
URL_RE = re.compile(r"https?://[^\s\)\]>\"]+")


def check_url(url: str) -> int | str:
    url = url.rstrip(".,;")
    try:
        req = urllib.request.Request(
            url,
            method="HEAD",
            headers={"User-Agent": "PROJECT_Trading-linkcheck/1.0"},
        )
        with urllib.request.urlopen(req, timeout=12, context=ssl.create_default_context()) as resp:
            return resp.status
    except urllib.error.HTTPError as exc:
        return exc.code
    except Exception as exc:  # noqa: BLE001
        return str(exc)


def main() -> None:
    checked: dict[str, int | str] = {}
    broken: list[tuple[int | str, str, list[str]]] = []
    ok_codes = {200, 202, 301, 302, 303, 307, 308, 403}

    for path in sorted(ROOT.rglob("*.md")):
        text = path.read_text(encoding="utf-8", errors="ignore")
        rel = str(path.relative_to(ROOT))
        for raw in sorted(set(URL_RE.findall(text))):
            url = raw.rstrip(".,;")
            if url not in checked:
                checked[url] = check_url(url)
            code = checked[url]
            if code not in ok_codes:
                for item in broken:
                    if item[1] == url:
                        item[2].append(rel)
                        break
                else:
                    broken.append((code, url, [rel]))

    print(f"TOTAL_URLS {len(checked)}")
    print(f"BROKEN {len(broken)}")
    for code, url, files in sorted(broken, key=lambda x: str(x[0])):
        print(f"{code}\t{url}\t{', '.join(files[:3])}{'...' if len(files)>3 else ''}")


if __name__ == "__main__":
    main()
