"""Every file path mentioned in docs/handoff/*.md must exist in the repo, so the report/paper/PPT team
is never sent to a missing file. Data-free; runs in CI."""
import glob
import re
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
HANDOFF = REPO / "docs" / "handoff"
EXTS = (".md", ".csv", ".png", ".py", ".json", ".yml", ".bib", ".ps1", ".txt", ".toml")
# where a bare file name (no folder) may live
SEARCH_DIRS = ["", "docs", "docs/handoff", "docs/handoff/figures", "docs/img", "reports/results", "reports/eda", "scripts", "data/reference"]
# things named in the docs that are intentionally not in the repository (gitignored / external)
EXTERNAL = {"yield_clean.parquet", "prices_monthly.parquet"}


def _tokens(text: str):
    for tok in re.findall(r"`([^`\n]+)`", text):
        tok = tok.strip().rstrip(".,;:")
        if " " in tok or tok.startswith(("http", "python", "git ", "pip ", "pytest")):
            continue
        if tok.endswith("/") or tok.lower().endswith(EXTS):
            yield tok


def _exists(tok: str) -> bool:
    if tok in EXTERNAL:
        return True
    if "*" in tok:
        return any(glob.glob(str(REPO / d / tok)) for d in SEARCH_DIRS)
    if "/" in tok:
        return (REPO / tok).exists() or (HANDOFF / tok).exists()
    return any((REPO / d / tok).exists() for d in SEARCH_DIRS)


def test_every_path_in_the_handoff_docs_exists():
    missing = []
    for md in sorted(HANDOFF.glob("*.md")):
        for tok in _tokens(md.read_text(encoding="utf-8")):
            if not _exists(tok):
                missing.append(f"{md.name}: {tok}")
    assert not missing, "broken paths in docs/handoff:\n" + "\n".join(missing)


def test_every_figure_listed_in_figures_md_is_present():
    text = (HANDOFF / "FIGURES.md").read_text(encoding="utf-8")
    names = set(re.findall(r"`(fig\d\d_[a-z0-9_]+\.png)`", text))
    assert len(names) >= 14
    for n in names:
        assert (HANDOFF / "figures" / n).exists(), n
    on_disk = {p.name for p in (HANDOFF / "figures").glob("*.png")}
    assert on_disk <= names, f"figures not described in FIGURES.md: {sorted(on_disk - names)}"
