import unittest
from types import SimpleNamespace

from shared.auth_service import AuthError, AuthService, normalize_email, validate_password


class FakeUserRepository:
    def __init__(self, channel=None):
        self.channel = channel
        self.users = {}

    def find_channel_by_title(self, title):
        return self.channel if self.channel and self.channel["channel_title"].casefold() == title.casefold() else None

    def create_user(self, user):
        if user["id"] in self.users:
            raise AuthError("이미 가입된 이메일입니다.", 409, "EMAIL_EXISTS")
        self.users[user["id"]] = user
        return user

    def get_user(self, user_id):
        return self.users.get(user_id)


class AuthValidationTests(unittest.TestCase):
    def test_email_and_password_rules(self):
        self.assertEqual(normalize_email(" User@Example.COM "), "user@example.com")
        self.assertEqual(validate_password("sample123"), "sample123")
        for invalid in ("no-number", "12345678", "abc123"):
            with self.assertRaises(AuthError):
                validate_password(invalid)


class AuthServiceTests(unittest.TestCase):
    def setUp(self):
        self.repository = FakeUserRepository(
            {"channel_id": "UC_SAMPLE", "channel_title": "Sample Channel"}
        )
        self.service = AuthService(
            self.repository,
            SimpleNamespace(jwt_secret="test-secret-that-is-long-enough", auth_token_ttl_hours=24),
        )

    def test_registered_channel_title_is_resolved_server_side(self):
        user = self.service.register(
            {
                "email": "user@example.com",
                "name": "사용자",
                "password": "sample123",
                "password_confirm": "sample123",
                "channel_name": "sample channel",
                "role": "admin",
                "channel_id": "OTHER",
            }
        )
        self.assertEqual(user["role"], "user")
        self.assertEqual(user["channel_id"], "UC_SAMPLE")

    def test_unknown_channel_is_stored_as_null(self):
        self.repository.channel = None
        user = self.service.register(
            {
                "email": "new@example.com",
                "name": "사용자",
                "password": "sample123",
                "password_confirm": "sample123",
                "channel_name": "없는 채널",
            }
        )
        self.assertIsNone(user["channel_id"])
        self.assertEqual(user["channel_status"], "not_found")

    def test_login_token_authenticates_user(self):
        self.service.register(
            {
                "email": "login@example.com",
                "name": "로그인 사용자",
                "password": "sample123",
                "password_confirm": "sample123",
                "channel_name": "Sample Channel",
            }
        )
        login = self.service.login({"email": "login@example.com", "password": "sample123"})
        authenticated = self.service.authenticate("Bearer " + login["access_token"])
        self.assertEqual(authenticated["email"], "login@example.com")

    def test_bearer_scheme_is_case_insensitive(self):
        self.service.register(
            {
                "email": "lowercase@example.com",
                "name": "로그인 사용자",
                "password": "sample123",
                "password_confirm": "sample123",
                "channel_name": "Sample Channel",
            }
        )
        login = self.service.login(
            {"email": "lowercase@example.com", "password": "sample123"}
        )
        authenticated = self.service.authenticate(
            "bearer " + login["access_token"]
        )
        self.assertEqual(authenticated["channel_id"], "UC_SAMPLE")

    def test_authentication_reads_current_user_scope_from_repository(self):
        self.service.register(
            {
                "email": "scope@example.com",
                "name": "범위 사용자",
                "password": "sample123",
                "password_confirm": "sample123",
                "channel_name": "Sample Channel",
            }
        )
        login = self.service.login({"email": "scope@example.com", "password": "sample123"})
        user = self.repository.users[login["user"]["id"]]
        user["channel_id"] = "UC_CHANGED"
        user["channel_title"] = "Changed Channel"

        authenticated = self.service.authenticate("Bearer " + login["access_token"])
        self.assertEqual(authenticated["channel_id"], "UC_CHANGED")

    def test_missing_or_tampered_token_is_rejected(self):
        with self.assertRaises(AuthError) as missing:
            self.service.authenticate("")
        self.assertEqual(missing.exception.code, "LOGIN_REQUIRED")

        self.service.register(
            {
                "email": "tampered@example.com",
                "name": "토큰 사용자",
                "password": "sample123",
                "password_confirm": "sample123",
                "channel_name": "Sample Channel",
            }
        )
        login = self.service.login({"email": "tampered@example.com", "password": "sample123"})
        token = login["access_token"]
        tampered = token[:-1] + ("A" if token[-1] != "A" else "B")
        with self.assertRaises(AuthError) as invalid:
            self.service.authenticate("Bearer " + tampered)
        self.assertEqual(invalid.exception.code, "INVALID_TOKEN")

    def test_disabled_account_is_rejected_after_token_was_issued(self):
        self.service.register(
            {
                "email": "disabled@example.com",
                "name": "비활성 사용자",
                "password": "sample123",
                "password_confirm": "sample123",
                "channel_name": "Sample Channel",
            }
        )
        login = self.service.login({"email": "disabled@example.com", "password": "sample123"})
        self.repository.users[login["user"]["id"]]["active"] = False
        with self.assertRaises(AuthError) as disabled:
            self.service.authenticate("Bearer " + login["access_token"])
        self.assertEqual(disabled.exception.code, "INVALID_TOKEN")


if __name__ == "__main__":
    unittest.main()
