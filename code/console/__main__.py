"""python -m console [--port 8765]  — serves on 127.0.0.1 only (reach it through SSH port forwarding)."""
import argparse
import threading

import uvicorn


def main():
    ap = argparse.ArgumentParser(prog="console")
    ap.add_argument("--port", type=int, default=8765)
    a = ap.parse_args()
    from . import data as D

    def warm():                      # build the scenario and sample indexes in the background
        try:
            D.SCEN.get()
            D.USAGE.get()
        except Exception:            # noqa: BLE001
            pass
    threading.Thread(target=warm, daemon=True).start()
    uvicorn.run("console.app:app", host="127.0.0.1", port=a.port, log_level="warning")


if __name__ == "__main__":
    main()
