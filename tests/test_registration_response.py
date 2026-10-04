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


class FakeCursor:
    def __init__(self):
        self.results = [
            (0,),       # SELECT COUNT(*) FROM users
            None,       # duplicate email lookup
            (
                1,
                "Admin",
                "admin@example.com",
                "2026-08-23",
                "admin",
                True,
                None,
                False,
            ),
        ]

    def __enter__(self):
        return self

    def __exit__(
        self,
        exc_type,
        exc,
        tb
    ):
        return False

    def execute(
        self,
        query,
        params=None
    ):
        pass

    def fetchone(self):
        return self.results.pop(0)


class FakeConnection:
    def __init__(self):
        self.cursor_instance = FakeCursor()

    def __enter__(self):
        return self

    def __exit__(
        self,
        exc_type,
        exc,
        tb
    ):
        return False

    def cursor(self):
        return self.cursor_instance

    def commit(self):
        pass


def test_first_user_registration_returns_complete_user(
    monkeypatch
):
    monkeypatch.setattr(
        auth,
        "get_connection",
        lambda: FakeConnection()
    )

    user, is_first_user = auth.register_user(
        "Admin",
        "admin@example.com",
        "password123"
    )

    assert is_first_user is True

    assert user["id"] == 1
    assert user["email"] == "admin@example.com"
    assert user["role"] == "admin"
    assert user["is_active"] is True
    assert user["must_change_password"] is False