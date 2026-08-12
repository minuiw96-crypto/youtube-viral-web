"""Registration, password hashing, and signed login tokens."""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import re
import time
from datetime import datetime, timedelta, timezone
from typing import Any

from .settings import Settings


EMAIL_PATTERN = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
LOWERCASE_PATTERN = re.compile(r"[a-z]")
DIGIT_PATTERN = re.compile(r"[0-9]")
PBKDF2_ITERATIONS = 310_000


def _base64url_encode(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).rstrip(b"=").decode("ascii")


def _base64url_decode(value: str) -> bytes:
    return base64.urlsafe_b64decode(value + "=" * (-len(value) % 4))


class AuthError(ValueError):
    def __init__(self, message: str, status_code: int = 400, code: str = "AUTH_ERROR") -> None:
        super().__init__(message)
        self.status_code = status_code
        self.code = code


def normalize_email(value: Any) -> str:
    email = str(value or "").strip().lower()
    if not EMAIL_PATTERN.fullmatch(email):
        raise AuthError("올바른 이메일 형식을 입력해 주세요.", code="INVALID_EMAIL")
    if len(email) > 254:
        raise AuthError("이메일이 너무 깁니다.", code="INVALID_EMAIL")
    return email


def validate_password(value: Any) -> str:
    password = str(value or "")
    if len(password) < 8:
        raise AuthError("비밀번호는 8자 이상이어야 합니다.", code="WEAK_PASSWORD")
    if not LOWERCASE_PATTERN.search(password):
        raise AuthError("비밀번호에 영문 소문자를 포함해 주세요.", code="WEAK_PASSWORD")
    if not DIGIT_PATTERN.search(password):
        raise AuthError("비밀번호에 숫자를 포함해 주세요.", code="WEAK_PASSWORD")
    if len(password) > 128:
        raise AuthError("비밀번호는 128자 이하여야 합니다.", code="WEAK_PASSWORD")
    return password


def user_id_for_email(email: str) -> str:
    return "user_" + hashlib.sha256(email.encode("utf-8")).hexdigest()[:32]


def hash_password(password: str) -> tuple[str, str]:
    salt = os.urandom(16)
    derived = hashlib.pbkdf2_hmac(
        "sha256", password.encode("utf-8"), salt, PBKDF2_ITERATIONS
    )
    return base64.b64encode(salt).decode("ascii"), base64.b64encode(derived).decode("ascii")


def verify_password(password: str, salt_text: str, hash_text: str) -> bool:
    try:
        salt = base64.b64decode(salt_text)
        expected = base64.b64decode(hash_text)
    except (ValueError, TypeError):
        return False
    actual = hashlib.pbkdf2_hmac(
        "sha256", password.encode("utf-8"), salt, PBKDF2_ITERATIONS
    )
    return hmac.compare_digest(actual, expected)


def public_user(user: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": user.get("id"),
        "email": user.get("email"),
        "name": user.get("name"),
        "role": user.get("role", "user"),
        "channel_id": user.get("channel_id"),
        "channel_title": user.get("channel_title"),
        "channel_status": user.get("channel_status"),
    }


