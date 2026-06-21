from dagster import MetadataValue, asset

GROUP = "examples"


@asset(
    group_name=GROUP,
    compute_kind="python",
    description="Example asset that returns a static greeting when examples are enabled.",
)
def example_greeting() -> str:
    """A trivial asset used to verify the example opt-in wiring."""
    return "hello from dagster"


@asset(
    group_name=GROUP,
    compute_kind="python",
    description="Example downstream asset that reports the greeting length.",
)
def example_length(context, example_greeting: str) -> int:
    """Depends on ``example_greeting`` to demonstrate parameter wiring."""
    length = len(example_greeting)
    context.add_output_metadata({"length": MetadataValue.int(length)})
    return length
