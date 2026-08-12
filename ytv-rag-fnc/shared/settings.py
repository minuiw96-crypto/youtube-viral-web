"""Environment-backed application settings."""

from __future__ import annotations

import os
from dataclasses import dataclass


def _first_setting(*names: str, default: str = "") -> str:
    for name in names:
        value = os.getenv(name, "").strip()
        if value:
            return value
    return default


def _as_bool(value: str) -> bool:
    return value.strip().lower() in {"1", "true", "yes", "on"}


@dataclass(frozen=True)
class Settings:
    azure_openai_endpoint: str
    chat_deployment: str
    embedding_deployment: str
    cosmos_endpoint: str
    cosmos_connection_string: str
    cosmos_database: str
    cosmos_app_database: str
    channels_container: str
    videos_container: str
    video_snapshots_container: str
    channel_snapshots_container: str
    predictions_container: str
    labels_container: str
    legacy_snapshots_container: str
    legacy_evaluations_container: str
    rag_container: str
    users_container: str
    jwt_secret: str
    auth_token_ttl_hours: int

    @classmethod
    def from_environment(cls) -> "Settings":
        return cls(
            azure_openai_endpoint=_first_setting("AZURE_OPENAI_ENDPOINT").rstrip("/"),
            chat_deployment=_first_setting("AZURE_OPENAI_CHAT_DEPLOYMENT"),
            embedding_deployment=_first_setting(
                "AZURE_OPENAI_EMBEDDING_DEPLOYMENT",
                "AZURE_OPENAI_EMBEDDINGS_DEPLOYMENT",
            ),
            cosmos_endpoint=_first_setting("COSMOS_DB_ENDPOINT", "COSMOSDB_ENDPOINT").rstrip("/"),
            cosmos_connection_string=_first_setting("COSMOS_DB_CONNECTION_STRING"),
            cosmos_database=_first_setting(
                "COSMOS_DB_DATABASE",
                "COSMOSDB_DATABASE",
                default="test-mvp-db",
            ),
            cosmos_app_database=_first_setting(
                "COSMOS_APP_DB_DATABASE", default="ytv-app-db"
            ),
            channels_container=_first_setting("COSMOS_CHANNELS_CONTAINER", default="channels"),
            videos_container=_first_setting("COSMOS_VIDEOS_CONTAINER", default="videos"),
            video_snapshots_container=_first_setting(
                "COSMOS_VIDEO_SNAPSHOTS_CONTAINER",
                "COSMOS_SNAPSHOTS_CONTAINER",
                default="video_snapshots",
            ),
            channel_snapshots_container=_first_setting(
                "COSMOS_CHANNEL_SNAPSHOTS_CONTAINER", default="channel_snapshots"
            ),
            predictions_container=_first_setting(
                "COSMOS_PREDICTIONS_CONTAINER", default="predictions"
            ),
            labels_container=_first_setting("COSMOS_LABELS_CONTAINER", default="labels"),
            legacy_snapshots_container=_first_setting(
                "COSMOS_LEGACY_SNAPSHOTS_CONTAINER", default="snapshots"
            ),
            legacy_evaluations_container=_first_setting(
                "COSMOS_LEGACY_EVALUATIONS_CONTAINER", default="evaluations"
            ),
            rag_container=_first_setting("COSMOS_RAG_CONTAINER", default="rag_documents"),
            users_container=_first_setting("COSMOS_USERS_CONTAINER", default="users"),
            jwt_secret=_first_setting("JWT_SECRET"),
            auth_token_ttl_hours=int(
                _first_setting("AUTH_TOKEN_TTL_HOURS", default="24")
            ),
        )

    @property
    def openai_ready(self) -> bool:
        return bool(self.azure_openai_endpoint and self.chat_deployment)

    @property
    def cosmos_ready(self) -> bool:
        return bool(self.cosmos_connection_string or self.cosmos_endpoint)

    @property
    def vector_search_ready(self) -> bool:
        return bool(self.cosmos_ready and self.embedding_deployment and self.rag_container)

    @property
    def auth_ready(self) -> bool:
        return bool(self.cosmos_ready and self.jwt_secret and self.users_container)
