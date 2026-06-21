from dagster import AssetCheckResult, MetadataValue
import polars as pl


def required_string_columns_check(
    df: pl.DataFrame,
    *,
    check_name: str,
    columns: list[str],
) -> AssetCheckResult:
    if df.is_empty():
        invalid_rows = 0
    else:
        invalid_rows = df.filter(
            pl.any_horizontal(
                [
                    pl.col(column).is_null() | (pl.col(column).str.strip_chars() == "")
                    for column in columns
                ]
            )
        ).height

    return AssetCheckResult(
        passed=invalid_rows == 0,
        check_name=check_name,
        metadata={"invalid_rows": MetadataValue.int(invalid_rows)},
    )


def event_start_valid_check(
    df: pl.DataFrame,
    *,
    check_name: str,
) -> AssetCheckResult:
    invalid_rows = (
        0 if df.is_empty() else df.filter(pl.col("event_start").is_null()).height
    )
    return AssetCheckResult(
        passed=invalid_rows == 0,
        check_name=check_name,
        metadata={"invalid_rows": MetadataValue.int(invalid_rows)},
    )


def raise_for_failed_event_checks(*results: AssetCheckResult) -> None:
    failed = [result.check_name for result in results if not result.passed]
    if failed:
        names = ", ".join(str(name) for name in failed)
        msg = f"Event ingestion asset checks failed before Postgres write: {names}"
        raise ValueError(msg)
