"""Cosmos DB storage for login users (ytv-app-db) and channel-title lookup (ytv-db)."""

from __future__ import annotations

from typing import Any

from azure.cosmos.exceptions import CosmosResourceExistsError, CosmosResourceNotFoundError

from .auth_service import AuthError
from .cosmos_repository import cosmos_client
from .settings import Settings


class UserRepository:
    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or Settings.from_environment()
        app_database = cosmos_client().get_database_client(self.settings.cosmos_app_database)
        self.users = app_database.get_container_client(self.settings.users_container)
        operational_database = cosmos_client().get_database_client(self.settings.cosmos_database)
        self.channels = operational_database.get_container_client(
            self.settings.channels_container
        )

    def get_user(self, user_id: str) -> dict[str, Any] | None:
        if not user_id:
            return None
        try:
            return self.users.read_item(item=user_id, partition_key=user_id)
        except CosmosResourceNotFoundError:
            return None

    def create_user(self, user: dict[str, Any]) -> dict[str, Any]:
        try:
            return self.users.create_item(user)
        except CosmosResourceExistsError as exc:
            raise AuthError(
                "이미 가입된 이메일입니다.", status_code=409, code="EMAIL_EXISTS"
            ) from exc

    def find_channel_by_title(self, channel_title: str) -> dict[str, Any] | None:
        rows = list(
            self.channels.query_items(
                query=(
                    "SELECT TOP 1 c.channel_id, c.channel_title "
                    "FROM c WHERE STRINGEQUALS(c.channel_title, @title, true)"
                ),
                parameters=[{"name": "@title", "value": channel_title}],
                enable_cross_partition_query=True,
            )
        )
        return rows[0] if rows else None
