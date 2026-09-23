import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))


def test_app_module_imports():
    import app.streamlit_app  # noqa: F401


def test_smoke_e2e_main_returns_0():
    result = subprocess.run(
        [sys.executable, str(REPO_ROOT / "scripts" / "smoke_e2e.py")],
        capture_output=True,
        text=True,
        cwd=REPO_ROOT,
    )
    assert result.returncode == 0, f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}"
    assert "smoke_e2e: PASS" in result.stdout


def test_infeasible_scenario_handled_without_exception():
    from agriopt.optim.problem import Scenario
    from app import data as appdata
    from app.pipeline import run_pipeline, weights_from_priority

    raw = appdata.load_cache_raw()
    params_df = appdata.params_df_from_records(raw["price_modes"]["market"])

    scenario = Scenario(water_budget_m3=1.0, land_ha=10.0, food_share_min=0.3, max_share=0.5, price_mode="market")
    result = run_pipeline(params_df, scenario, weights_from_priority(0.5))

    assert result.feasible is False
    assert isinstance(result.message, str) and len(result.message) > 0
