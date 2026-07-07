"""proxy-gateway entrypoint — sing-box + awesome-vpn urltest."""

from __future__ import annotations

import logging
import os
import subprocess
import sys
import time

from proxy_gateway.awesome_vpn import fetch_singbox_outbounds
from proxy_gateway.singbox_config import write_config

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

CONFIG_PATH = os.environ.get("SINGBOX_CONFIG_PATH", "/tmp/sing-box.json")
SINGBOX_BIN = os.environ.get("SINGBOX_BIN", "sing-box")
REFRESH_SEC = int(os.environ.get("PROXY_GATEWAY_REFRESH_SEC", "3600"))


def run_once() -> int:
    logger.info("Fetching awesome-vpn outbounds…")
    outbounds = fetch_singbox_outbounds()
    logger.info("Loaded %d nodes, building sing-box config", len(outbounds))
    write_config(CONFIG_PATH, outbounds=outbounds)
    logger.info("Starting sing-box on port %s", os.environ.get("PROXY_GATEWAY_PORT", "17890"))
    proc = subprocess.Popen([SINGBOX_BIN, "run", "-c", CONFIG_PATH])
    try:
        return proc.wait()
    except KeyboardInterrupt:
        proc.terminate()
        return 0


def main() -> None:
    while True:
        code = run_once()
        logger.warning("sing-box exited with code %s, restart in 10s", code)
        time.sleep(10)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        sys.exit(0)
