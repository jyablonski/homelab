from __future__ import annotations
from collections.abc import Iterator
from contextlib import contextmanager
from typing import Any
from urllib.parse import quote
from uuid import uuid4

import polars as pl
import psycopg2
from dagster import ConfigurableResource, EnvVar
from psycopg2 import sql
from psycopg2.extensions import connection as Connection
from psycopg2.extras import execute_values


class PostgresResource(ConfigurableResource):
    """Thin psycopg2 wrapper for reading and writing the source database."""

    host: str
    port: str = "5432"
    database: str = "postgres"
    user: str = "postgres"
    password: str
    search_path: str = "source,public"
    connect_timeout: int = 5

    @property
    def dsn(self) -> str:
        """Build a PostgreSQL DSN from the configured source DB fields."""
        return (
            f"postgresql://{quote(self.user, safe='')}:{quote(self.password, safe='')}@"
            f"{self.host}:{self.port}/{self.database}"
        )

    @contextmanager
    def connection(self) -> Iterator[Connection]:
        conn = psycopg2.connect(
            host=self.host,
            port=self.port,
            dbname=self.database,
            user=self.user,
            password=self.password,
            connect_timeout=self.connect_timeout,
            options=f"-c search_path={self.search_path}",
        )
        try:
            yield conn
        finally:
            conn.close()

    def fetch_all(
        self, query: str, params: tuple[Any, ...] | None = None
    ) -> list[tuple]:
        with self.connection() as conn, conn.cursor() as cur:
            cur.execute(query, params)
            return cur.fetchall()

    def fetch_value(self, query: str, params: tuple[Any, ...] | None = None) -> Any:
        with self.connection() as conn, conn.cursor() as cur:
            cur.execute(query, params)
            row = cur.fetchone()
            return row[0] if row else None

    def execute(self, query: str, params: tuple[Any, ...] | None = None) -> None:
        with self.connection() as conn, conn.cursor() as cur:
            cur.execute(query, params)
            conn.commit()

    def merge_polars(
        self,
        df: pl.DataFrame,
        target: str,
        conflict_keys: list[str],
        update_cols: list[str],
    ) -> int:
        """Merge a Polars frame into Postgres through a temporary staging table."""
        if df.is_empty():
            return 0

        schema_name, table_name = _split_table_name(target)
        columns = df.columns
        staging_table = f"{table_name}_staging_{uuid4().hex}"
        insert_rows = [tuple(row[col] for col in columns) for row in df.to_dicts()]

        target_ident = sql.Identifier(schema_name, table_name)
        staging_ident = sql.Identifier(staging_table)
        column_idents = sql.SQL(", ").join(sql.Identifier(col) for col in columns)
        conflict_idents = sql.SQL(", ").join(
            sql.Identifier(col) for col in conflict_keys
        )
        update_assignments = sql.SQL(", ").join(
            sql.SQL("{} = EXCLUDED.{}").format(sql.Identifier(col), sql.Identifier(col))
            for col in update_cols
        )

        with self.connection() as conn, conn.cursor() as cur:
            cur.execute(
                sql.SQL(
                    "CREATE TEMP TABLE {} ON COMMIT DROP AS "
                    "SELECT {} FROM {} WHERE false"
                ).format(staging_ident, column_idents, target_ident)
            )
            execute_values(
                cur,
                sql.SQL("INSERT INTO {} ({}) VALUES %s").format(
                    staging_ident, column_idents
                ),
                insert_rows,
            )
            merge_query = sql.SQL(
                """
                INSERT INTO {} ({})
                SELECT {} FROM {}
                ON CONFLICT ({}) DO UPDATE SET {}
                """
            ).format(
                target_ident,
                column_idents,
                column_idents,
                staging_ident,
                conflict_idents,
                update_assignments,
            )
            cur.execute(merge_query)
            affected = cur.rowcount
            conn.commit()
            return affected


def _split_table_name(target: str) -> tuple[str, str]:
    parts = target.split(".")
    if len(parts) == 1:
        return "public", parts[0]
    if len(parts) == 2 and all(parts):
        return parts[0], parts[1]
    msg = f"target must be '<table>' or '<schema>.<table>', got {target!r}"
    raise ValueError(msg)


postgres_resource = PostgresResource(
    host=EnvVar("DB_HOST"),
    port=EnvVar("DB_PORT"),
    database=EnvVar("DB_NAME"),
    user=EnvVar("DB_USER"),
    password=EnvVar("DB_PASSWORD"),
    search_path=EnvVar("DB_SEARCH_PATH"),
)
