import sys
from pathlib import Path

sys.path.insert(
    0,
    str(
        Path(__file__).resolve().parents[1]
        / "backend"
    )
)

import main
import rag


# ============================================================
# GROUNDED REJECTION TEST
# ============================================================


def test_grounded_rejection_returns_no_sources(
    monkeypatch
):
    """
    A retrieved chunk may pass the vector similarity threshold
    while still not containing enough evidence to answer the
    user's question.

    If Gemini performs the final answerability check and rejects
    the question, KnowledgeHub must not expose those candidate
    chunks as supporting sources.
    """

    fake_results = [
        (
            101,
            20,
            "cicd.pdf",
            21,
            (
                "CI/CD automation tools include Jenkins, "
                "GitHub Actions, GitLab CI/CD and Azure DevOps."
            ),
            0.3346
        )
    ]

    class FakeResponse:
        text = rag.REJECTION_ANSWER

    class FakeModels:

        def generate_content(
            self,
            model,
            contents
        ):
            return FakeResponse()

    class FakeClient:
        models = FakeModels()

    monkeypatch.setattr(
        rag,
        "search_documents",
        lambda query, limit: fake_results
    )

    monkeypatch.setattr(
        rag,
        "client",
        FakeClient()
    )

    result = rag.generate_answer(
        "Does Jenkins belong to Microsoft?"
    )

    assert result["answer"] == (
        rag.REJECTION_ANSWER
    )

    assert result["sources"] == []


# ============================================================
# SOURCE EVIDENCE ENDPOINT TESTS
# ============================================================


class FakeCursor:
    """
    Minimal fake database cursor used by the source-evidence
    endpoint tests.
    """

    def __init__(
        self,
        row
    ):
        self.row = row

        self.executed_query = None
        self.executed_params = None

    def __enter__(
        self
    ):
        return self

    def __exit__(
        self,
        exc_type,
        exc_value,
        traceback
    ):
        return False

    def execute(
        self,
        query,
        params=None
    ):
        self.executed_query = query
        self.executed_params = params

    def fetchone(
        self
    ):
        return self.row


class FakeConnection:
    """
    Minimal fake database connection.
    """

    def __init__(
        self,
        row
    ):
        self.cursor_instance = (
            FakeCursor(
                row
            )
        )

    def __enter__(
        self
    ):
        return self

    def __exit__(
        self,
        exc_type,
        exc_value,
        traceback
    ):
        return False

    def cursor(
        self
    ):
        return self.cursor_instance


def test_get_document_chunk_returns_evidence(
    monkeypatch
):
    """
    The V2 source-evidence endpoint should return the stored
    document passage together with its identifying metadata.
    """

    fake_row = (
        201,
        10,
        "CI_CD_Pipeline_Complete_Guide.pdf",
        3,
        (
            "Continuous Delivery usually requires "
            "human approval before production."
        )
    )

    fake_connection = (
        FakeConnection(
            fake_row
        )
    )

    monkeypatch.setattr(
        main,
        "get_connection",
        lambda: fake_connection
    )

    result = main.get_document_chunk(
        document_id=10,
        chunk_index=3
    )

    assert result == {
        "success": True,
        "chunk_id": 201,
        "document_id": 10,
        "filename": (
            "CI_CD_Pipeline_Complete_Guide.pdf"
        ),
        "chunk_index": 3,
        "content": (
            "Continuous Delivery usually requires "
            "human approval before production."
        )
    }

    assert (
        fake_connection
        .cursor_instance
        .executed_params
        == (
            10,
            3
        )
    )


def test_get_document_chunk_when_not_found(
    monkeypatch
):
    """
    A request for a chunk that does not exist should return a
    clean application response rather than inventing evidence.
    """

    fake_connection = (
        FakeConnection(
            None
        )
    )

    monkeypatch.setattr(
        main,
        "get_connection",
        lambda: fake_connection
    )

    result = main.get_document_chunk(
        document_id=999,
        chunk_index=99
    )

    assert result == {
        "success": False,
        "message": (
            "Supporting document passage "
            "not found."
        )
    }

    assert (
        fake_connection
        .cursor_instance
        .executed_params
        == (
            999,
            99
        )
    )