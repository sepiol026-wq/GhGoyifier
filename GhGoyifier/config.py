# CopyLeft 2026 github.com/sepiol026-wq | telegram:@samsepi0l_ovf. Licensed under AGPLv3.
# Portions derived from vsecoder/github-notifi-bot; original MIT license is retained in LICENSE.

import os

import toml
from pydantic import BaseModel, ConfigDict, Field


class _Section(BaseModel):
    """Common Pydantic config for every TOML section: ignore unknown keys
    so adding new fields in the future doesn't break older configs."""
    model_config = ConfigDict(extra="ignore")


class ConfigBot(_Section):
    token: str


class ConfigDatabase(_Section):
    models: list[str]
    protocol: str = "sqlite"
    file_name: str = "production-database.sqlite3"
    user: str | None = None
    password: str | None = None
    host: str | None = None
    port: str | None = None

    def get_db_url(self) -> str:
        if self.protocol == "sqlite":
            return f"{self.protocol}://{self.file_name}"
        return (
            f"{self.protocol}://{self.user}:{self.password}"
            f"@{self.host}:{self.port}"
        )

    def get_tortoise_config(self) -> dict:
        return {
            "connections": {"default": self.get_db_url()},
            "apps": {
                "models": {
                    "models": self.models,
                    "default_connection": "default",
                },
            },
        }


class ConfigSettings(_Section):
    owner_id: int
    throttling_rate: float = 0.5
    drop_pending_updates: bool = True
    buttons: str = "inline"

    def model_post_init(self, __context) -> None:
        if self.buttons not in {"inline", "in-msg"}:
            raise ValueError("settings.buttons must be 'inline' or 'in-msg'")


class ConfigApi(_Section):
    id: int = 2040
    hash: str = "b18441a1ff607e10a989891a5462e627"
    bot_api_url: str = "https://api.telegram.org"
    host: str = "localhost:4454"

    @property
    def is_local(self) -> bool:
        return self.bot_api_url != "https://api.telegram.org"


class ConfigGitHubApp(_Section):
    """Optional GitHub App credentials. Considered "configured" only when
    ``app_id``, ``slug`` and ``private_key_path`` are all set."""
    app_id: int = 0
    slug: str = ""
    private_key_path: str = ""
    webhook_secret: str = ""

    @property
    def is_configured(self) -> bool:
        return bool(self.app_id and self.slug and self.private_key_path)


class ConfigNotifications(_Section):
    mode: str = "polling"
    poll_interval: int = 30
    none_auth_perm: bool = False


class Config(_Section):
    bot: ConfigBot
    database: ConfigDatabase
    settings: ConfigSettings

    api: ConfigApi = Field(default_factory=ConfigApi)
    github_app: ConfigGitHubApp = Field(default_factory=ConfigGitHubApp)
    notifications: ConfigNotifications = Field(default_factory=ConfigNotifications)


def parse_config(config_file: str = "config.toml") -> Config:
    if not os.path.isfile(config_file) and not config_file.endswith(".toml"):
        config_file += ".toml"
    if not os.path.isfile(config_file):
        raise FileNotFoundError(
            f"Config file not found: {config_file} no such file"
        )
    with open(config_file, "r") as f:
        data = toml.load(f)
    return Config.model_validate(dict(data))
