"""Input validation in build_crop_params must be real exceptions (asserts vanish under python -O).
Validation runs before any model is loaded, so no data or models are needed."""
import pytest

from agriopt.optim.params import build_crop_params


@pytest.mark.parametrize(
    "kwargs, fragment",
    [
        ({"price_mode": "spot"}, "price_mode"),
        ({"water_basis": "rainfed"}, "water_basis"),
        ({"region": "goa"}, "region"),
    ],
)
def test_bad_inputs_raise_value_error(kwargs, fragment):
    with pytest.raises(ValueError, match=fragment):
        build_crop_params(verbose=False, **kwargs)
