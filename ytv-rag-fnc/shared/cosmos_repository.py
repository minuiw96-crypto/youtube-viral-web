"""Read the four operational containers and the optional RAG container."""

from __future__ import annotations

from collections import Counter
from functools import lru_cache
from typing import Any

from .embedding_search import rank_documents
from .search_normalization import lexical_rank_documents
from .settings import Settings


def _query(container: Any, query: str, parameters: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return list(
        container.query_items(
            query=query,
            parameters=parameters,
            enable_cross_partition_query=True,
        )
    )


@lru_cache(maxsize=1)
def cosmos_client() -> Any:
    from azure.cosmos import CosmosClient
    from azure.identity import DefaultAzureCredential

    settings = Settings.from_environment()
    if settings.cosmos_connection_string:
        return CosmosClient.from_connection_string(settings.cosmos_connection_string)
    if not settings.cosmos_endpoint:
        raise RuntimeError("Cosmos DB 환경 변수가 설정되지 않았습니다.")
    return CosmosClient(settings.cosmos_endpoint, credential=DefaultAzureCredential())


class CosmosRepository:
    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or Settings.from_environment()
        self.database = cosmos_client().get_database_client(self.settings.cosmos_database)
        self.app_database = cosmos_client().get_database_client(
            self.settings.cosmos_app_database
        )

    def _container(self, name: str) -> Any:
        return self.database.get_container_client(name)

    def _app_container(self, name: str) -> Any:
        return self.app_database.get_container_client(name)

    @staticmethod
    def _count(container: Any) -> int:
        rows = _query(container, "SELECT VALUE COUNT(1) FROM c", [])
        return int(rows[0]) if rows else 0

    @staticmethod
    def _distinct_video_count(container: Any) -> int:
        rows = _query(
            container,
            "SELECT DISTINCT VALUE c.video_id FROM c "
            "WHERE IS_DEFINED(c.video_id) AND NOT IS_NULL(c.video_id) AND c.video_id != ''",
            [],
        )
        return len(rows)

    def admin_counts(self) -> dict[str, int]:
        return {
            "channels": self._count(self._container(self.settings.channels_container)),
            "videos": self._count(self._container(self.settings.videos_container)),
            "predictions": self._count(self._container(self.settings.predictions_container)),
            "labels": self._count(self._container(self.settings.labels_container)),
            "video_snapshots": self._count(self._container(self.settings.video_snapshots_container)),
            "users": self._count(self._app_container(self.settings.users_container)),
            "predicted_videos": self._distinct_video_count(self._container(self.settings.predictions_container)),
            "labeled_videos": self._distinct_video_count(self._container(self.settings.labels_container)),
        }

    def channel_category_counts(self) -> list[dict[str, Any]]:
        category_values = _query(
            self._container(self.settings.channels_container),
            "SELECT VALUE c.project_category FROM c",
            [],
        )
        counts = Counter(str(value or "기타") for value in category_values)
        return [
            {
                "name": name,
                "channel_count": count,
            }
            for name, count in counts.items()
        ]

    def get_channel(self, channel_id: str) -> dict[str, Any] | None:
        rows = _query(
            self._container(self.settings.channels_container),
            "SELECT TOP 1 * FROM c WHERE c.channel_id = @channel_id",
            [{"name": "@channel_id", "value": channel_id}],
        )
        return rows[0] if rows else None

    def list_channels(self, limit: int | None = 200) -> list[dict[str, Any]]:
        query = (
            "SELECT * FROM c"
            if limit is None
            else f"SELECT TOP {max(1, min(limit, 500))} * FROM c"
        )
        return _query(self._container(self.settings.channels_container), query, [])

    def find_channel_by_title(self, channel_title: str) -> dict[str, Any] | None:
        rows = _query(
            self._container(self.settings.channels_container),
            "SELECT TOP 1 c.channel_id, c.channel_title FROM c "
            "WHERE STRINGEQUALS(c.channel_title, @title, true)",
            [{"name": "@title", "value": channel_title}],
        )
        return rows[0] if rows else None

    def get_channel_snapshots(
        self, channel_id: str, limit: int = 100
    ) -> list[dict[str, Any]]:
        limit = max(1, min(limit, 200))
        return _query(
            self._container(self.settings.channel_snapshots_container),
            f"SELECT TOP {limit} * FROM c WHERE c.channel_id = @channel_id "
            "ORDER BY c.snapshot_time ASC",
            [{"name": "@channel_id", "value": channel_id}],
        )

    def get_video(self, video_id: str) -> dict[str, Any] | None:
        rows = _query(
            self._container(self.settings.videos_container),
            "SELECT TOP 1 * FROM c WHERE c.video_id = @video_id OR c.id = @video_id",
            [{"name": "@video_id", "value": video_id}],
        )
        return rows[0] if rows else None

    def list_channel_videos(self, channel_id: str, limit: int = 50) -> list[dict[str, Any]]:
        limit = max(1, min(limit, 100))
        return _query(
            self._container(self.settings.videos_container),
            f"SELECT TOP {limit} * FROM c WHERE c.channel_id = @channel_id",
            [{"name": "@channel_id", "value": channel_id}],
        )

    def list_videos(self, limit: int = 500) -> list[dict[str, Any]]:
        limit = max(1, min(limit, 1000))
        return _query(
            self._container(self.settings.videos_container),
            f"SELECT TOP {limit} * FROM c",
            [],
        )

    def list_predictions(self, limit: int | None = 500) -> list[dict[str, Any]]:
        query = (
            "SELECT * FROM c"
            if limit is None
            else f"SELECT TOP {max(1, min(limit, 1000))} * FROM c"
        )
        return _query(self._container(self.settings.predictions_container), query, [])

    def list_labels(self, limit: int = 500) -> list[dict[str, Any]]:
        limit = max(1, min(limit, 1000))
        return _query(
            self._container(self.settings.labels_container),
            f"SELECT TOP {limit} * FROM c",
            [],
        )

    def list_video_snapshots(self, limit: int = 1000) -> list[dict[str, Any]]:
        limit = max(1, min(limit, 2000))
        return _query(
            self._container(self.settings.video_snapshots_container),
            f"SELECT TOP {limit} * FROM c",
            [],
        )

    def list_users(self, limit: int = 500) -> list[dict[str, Any]]:
        limit = max(1, min(limit, 1000))
        return _query(
            self._app_container(self.settings.users_container),
            f"SELECT TOP {limit} c.id, c.email, c.name, c.role, "
            "c.channel_id, c.channel_title, c.channel_status, c.active, c.created_at FROM c",
            [],
        )

    def list_channel_predictions(
        self, channel_id: str, limit: int = 100
    ) -> list[dict[str, Any]]:
        limit = max(1, min(limit, 200))
        return _query(
            self._container(self.settings.predictions_container),
            f"SELECT TOP {limit} * FROM c WHERE c.channel_id = @channel_id",
            [{"name": "@channel_id", "value": channel_id}],
        )

    def list_channel_labels(
        self, channel_id: str, limit: int = 100
    ) -> list[dict[str, Any]]:
        limit = max(1, min(limit, 200))
        return _query(
            self._container(self.settings.labels_container),
            f"SELECT TOP {limit} * FROM c WHERE c.channel_id = @channel_id",
            [{"name": "@channel_id", "value": channel_id}],
        )

    def list_channel_video_snapshots(
        self, channel_id: str, limit: int = 200
    ) -> list[dict[str, Any]]:
        limit = max(1, min(limit, 500))
        return _query(
            self._container(self.settings.video_snapshots_container),
            f"SELECT TOP {limit} * FROM c WHERE c.channel_id = @channel_id",
            [{"name": "@channel_id", "value": channel_id}],
        )

    def get_latest_prediction(self, video_id: str) -> dict[str, Any] | None:
        rows = _query(
            self._container(self.settings.predictions_container),
            "SELECT TOP 1 * FROM c WHERE c.video_id = @video_id ORDER BY c.predicted_at DESC",
            [{"name": "@video_id", "value": video_id}],
        )
        return rows[0] if rows else None

    def get_snapshots(self, video_id: str, limit: int = 100) -> list[dict[str, Any]]:
        from azure.cosmos.exceptions import CosmosResourceNotFoundError

        limit = max(1, min(limit, 200))
        parameters = [{"name": "@video_id", "value": video_id}]
        query = f"SELECT TOP {limit} * FROM c WHERE c.video_id = @video_id ORDER BY c.snapshot_time ASC"
        try:
            return _query(
                self._container(self.settings.video_snapshots_container),
                query,
                parameters,
            )
        except CosmosResourceNotFoundError:
            legacy_query = f"SELECT TOP {limit} * FROM c WHERE c.video_id = @video_id ORDER BY c.target_age_hours ASC"
            return _query(
                self._container(self.settings.legacy_snapshots_container),
                legacy_query,
                parameters,
            )

    def get_evaluation(
        self,
        video_id: str,
        candidate_batch_id: str | None,
    ) -> dict[str, Any] | None:
        from azure.cosmos.exceptions import CosmosResourceNotFoundError

        parameters = [{"name": "@video_id", "value": video_id}]
        labels_container_exists = True
        try:
            labels = _query(
                self._container(self.settings.labels_container),
                "SELECT TOP 1 * FROM c WHERE c.video_id = @video_id ORDER BY c.calculated_at DESC",
                parameters,
            )
            if labels:
                return labels[0]
        except CosmosResourceNotFoundError:
            labels_container_exists = False

        if labels_container_exists:
            return None

        container = self._container(self.settings.legacy_evaluations_container)
        direct = _query(
            container,
            "SELECT TOP 1 * FROM c WHERE c.video_id = @video_id ORDER BY c.evaluated_at DESC",
            parameters,
        )
        if not candidate_batch_id:
            return None
        batch = _query(
            container,
            "SELECT TOP 1 * FROM c WHERE c.candidate_batch_id = @batch_id ORDER BY c.evaluated_at DESC",
            [{"name": "@batch_id", "value": candidate_batch_id}],
        )
        return batch[0] if batch else None

    def upsert_rag_document(self, document: dict[str, Any]) -> dict[str, Any]:
        return self._app_container(self.settings.rag_container).upsert_item(document)

    def list_rag_documents(
        self,
        channel_id: str,
        limit: int = 200,
    ) -> list[dict[str, Any]]:
        limit = max(1, min(limit, 500))
        return _query(
            self._app_container(self.settings.rag_container),
            f"SELECT TOP {limit} * FROM c "
            "WHERE c.channel_id = 'GLOBAL' OR c.channel_id = @channel_id",
            [{"name": "@channel_id", "value": channel_id}],
        )

    def vector_search(
        self,
        embedding: list[float],
        channel_id: str,
        limit: int = 5,
    ) -> list[dict[str, Any]]:
        return rank_documents(
            embedding,
            self.list_rag_documents(channel_id),
            limit=limit,
        )

    def lexical_search(
        self,
        question: str,
        channel_id: str,
        limit: int = 5,
    ) -> list[dict[str, Any]]:
        return lexical_rank_documents(
            question, self.list_rag_documents(channel_id), limit=limit
        )