class AuthService:
    def __init__(self, repository: Any, settings: Settings | None = None) -> None:
        self.repository = repository
        self.settings = settings or Settings.from_environment()

    def register(self, body: dict[str, Any]) -> dict[str, Any]:
        email = normalize_email(body.get("email"))
        password = validate_password(body.get("password"))
        if password != str(body.get("password_confirm") or ""):
            raise AuthError("비밀번호 확인이 일치하지 않습니다.", code="PASSWORD_MISMATCH")

        name = str(body.get("name") or "").strip()
        if not name or len(name) > 100:
            raise AuthError("이름을 1자 이상 100자 이하로 입력해 주세요.", code="INVALID_NAME")
        channel_input = str(body.get("channel_name") or "").strip()
        if not channel_input or len(channel_input) > 200:
            raise AuthError("채널명을 입력해 주세요.", code="INVALID_CHANNEL_NAME")

        channel = self.repository.find_channel_by_title(channel_input)
        now = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        salt, password_hash = hash_password(password)
        user = {
            "id": user_id_for_email(email),
            "email": email,
            "name": name,
            "password_hash": password_hash,
            "password_salt": salt,
            "password_algorithm": f"pbkdf2_sha256:{PBKDF2_ITERATIONS}",
            "role": "user",
            "channel_input": channel_input,
            "channel_id": channel.get("channel_id") if channel else None,
            "channel_title": channel.get("channel_title") if channel else None,
            "channel_status": "connected" if channel else "not_found",
            "active": True,
            "created_at": now,
            "updated_at": now,
        }
        self.repository.create_user(user)
        return public_user(user)

    def login(self, body: dict[str, Any]) -> dict[str, Any]:
        email = normalize_email(body.get("email"))
        user = self.repository.get_user(user_id_for_email(email))
        password = str(body.get("password") or "")
        if not user or not verify_password(
            password, str(user.get("password_salt") or ""), str(user.get("password_hash") or "")
        ):
            raise AuthError(
                "이메일 또는 비밀번호가 올바르지 않습니다.",
                status_code=401,
                code="INVALID_CREDENTIALS",
            )
        if not user.get("active", True):
            raise AuthError("비활성화된 계정입니다.", status_code=403, code="ACCOUNT_DISABLED")
        return {"access_token": self.issue_token(user), "user": public_user(user)}

    def issue_token(self, user: dict[str, Any]) -> str:
        if not self.settings.jwt_secret:
            raise RuntimeError("JWT_SECRET 환경 변수가 설정되지 않았습니다.")
        now = int(time.time())
        payload = {
            "sub": user["id"],
            "iat": now,
            "exp": now + int(timedelta(hours=self.settings.auth_token_ttl_hours).total_seconds()),
        }
        header = {"alg": "HS256", "typ": "JWT"}
        encoded_header = _base64url_encode(
            json.dumps(header, separators=(",", ":")).encode("utf-8")
        )
        encoded_payload = _base64url_encode(
            json.dumps(payload, separators=(",", ":")).encode("utf-8")
        )
        signing_input = f"{encoded_header}.{encoded_payload}".encode("ascii")
        signature = hmac.new(
            self.settings.jwt_secret.encode("utf-8"), signing_input, hashlib.sha256
        ).digest()
        return f"{encoded_header}.{encoded_payload}.{_base64url_encode(signature)}"

    def authenticate(self, authorization: str) -> dict[str, Any]:
        if not self.settings.jwt_secret:
            raise AuthError(
                "인증 서버 설정이 완료되지 않았습니다.",
                status_code=503,
                code="AUTH_CONFIGURATION_ERROR",
            )

        parts = str(authorization or "").strip().split(maxsplit=1)
        if len(parts) != 2 or parts[0].lower() != "bearer" or not parts[1].strip():
            raise AuthError("로그인이 필요합니다.", status_code=401, code="LOGIN_REQUIRED")
        token = parts[1].strip()
        try:
            encoded_header, encoded_payload, encoded_signature = token.split(".")
            signing_input = f"{encoded_header}.{encoded_payload}".encode("ascii")
            expected = hmac.new(
                self.settings.jwt_secret.encode("utf-8"), signing_input, hashlib.sha256
            ).digest()
            if not hmac.compare_digest(expected, _base64url_decode(encoded_signature)):
                raise ValueError("signature mismatch")
            header = json.loads(_base64url_decode(encoded_header))
            payload = json.loads(_base64url_decode(encoded_payload))
            if header.get("alg") != "HS256" or not payload.get("sub"):
                raise ValueError("invalid claims")
            if int(payload.get("exp") or 0) <= int(time.time()):
                raise AuthError("로그인이 만료되었습니다.", 401, "TOKEN_EXPIRED")
        except AuthError:
            raise
        except (ValueError, TypeError, json.JSONDecodeError) as exc:
            raise AuthError("올바르지 않은 로그인 정보입니다.", 401, "INVALID_TOKEN") from exc
        user = self.repository.get_user(str(payload.get("sub") or ""))
        if not user or not user.get("active", True):
            raise AuthError("사용자 계정을 찾을 수 없습니다.", 401, "INVALID_TOKEN")
        return user
