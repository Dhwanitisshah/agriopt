"""Headless check: does the Streamlit app render all tabs without exception,
in both normal and risk-aware mode? Run as a SEPARATE PROCESS (not imported
in-process by pytest) -- streamlit.testing.v1.AppTest spins up its own
background script-runner thread, and on this environment, running an
AppTest session followed by further direct pymoo/NSGA calls in the SAME
process was observed to deadlock (a real thread-join hang, not a flaky
timing issue -- reproduced repeatedly). Isolating AppTest into its own
process avoids that entirely; tests/test_app_smoke.py invokes this via
subprocess, the same pattern already used for scripts/smoke_e2e.py.
"""
from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")


def main() -> int:
    from streamlit.testing.v1 import AppTest

    at = AppTest.from_file(str(REPO_ROOT / "app" / "streamlit_app.py"))

    at.run(timeout=90)
    if at.exception:
        print(f"FAIL: normal mode raised: {list(at.exception)}")
        return 1
    if len(at.tabs) != 6:
        print(f"FAIL: expected 6 tabs in normal mode, got {len(at.tabs)}")
        return 1
    print("OK: normal mode, 6 tabs, no exceptions")

    at.toggle[0].set_value(True).run(timeout=90)
    if at.exception:
        print(f"FAIL: risk-aware mode raised: {list(at.exception)}")
        return 1
    if len(at.tabs) != 6:
        print(f"FAIL: expected 6 tabs in risk-aware mode, got {len(at.tabs)}")
        return 1
    print("OK: risk-aware mode, 6 tabs, no exceptions")

    print("check_app_tabs: PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
