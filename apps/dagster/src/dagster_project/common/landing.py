from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

import polars as pl
from dagster import AssetExecutionContext, MetadataValue

from dagster_project.resources import PostgresResource


def utc_now() -> datetime:
    return datetime.now(UTC)


def parse_iso_utc(value: Any) -> datetime | None:
    if not value:
        return None
    normalized = str(value).replace("Z", "+00:00")
    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)


def stamp(
    df: pl.DataFrame,
    *,
    source: str,
    modified_at: datetime | None = None,
) -> pl.DataFrame:
    modified_at = modified_at or utc_now()
    return df.with_columns(
        pl.lit(source).alias("source"),
        pl.lit(modified_at).alias("modified_at"),
    )


def filter_forward_window(
    df: pl.DataFrame,
    *,
    timestamp_col: str,
    days: int,
    now: datetime | None = None,
) -> pl.DataFrame:
    if df.is_empty():
        return df

    now = now or utc_now()
    end = now + timedelta(days=days)
    return df.filter(
        pl.col(timestamp_col).is_not_null()
        & (pl.col(timestamp_col) >= now)
        & (pl.col(timestamp_col) <= end)
    )


def empty_frame(schema: dict[str, Any]) -> pl.DataFrame:
    return pl.DataFrame(schema=schema)


def land_events(
    context: AssetExecutionContext,
    postgres: PostgresResource,
    *,
    df: pl.DataFrame,
    target: str,
    source: str,
    conflict_keys: list[str],
    update_cols: list[str],
    forward_window_days: int,
    fetched: int,
    log_source: str,
    detail: str = "",
    apply_forward_window: bool = True,
    extra_metadata: dict[str, MetadataValue] | None = None,
) -> int:
    parsed = df.height
    if apply_forward_window:
        df = filter_forward_window(
            df,
            timestamp_col="event_start",
            days=forward_window_days,
        )
    after_window = df.height
    df = stamp(df, source=source)
    rows = postgres.merge_polars(
        df,
        target=target,
        conflict_keys=conflict_keys,
        update_cols=update_cols,
    )
    metadata = log_landing_summary(
        context,
        source=log_source,
        fetched=fetched,
        parsed=parsed,
        after_window=after_window,
        merged=rows,
        forward_window_days=forward_window_days,
        detail=detail,
    )
    if extra_metadata:
        metadata.update(extra_metadata)
    context.add_output_metadata(metadata)
    return rows


def log_landing_summary(
    context: AssetExecutionContext,
    *,
    source: str,
    fetched: int,
    parsed: int,
    after_window: int,
    merged: int,
    forward_window_days: int,
    detail: str = "",
) -> dict[str, MetadataValue]:
    message = (
        f"{source} landing: fetched={fetched} parsed={parsed} "
        f"in_window={after_window} merged={merged} "
        f"(forward_window_days={forward_window_days})"
    )
    if detail:
        message = f"{message}; {detail}"
    context.log.info(message)

    return {
        "fetched": MetadataValue.int(fetched),
        "parsed": MetadataValue.int(parsed),
        "after_window_filter": MetadataValue.int(after_window),
        "forward_window_days": MetadataValue.int(forward_window_days),
        "rows_merged": MetadataValue.int(merged),
    }
