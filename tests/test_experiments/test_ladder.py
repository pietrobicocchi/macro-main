"""The ablation ladder (experiments/settings.py) must end at today's defaults, or its top rung measures another model."""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "experiments"))

from settings import LADDER  # noqa: E402

from macromodel.configurations import CountryConfiguration  # noqa: E402


def test_top_rung_of_the_ladder_is_todays_defaults():
    top = CountryConfiguration()
    for change in LADDER[-1].changes:
        change(top)

    assert json.loads(top.model_dump_json()) == json.loads(CountryConfiguration().model_dump_json())
    assert LADDER[-1].data == {}


def test_bottom_rung_differs_from_the_defaults():
    bottom = CountryConfiguration()
    for change in LADDER[0].changes:
        change(bottom)

    assert json.loads(bottom.model_dump_json()) != json.loads(CountryConfiguration().model_dump_json())
