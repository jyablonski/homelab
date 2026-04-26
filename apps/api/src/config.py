from dataclasses import dataclass, field
from functools import lru_cache
from os import getenv


@dataclass(frozen=True)
class Settings:
    app_name: str = field(default_factory=lambda: getenv("API_APP_NAME", "Homelab API"))
    environment: str = field(default_factory=lambda: getenv("API_ENV", "local"))
    root_path: str = field(default_factory=lambda: getenv("API_ROOT_PATH", ""))
    database_url: str = field(default_factory=lambda: getenv("DATABASE_URL", ""))
    db_host: str = field(default_factory=lambda: getenv("DB_HOST", "localhost"))
    db_port: str = field(default_factory=lambda: getenv("DB_PORT", "5432"))
    db_name: str = field(default_factory=lambda: getenv("DB_NAME", "postgres"))
    db_user: str = field(default_factory=lambda: getenv("DB_USER", "postgres"))
    db_password: str = field(default_factory=lambda: getenv("DB_PASSWORD", ""))
    db_search_path: str = field(
        default_factory=lambda: getenv("DB_SEARCH_PATH", "source,public")
    )
    db_connect_timeout: int = field(
        default_factory=lambda: int(getenv("DB_CONNECT_TIMEOUT", "5"))
    )

    @property
    def normalized_database_url(self) -> str:
        return self.database_url.replace("postgresql+psycopg2://", "postgresql://")

    @property
    def sqlalchemy_database_url(self) -> str:
        if self.database_url:
            return self.normalized_database_url

        return (
            f"postgresql://{self.db_user}:{self.db_password}"
            f"@{self.db_host}:{self.db_port}/{self.db_name}"
        )


@lru_cache
def get_settings() -> Settings:
    return Settings()
