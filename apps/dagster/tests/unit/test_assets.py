import pytest
from dagster import materialize

from dagster_project.defs.assets.internal.example import (
    example_greeting,
    example_length,
)

pytestmark = pytest.mark.unit


def test_example_assets_materialize():
    result = materialize([example_greeting, example_length])
    assert result.success
    assert result.output_for_node("example_length") == len("hello from dagster")
