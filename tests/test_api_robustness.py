import asyncio
import sys
from pathlib import Path

import pytest
from fastapi import HTTPException


sys.path.insert(
    0,
    str(
        Path(__file__).resolve().parents[1]
        / "backend"
    )
)

import main


class FakeCursor:
    def __init__(
        self,
        fetchone_value=None
    ):
        self.fetchone_value = (
            fetchone_value
        )

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
        return None

    def fetchone(self):
        return self.fetchone_value


class FakeConnection:
    def __init__(
        self,
        fetchone_value=None
    ):
        self.cursor_object = (
            FakeCursor(
                fetchone_value
            )
        )

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
        return self.cursor_object

    def commit(self):
        return None


def test_delete_document_not_found_is_404(
    monkeypatch
):
    monkeypatch.setattr(
        main,
        "get_connection",
        lambda:
            FakeConnection(None)
    )

    with pytest.raises(
        HTTPException
    ) as error:
        main.delete_document(
            document_id=999,
            current_user={
                "id": 7
            }
        )

    assert (
        error.value.status_code
        == 404
    )

    assert (
        error.value.detail
        == "Document not found."
    )


def test_get_chat_not_found_is_404(
    monkeypatch
):
    monkeypatch.setattr(
        main,
        "get_connection",
        lambda:
            FakeConnection(None)
    )

    with pytest.raises(
        HTTPException
    ) as error:
        main.get_chat(
            session_id=999,
            current_user={
                "id": 7
            }
        )

    assert (
        error.value.status_code
        == 404
    )


def test_delete_chat_not_found_is_404(
    monkeypatch
):
    monkeypatch.setattr(
        main,
        "get_connection",
        lambda:
            FakeConnection(None)
    )

    with pytest.raises(
        HTTPException
    ) as error:
        main.delete_chat(
            session_id=999,
            current_user={
                "id": 7
            }
        )

    assert (
        error.value.status_code
        == 404
    )


def test_empty_question_is_400():
    with pytest.raises(
        HTTPException
    ) as error:
        asyncio.run(
            main.ask_question(
                {
                    "question": "   "
                },
                current_user={
                    "id": 7
                }
            )
        )

    assert (
        error.value.status_code
        == 400
    )

    assert (
        error.value.detail
        == "Please provide a question."
    )
