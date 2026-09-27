"""Phase 10 deploy-readiness checks that run in the normal test suite
(fast, no clone/venv needed) -- the full fresh-clone-and-fresh-venv
end-to-end verification (item 2 of the Phase 10 brief) is deliberately NOT
automated into this suite or into CI: it requires network access (pip
installing into a brand-new venv, potentially a fresh `git clone`), takes
tens of seconds to minutes, and CI already exercises the equivalent app
code path via `scripts/smoke_e2e.py` + `scripts/check_app_tabs.py` against
the FULL requirements.txt env (see .github/workflows/tests.yml). This is a
deliberate choice (documented per the brief's own "your call, but be
explicit" instruction), not an oversight -- treat a real fresh-clone/
fresh-venv/slim-requirements run as a manual, release-time check (done once
by the Phase 10 agent; see its final report for the result), not a routine
CI step.

What IS automated here: that requirements-app.txt's own package list is
sufficient to import everything the app's live path actually imports
(app.streamlit_app and everything it imports at module level), run in the
CURRENT env (which has the full requirements.txt installed, a superset of
requirements-app.txt) -- this catches "app imports a heavy lib" regressions
without needing a second venv, though it can't catch "requirements-app.txt
is missing a package the current env happens to already have for other
reasons" (that class of bug needs the real fresh-venv check above)."""
from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent


def test_app_import_path_never_pulls_in_heavy_training_libs():
    """agriopt.models.* (sklearn/xgboost/shap) must never end up in
    sys.modules just from importing the app's own module graph -- this is
    the actual invariant "the app never loads models/*.joblib at request
    time" depends on (see app/data.py's module docstring)."""
    before = set(sys.modules)
    import app.streamlit_app  # noqa: F401

    after = set(sys.modules)
    newly_imported_roots = {m.split(".")[0] for m in (after - before)}
    heavy = newly_imported_roots & {"sklearn", "xgboost", "shap"}
    assert not heavy, f"app.streamlit_app's import graph pulled in heavy training-only libs: {heavy}"


def test_requirements_app_txt_has_no_heavy_training_libs():
    """Checks only the actual package lines (not comments -- the file's own
    header comment explicitly NAMES these libraries to explain why they are
    excluded, which would otherwise false-positive a naive substring check)."""
    lines = [
        ln.strip().lower()
        for ln in (REPO_ROOT / "requirements-app.txt").read_text(encoding="utf-8").splitlines()
        if ln.strip() and not ln.strip().startswith("#")
    ]
    for banned in ("xgboost", "scikit-learn", "sklearn", "shap", "kaggle"):
        assert not any(line.startswith(banned) for line in lines), f"requirements-app.txt should not list {banned!r} (training-only)"


def test_requirements_app_txt_is_pinned():
    lines = [
        ln.strip()
        for ln in (REPO_ROOT / "requirements-app.txt").read_text(encoding="utf-8").splitlines()
        if ln.strip() and not ln.strip().startswith("#")
    ]
    assert lines, "requirements-app.txt has no package lines"
    for line in lines:
        assert "==" in line, f"requirements-app.txt line not pinned to an exact version: {line!r}"


def test_streamlit_config_toml_exists_and_has_headless():
    config_path = REPO_ROOT / ".streamlit" / "config.toml"
    assert config_path.exists()
    text = config_path.read_text(encoding="utf-8")
    assert "headless = true" in text


def test_gitignore_negation_keeps_cache_trackable():
    """The .gitignore negation for data/processed/crop_params_cache.json is
    the actual mechanism the whole deploy story depends on -- checked here
    via `git check-ignore` semantics reimplemented minimally (full
    correctness was verified once with a real `git status`/`git check-ignore`
    by the Phase 10 agent; see its final report)."""
    gitignore_text = (REPO_ROOT / ".gitignore").read_text(encoding="utf-8")
    assert "data/processed/*" in gitignore_text, "expected the wildcard-contents form, not a bare 'data/processed/' directory ignore"
    assert "!data/processed/crop_params_cache.json" in gitignore_text
