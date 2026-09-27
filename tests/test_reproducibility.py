"""Phase 8: seed-reproducibility of solve_nsga2/solve_nsga3, in-process and
across separate `python -c` subprocesses.

Root cause (see agriopt.models.yield_model._force_single_threaded_predict
for the full writeup): the saved yield model (models/yield_best.joblib) is a
RandomForestRegressor(n_jobs=-1). sklearn's RandomForest.predict() with
n_jobs != 1 sums per-tree predictions across threads, and the accumulation
ORDER is scheduled by the OS -- not fixed by `random_state` -- so
floating-point non-associativity made expected_yield_saleable() (and hence
build_crop_params()'s profit_ha) differ by ~1e-13 relative between separate
process runs. That tiny noise fed into the NSGA-II/III objective evaluation
and was the actual source of non-reproducibility (pymoo's own seed handling,
and get_reference_directions("das-dennis", ...), are both confirmed
deterministic in isolation -- see the subprocess tests below, which now
pass with the load_model() fix in place). solvers.py additionally pins
OMP/OPENBLAS/MKL/NUMBA thread counts to 1 as defense in depth (matching the
convention in scripts/40_build_cache.py etc.), though that was not itself
the root cause here.
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import numpy as np
import pytest

pytestmark = pytest.mark.needs_data  # Phase 10: needs gitignored data/raw or models/*.joblib -- see pyproject.toml's marker registration

from agriopt.optim.params import build_crop_params
from agriopt.optim.problem import Scenario
from agriopt.optim.risk import build_risk_inputs
from agriopt.optim.solvers import solve_nsga2, solve_nsga3

REPO_ROOT = Path(__file__).resolve().parent.parent
GENS = 15  # small, just enough generations to exercise real optimizer dynamics


@pytest.fixture(scope="module")
def params():
    return build_crop_params("market", verbose=False)


@pytest.fixture(scope="module")
def scenario(params):
    return Scenario(water_budget_m3=5_000_000, land_ha=10.0)


# --- in-process ----------------------------------------------------------------


def test_nsga2_in_process_reproducible(params, scenario):
    X1, F1, _ = solve_nsga2(scenario, params, gens=GENS, seed=42)
    X2, F2, _ = solve_nsga2(scenario, params, gens=GENS, seed=42)
    np.testing.assert_array_equal(X1, X2)
    np.testing.assert_array_equal(F1, F2)


def test_nsga3_in_process_reproducible(params, scenario):
    risk_inputs = build_risk_inputs(params)
    X1, F1, _ = solve_nsga3(scenario, params, risk_inputs.Sigma, gens=GENS, seed=42)
    X2, F2, _ = solve_nsga3(scenario, params, risk_inputs.Sigma, gens=GENS, seed=42)
    np.testing.assert_array_equal(X1, X2)
    np.testing.assert_array_equal(F1, F2)


# --- subprocess (catches thread-count/BLAS-vendor/parallel-predict nondeterminism) --

_NSGA2_SCRIPT = f"""
import numpy as np
from agriopt.optim.params import build_crop_params
from agriopt.optim.problem import Scenario
from agriopt.optim.solvers import solve_nsga2

scenario = Scenario(water_budget_m3=5_000_000, land_ha=10.0)
params_df = build_crop_params("market", verbose=False)
X, F, _ = solve_nsga2(scenario, params_df, gens={GENS}, seed=42)
np.savez(r"{{out_path}}", X=X, F=F)
"""

_NSGA3_SCRIPT = f"""
import numpy as np
from agriopt.optim.params import build_crop_params
from agriopt.optim.problem import Scenario
from agriopt.optim.risk import build_risk_inputs
from agriopt.optim.solvers import solve_nsga3

scenario = Scenario(water_budget_m3=5_000_000, land_ha=10.0)
params_df = build_crop_params("market", verbose=False)
risk_inputs = build_risk_inputs(params_df)
X, F, _ = solve_nsga3(scenario, params_df, risk_inputs.Sigma, gens={GENS}, seed=42)
np.savez(r"{{out_path}}", X=X, F=F)
"""


def _run_subprocess(script_template: str, out_path: Path) -> None:
    code = script_template.format(out_path=str(out_path))
    result = subprocess.run(
        [sys.executable, "-c", code],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        timeout=300,
    )
    assert result.returncode == 0, f"subprocess failed:\nstdout={result.stdout}\nstderr={result.stderr}"


def test_nsga2_subprocess_reproducible(tmp_path):
    out1, out2 = tmp_path / "run1.npz", tmp_path / "run2.npz"
    _run_subprocess(_NSGA2_SCRIPT, out1)
    _run_subprocess(_NSGA2_SCRIPT, out2)
    d1, d2 = np.load(out1), np.load(out2)
    np.testing.assert_allclose(d1["X"], d2["X"], atol=1e-12, rtol=0)
    np.testing.assert_allclose(d1["F"], d2["F"], atol=1e-12, rtol=0)


def test_nsga3_subprocess_reproducible(tmp_path):
    out1, out2 = tmp_path / "run1.npz", tmp_path / "run2.npz"
    _run_subprocess(_NSGA3_SCRIPT, out1)
    _run_subprocess(_NSGA3_SCRIPT, out2)
    d1, d2 = np.load(out1), np.load(out2)
    np.testing.assert_allclose(d1["X"], d2["X"], atol=1e-12, rtol=0)
    np.testing.assert_allclose(d1["F"], d2["F"], atol=1e-12, rtol=0)
