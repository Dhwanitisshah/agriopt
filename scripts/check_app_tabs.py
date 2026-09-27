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


EXPECTED_TABS = 8


def main() -> int:
    from streamlit.testing.v1 import AppTest

    at = AppTest.from_file(str(REPO_ROOT / "app" / "streamlit_app.py"))

    at.run(timeout=90)
    if at.exception:
        print(f"FAIL: normal mode raised: {list(at.exception)}")
        return 1
    if len(at.tabs) != EXPECTED_TABS:
        print(f"FAIL: expected {EXPECTED_TABS} tabs in normal mode, got {len(at.tabs)}")
        return 1
    print(f"OK: normal mode, {EXPECTED_TABS} tabs, no exceptions")

    at.toggle[0].set_value(True).run(timeout=90)
    if at.exception:
        print(f"FAIL: risk-aware mode raised: {list(at.exception)}")
        return 1
    if len(at.tabs) != EXPECTED_TABS:
        print(f"FAIL: expected {EXPECTED_TABS} tabs in risk-aware mode, got {len(at.tabs)}")
        return 1
    print(f"OK: risk-aware mode, {EXPECTED_TABS} tabs, no exceptions")
    at.toggle[0].set_value(False).run(timeout=90)  # back to normal mode before the region/water-basis sweep below

    # Phase 10: sweep every region x water-basis combination the sidebar now
    # exposes -- each rerun must still render all EXPECTED_TABS tabs with no
    # exception. Widget order in the sidebar: region selectbox is
    # at.selectbox[0] ("Price mode" comes first? no -- see sidebar.py: the
    # sidebar renders "Price mode" selectbox BEFORE "Region"/"Water basis",
    # so selectbox[0]=price mode, [1]=region, [2]=water basis), found by
    # label rather than a hardcoded index to stay robust to reordering.
    def _select_by_label(label_substr: str):
        for sb in at.selectbox:
            if label_substr.lower() in (sb.label or "").lower():
                return sb
        raise AssertionError(f"no selectbox found with label containing {label_substr!r}")

    region_options = list(_select_by_label("Region").options)
    water_basis_options = list(_select_by_label("Water basis").options)

    for region_opt in region_options:
        _select_by_label("Region").set_value(region_opt).run(timeout=90)
        if at.exception:
            print(f"FAIL: region={region_opt!r} raised: {list(at.exception)}")
            return 1
        if len(at.tabs) != EXPECTED_TABS:
            print(f"FAIL: region={region_opt!r}: expected {EXPECTED_TABS} tabs, got {len(at.tabs)}")
            return 1
    print(f"OK: all {len(region_options)} region options render without exception")

    for basis_opt in water_basis_options:
        _select_by_label("Water basis").set_value(basis_opt).run(timeout=90)
        if at.exception:
            print(f"FAIL: water_basis={basis_opt!r} raised: {list(at.exception)}")
            return 1
        if len(at.tabs) != EXPECTED_TABS:
            print(f"FAIL: water_basis={basis_opt!r}: expected {EXPECTED_TABS} tabs, got {len(at.tabs)}")
            return 1
    print(f"OK: all {len(water_basis_options)} water-basis options render without exception")

    print("check_app_tabs: PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
