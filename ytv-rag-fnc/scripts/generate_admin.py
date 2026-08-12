"""Generate a password-hashed admin item for manual Cosmos DB insertion."""

from __future__ import annotations

import getpass
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from shared.auth_service import (  # noqa: E402
    PBKDF2_ITERATIONS,
    hash_password,
    normalize_email,
    user_id_for_email,
    validate_password,
)


def main() -> None:
    email = normalize_email(input("관리자 이메일: "))
    name = input("관리자 이름: ").strip()
    if not name:
        raise SystemExit("관리자 이름을 입력해야 합니다.")
    password = validate_password(getpass.getpass("관리자 비밀번호: "))
    if password != getpass.getpass("비밀번호 확인: "):
        raise SystemExit("비밀번호 확인이 일치하지 않습니다.")

    salt, password_hash = hash_password(password)
    now = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    document = {
        "id": user_id_for_email(email),
        "email": email,
        "name": name,
        "password_hash": password_hash,
        "password_salt": salt,
        "password_algorithm": f"pbkdf2_sha256:{PBKDF2_ITERATIONS}",
        "role": "admin",
        "channel_input": None,
        "channel_id": None,
        "channel_title": None,
        "channel_status": "admin_all_access",
        "active": True,
        "created_at": now,
        "updated_at": now,
    }
    print("\n아래 JSON을 ytv-app-db/users의 New Item에 붙여 넣으세요.\n")
    print(json.dumps(document, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
