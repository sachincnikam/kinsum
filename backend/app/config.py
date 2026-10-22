"""App settings, read from environment variables and the .env file at the repo root."""

from pathlib import Path

from platformdirs import user_data_dir
from pydantic_settings import BaseSettings, SettingsConfigDict

REPO_ROOT = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=REPO_ROOT / ".env", env_file_encoding="utf-8", extra="ignore"
    )

    anthropic_api_key: str = ""
    kinsum_data_dir: str = ""
    kinsum_port: int = 8000
    # Lock the app after this many minutes with nobody using it.
    kinsum_idle_lock_minutes: int = 10

    @property
    def data_dir(self) -> Path:
        """Folder for the database, backups and logs — always outside the repo.

        Windows: %LOCALAPPDATA%\\Kinsum   Mac: ~/Library/Application Support/Kinsum
        """
        path = Path(self.kinsum_data_dir) if self.kinsum_data_dir else Path(
            user_data_dir("Kinsum", appauthor=False, roaming=False)
        )
        path.mkdir(parents=True, exist_ok=True)
        return path

    @property
    def ai_enabled(self) -> bool:
        return bool(self.anthropic_api_key.strip())


settings = Settings()
