import sys
from pathlib import Path

sys.path.insert(
    0,
    str(
        Path(__file__).resolve().parents[1]
        / "backend"
    )
)

import rag
import main


class FakeCursor:
    def __init__(
        self,
        row
    ):
        self.row = row
        self.executed_query = None
        self.executed_parameters = None

    def execute(
        self,
        query,
        parameters
    ):
        self.executed_query = query
        self.executed_parameters = parameters

    def fetchone(self):
        return self.row

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
    def __init__(
        self,
        row
    ):
        self.cursor_instance = (
            FakeCursor(
                row
            )
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


def test_grounded_rejection_returns_no_sources(
    monkeypatch
):
    """
    A retrieved candidate can be relevant while still
    lacking enough evidence to answer the user's claim.

    Gemini's evidence check must reject the answer and
    KnowledgeHub must not expose candidate chunks as
    supporting sources.
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
        lambda query, limit, user_id=None:
            fake_results
    )

    monkeypatch.setattr(
        rag,
        "client",
        FakeClient()
    )

    result = rag.generate_answer(
        "Does Jenkins belong to Microsoft?"
    )

    assert (
        result["answer"]
        == rag.REJECTION_ANSWER
    )

    assert result["sources"] == []


def test_get_document_chunk_returns_evidence(
    monkeypatch
):
    """
    The source-evidence endpoint must return a stored
    passage only when it belongs to the authenticated user.
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
        lambda:
            fake_connection
    )

    result = main.get_document_chunk(
        document_id=10,
        chunk_index=3,
        current_user={
            "id": 7,
            "name": "Test User",
            "email": "test@example.com"
        }
    )

    assert result["success"] is True
    assert result["chunk_id"] == 201
    assert result["document_id"] == 10

    assert (
        result["filename"]
        == "CI_CD_Pipeline_Complete_Guide.pdf"
    )

    assert result["file_type"] == "PDF"
    assert result["chunk_index"] == 3

    assert (
        "human approval"
        in result["content"]
    )

    parameters = (
        fake_connection
        .cursor_instance
        .executed_parameters
    )

    assert parameters == (
        10,
        3,
        7
    )

    assert (
        "d.user_id = %s"
        in fake_connection
        .cursor_instance
        .executed_query
    )


def test_get_document_chunk_when_not_found(
    monkeypatch
):
    """
    A missing or unauthorized source passage returns the
    same safe not-found response rather than exposing data.
    """

    fake_connection = (
        FakeConnection(
            None
        )
    )

    monkeypatch.setattr(
        main,
        "get_connection",
        lambda:
            fake_connection
    )

    result = main.get_document_chunk(
        document_id=999,
        chunk_index=99,
        current_user={
            "id": 8,
            "name": "Other User",
            "email": "other@example.com"
        }
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
        .executed_parameters
        ==
        (
            999,
            99,
            8
        )
    )