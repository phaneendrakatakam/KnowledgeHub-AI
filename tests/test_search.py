import sys
from pathlib import Path

sys.path.insert(
    0,
    str(
        Path(__file__).resolve().parents[1]
        / "backend"
    )
)

import search


def test_search_documents_returns_database_results(
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
            10,
            "test.pdf",
            0,
            "KnowledgeHub test content",
            0.15,
        ),
        (
            2,
            10,
            "test.pdf",
            1,
            "More test content",
            0.25,
        ),
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

    def fake_get_connection():
        return fake_connection

    def fake_create_embedding(
        query
    ):
        assert (
            query
            == "What is KnowledgeHub?"
        )
        return fake_embedding

    monkeypatch.setattr(
        search,
        "create_embedding",
        fake_create_embedding
    )

    monkeypatch.setattr(
        search,
        "get_connection",
        fake_get_connection
    )

    result = (
        search.search_documents(
            "What is KnowledgeHub?",
            limit=3
        )
    )

    assert result == fake_results

    # V3 retrieves a wider semantic
    # candidate pool before reranking.
    assert (
        fake_connection
        .cursor_instance
        .executed_parameters
        ==
        (
            fake_embedding,
            fake_embedding,
            50,
        )
    )


def test_search_documents_uses_wider_candidate_pool(
    monkeypatch
):
    fake_embedding = [
        0.5,
        0.6,
        0.7
    ]

    fake_results = [
        (
            1,
            20,
            "document.pdf",
            0,
            "Test content",
            0.10,
        ),
    ]

    class FakeCursor:
        def __init__(self):
            self.executed_parameters = None

        def execute(
            self,
            query,
            parameters
        ):
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

    result = (
        search.search_documents(
            "test query",
            limit=5
        )
    )

    assert result == fake_results

    # Final result limit is 5, but
    # the database candidate pool is 50.
    assert (
        fake_connection
        .cursor_instance
        .executed_parameters
        ==
        (
            fake_embedding,
            fake_embedding,
            50,
        )
    )


def test_search_documents_respects_limit_above_candidate_floor(
    monkeypatch
):
    fake_embedding = [
        0.2,
        0.4,
        0.6
    ]

    fake_results = []

    class FakeCursor:
        def __init__(self):
            self.executed_parameters = None

        def execute(
            self,
            query,
            parameters
        ):
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

    result = (
        search.search_documents(
            "large candidate request",
            limit=60
        )
    )

    assert result == []

    assert (
        fake_connection
        .cursor_instance
        .executed_parameters
        ==
        (
            fake_embedding,
            fake_embedding,
            60,
        )
    )


def test_search_documents_returns_only_requested_limit(
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
            30,
            "doc.pdf",
            0,
            "Pipeline as Code using Jenkinsfile.",
            0.40,
        ),
        (
            2,
            30,
            "doc.pdf",
            1,
            "General pipeline information.",
            0.20,
        ),
        (
            3,
            30,
            "doc.pdf",
            2,
            "Another unrelated chunk.",
            0.10,
        ),
    ]

    class FakeCursor:
        def execute(
            self,
            query,
            parameters
        ):
            pass

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
        def cursor(self):
            return FakeCursor()

        def __enter__(self):
            return self

        def __exit__(
            self,
            exc_type,
            exc_value,
            traceback
        ):
            pass

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
            FakeConnection()
    )

    result = (
        search.search_documents(
            "What is Pipeline as Code?",
            limit=2
        )
    )

    assert len(result) == 2

    # Exact lexical match should be
    # promoted by hybrid reranking.
    assert result[0][3] == 0


def test_search_documents_returns_empty_results(
    monkeypatch
):
    fake_embedding = [
        0.1,
        0.2,
        0.3
    ]

    class FakeCursor:
        def execute(
            self,
            query,
            parameters
        ):
            pass

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
        def cursor(self):
            return FakeCursor()

        def __enter__(self):
            return self

        def __exit__(
            self,
            exc_type,
            exc_value,
            traceback
        ):
            pass

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
            FakeConnection()
    )

    result = (
        search.search_documents(
            "query with no matches"
        )
    )

    assert result == []