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
import search


def test_normalize_email_is_case_insensitive():
    assert (
        auth.normalize_email(
            "  User@Example.COM  "
        )
        == "user@example.com"
    )


def test_password_hash_round_trip():
    password = "KnowledgeHub123!"

    password_hash = (
        auth.hash_password(
            password
        )
    )

    assert password_hash != password

    assert auth.verify_password(
        password,
        password_hash
    ) is True


def test_password_hash_rejects_wrong_password():
    password_hash = (
        auth.hash_password(
            "CorrectPassword123!"
        )
    )

    assert auth.verify_password(
        "WrongPassword123!",
        password_hash
    ) is False


def test_password_hash_uses_unique_salt():
    password = "SamePassword123!"

    first_hash = (
        auth.hash_password(
            password
        )
    )

    second_hash = (
        auth.hash_password(
            password
        )
    )

    assert first_hash != second_hash

    assert auth.verify_password(
        password,
        first_hash
    ) is True

    assert auth.verify_password(
        password,
        second_hash
    ) is True


def test_search_documents_scopes_candidates_to_authenticated_user(
    monkeypatch
):
    fake_embedding = [
        0.1,
        0.2,
        0.3
    ]

    fake_results = [
        (
            1,
            20,
            "private.pdf",
            0,
            "Private user content.",
            0.10
        )
    ]

    class FakeCursor:
        def __init__(self):
            self.executed_query = None
            self.executed_parameters = None

        def execute(
            self,
            query,
            parameters
        ):
            self.executed_query = query
            self.executed_parameters = (
                parameters
            )

        def fetchall(self):
            return fake_results

        def __enter__(self):
            return self

        def __exit__(
            self,
            exc_type,
            exc_value,
            traceback
        ):
            pass

    class FakeConnection:
        def __init__(self):
            self.cursor_instance = (
                FakeCursor()
            )

        def cursor(self):
            return self.cursor_instance

        def __enter__(self):
            return self

        def __exit__(
            self,
            exc_type,
            exc_value,
            traceback
        ):
            pass

    fake_connection = (
        FakeConnection()
    )

    monkeypatch.setattr(
        search,
        "create_embedding",
        lambda query:
            fake_embedding
    )

    monkeypatch.setattr(
        search,
        "get_connection",
        lambda:
            fake_connection
    )

    results = search.search_documents(
        "private query",
        limit=3,
        user_id=99
    )

    assert results == fake_results

    query_text = (
        fake_connection
        .cursor_instance
        .executed_query
    )

    parameters = (
        fake_connection
        .cursor_instance
        .executed_parameters
    )

    assert "WHERE d.user_id = %s" in query_text

    assert parameters == (
        fake_embedding,
        99,
        fake_embedding,
        50
    )


def test_search_documents_without_user_id_preserves_unscoped_test_mode(
    monkeypatch
):
    fake_embedding = [
        0.4,
        0.5,
        0.6
    ]

    class FakeCursor:
        def __init__(self):
            self.executed_query = None
            self.executed_parameters = None

        def execute(
            self,
            query,
            parameters
        ):
            self.executed_query = query
            self.executed_parameters = parameters

        def fetchall(self):
            return []

        def __enter__(self):
            return self

        def __exit__(
            self,
            exc_type,
            exc_value,
            traceback
        ):
            pass

    class FakeConnection:
        def __init__(self):
            self.cursor_instance = FakeCursor()

        def cursor(self):
            return self.cursor_instance

        def __enter__(self):
            return self

        def __exit__(
            self,
            exc_type,
            exc_value,
            traceback
        ):
            pass

    fake_connection = FakeConnection()

    monkeypatch.setattr(
        search,
        "create_embedding",
        lambda query:
            fake_embedding
    )

    monkeypatch.setattr(
        search,
        "get_connection",
        lambda:
            fake_connection
    )

    result = search.search_documents(
        "test query",
        limit=3
    )

    assert result == []

    query_text = (
        fake_connection
        .cursor_instance
        .executed_query
    )

    assert "WHERE d.user_id = %s" not in query_text

    assert (
        fake_connection
        .cursor_instance
        .executed_parameters
        ==
        (
            fake_embedding,
            fake_embedding,
            50
        )
    )