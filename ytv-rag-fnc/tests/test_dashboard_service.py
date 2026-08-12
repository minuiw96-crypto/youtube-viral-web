import unittest
from datetime import datetime, timezone

from shared.dashboard_service import DashboardAccessError, DashboardService


class FakeDashboardRepository:
    def get_channel(self, channel_id):
        return {"channel_id": channel_id, "channel_title": "맛있는하루", "project_category": "kr_mukbang", "subscriber_count": 234000, "custom_url": "@tasty-day", "thumbnail_high_url": "https://yt3.example/channel.jpg"}

    def get_channel_snapshots(self, channel_id, limit=200):
        return [
            {"channel_id": channel_id, "snapshot_time": "2026-07-01T00:00:00Z", "subscriber_count": 10000, "view_count": 1000000, "video_count": 3},
            {"channel_id": channel_id, "snapshot_time": "2026-08-01T00:00:00Z", "subscriber_count": 10500, "view_count": 1200000, "video_count": 4},
        ]

    def list_channel_videos(self, channel_id, limit=100):
        return [{"video_id": "VIDEO_1", "channel_id": channel_id, "title": "냉면 먹방", "published_at": "2026-08-01T03:00:00Z", "thumbnail_high_url": "https://i.ytimg.com/vi/VIDEO_1/hqdefault.jpg"}]

    def list_channel_predictions(self, channel_id, limit=200):
        return [{"video_id": "VIDEO_1", "channel_id": channel_id, "predicted_score": 78, "predicted_at": "2026-08-01T04:00:00Z"}]

    def list_channel_labels(self, channel_id, limit=200):
        return [{"video_id": "VIDEO_1", "channel_id": channel_id, "label_score": 82, "calculated_at": "2026-08-04T04:00:00Z"}]

    def list_channel_video_snapshots(self, channel_id, limit=500):
        return [{"video_id": "VIDEO_1", "channel_id": channel_id, "target_age_hours": 72, "snapshot_time": "2026-08-04T03:00:00Z", "view_count": 1000, "like_count": 40, "comment_count": 10}]

    def get_video(self, video_id):
        for video in self.list_channel_videos("CHANNEL_A"):
            if video.get("video_id") == video_id:
                return video
        return None

    def list_channels(self, limit=500):
        return [self.get_channel("CHANNEL_A")]

    def list_videos(self, limit=1000):
        return self.list_channel_videos("CHANNEL_A")

    def list_predictions(self, limit=1000):
        return self.list_channel_predictions("CHANNEL_A")

    def list_labels(self, limit=1000):
        return self.list_channel_labels("CHANNEL_A")

    def list_video_snapshots(self, limit=2000):
        return self.list_channel_video_snapshots("CHANNEL_A")

    def list_users(self, limit=1000):
        return [{"id": "user_1", "email": "user@example.com", "role": "user", "channel_id": "CHANNEL_A"}]

    def admin_counts(self):
        return {
            "channels": 1,
            "videos": 1234,
            "predictions": 900,
            "labels": 700,
            "video_snapshots": 4321,
            "users": 1,
            "predicted_videos": 800,
            "labeled_videos": 600,
        }

    def channel_category_counts(self):
        return [{"name": "kr_mukbang", "channel_count": 1}]


class DashboardServiceTests(unittest.TestCase):
    def setUp(self):
        self.service = DashboardService(
            FakeDashboardRepository(),
            now_provider=lambda: datetime(2026, 8, 8, 12, tzinfo=timezone.utc),
        )
        self.user = {"role": "user", "channel_id": "CHANNEL_A", "channel_title": "맛있는하루"}

    def test_channel_summary_combines_containers(self):
        result = self.service.channel_summary(self.user)
        self.assertEqual(result["subscriber_count"], 10500)
        self.assertEqual(result["subscriber_growth_rate"], 5.0)
        self.assertEqual(result["view_growth_rate"], 20.0)
        self.assertEqual(result["average_engagement_rate"], 5.0)
        self.assertEqual(result["recent_videos"][0]["viral_score"], 78)
        self.assertEqual(result["channel_thumbnail_url"], "https://yt3.example/channel.jpg")
        self.assertEqual(result["channel_url"], "https://www.youtube.com/@tasty-day")
        self.assertEqual(result["recent_videos"][0]["thumbnail_url"], "https://i.ytimg.com/vi/VIDEO_1/hqdefault.jpg")
        self.assertEqual(result["recent_videos"][0]["video_url"], "https://www.youtube.com/watch?v=VIDEO_1")
        self.assertTrue(result["recent_videos"][0]["has_72h_tracking"])
        self.assertEqual(result["recent_videos"][0]["tracking_hours"], 72.0)

    def test_video_metadata_reads_title_and_thumbnail_from_videos_container(self):
        result = self.service.video_metadata("VIDEO_1")
        self.assertTrue(result["found"])
        self.assertEqual(result["video_id"], "VIDEO_1")
        self.assertEqual(result["title"], "냉면 먹방")
        self.assertEqual(
            result["thumbnail_url"],
            "https://i.ytimg.com/vi/VIDEO_1/hqdefault.jpg",
        )

    def test_video_metadata_returns_not_found_without_fabricating_values(self):
        self.assertEqual(
            self.service.video_metadata("UNKNOWN"),
            {"found": False, "video_id": "UNKNOWN"},
        )

    def test_user_cannot_request_another_channel(self):
        with self.assertRaises(DashboardAccessError):
            self.service.channel_summary(self.user, "CHANNEL_B")

    def test_admin_overview_open_to_any_authenticated_user(self):
        result = self.service.admin_overview(self.user)
        self.assertEqual(result["stats"]["channel_count"], 1)
        self.assertEqual(result["stats"]["video_count"], 1234)
        self.assertEqual(result["stats"]["snapshot_count"], 4321)
        self.assertEqual(result["stats"]["prediction_coverage"], 64.8)
        self.assertEqual(result["stats"]["label_coverage"], 48.6)
        self.assertNotIn("users", result)
        self.assertNotIn("pipeline", result)

    def test_admin_overview_video_ranking_includes_channel_context(self):
        result = self.service.admin_overview(self.user)
        ranking = result["video_ranking"]
        self.assertEqual(len(ranking), 1)
        self.assertEqual(ranking[0]["video_id"], "VIDEO_1")
        self.assertEqual(ranking[0]["viral_score"], 78)
        self.assertEqual(ranking[0]["channel_title"], "맛있는하루")
        self.assertEqual(ranking[0]["channel_thumbnail_url"], "https://yt3.example/channel.jpg")
        self.assertEqual(ranking[0]["category"], "kr_mukbang")
        self.assertEqual(ranking[0]["subscriber_count"], 234000)
        self.assertEqual(ranking[0]["published_at"], "2026-08-01T03:00:00Z")

    def test_admin_overview_video_ranking_excludes_videos_older_than_seven_days(self):
        service = DashboardService(
            FakeDashboardRepository(),
            now_provider=lambda: datetime(2026, 8, 9, 12, tzinfo=timezone.utc),
        )
        self.assertEqual(service.admin_overview(self.user)["video_ranking"], [])

    def test_admin_overview_includes_channels_without_requiring_predictions(self):
        result = self.service.admin_overview(self.user)
        channels = result["channel_benchmarks"]
        self.assertEqual(len(channels), 1)
        self.assertEqual(channels[0]["channel_id"], "CHANNEL_A")
        self.assertEqual(channels[0]["project_category"], "kr_mukbang")
        self.assertEqual(channels[0]["subscriber_count"], 234000)


if __name__ == "__main__":
    unittest.main()
