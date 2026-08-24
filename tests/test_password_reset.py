import sys
from pathlib import Path

sys.path.insert(
    0,
    str(
        Path(__file__).resolve().parents[1]
        / "backend"
    )
)

import auth


def test_temporary_password_hash_is_not_plaintext():
    temporary_password = "KH-TestPassword123!"

    password_hash = auth.hash_password(
        temporary_password
    )

    assert password_hash != temporary_password
    assert auth.verify_password(
        temporary_password,
        password_hash
    ) is True


def test_wrong_temporary_password_is_rejected():
    password_hash = auth.hash_password(
        "KH-CorrectPassword123!"
    )

    assert auth.verify_password(
        "KH-WrongPassword123!",
        password_hash
    ) is False
