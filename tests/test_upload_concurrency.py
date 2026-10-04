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
        row
    ):
        self.row = row
        self.executed = []

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
        self.executed.append(
            (
                query,
                params
            )
        )

    def fetchone(self):
        return self.row


class FakeConnection:
    def __init__(
        self,
        row
    ):
        self.cursor_object = (
            FakeCursor(
                row
            )
        )
        self.autocommit = False
        self.closed = False

    def cursor(self):
        return self.cursor_object

    def close(self):
        self.closed = True


def test_upload_lock_key_is_user_and_filename_scoped():
    assert (
        main._document_upload_lock_key(
            7,
            "Policy.PDF"
        )
        ==
        "knowledgehub-upload:7:policy.pdf"
    )

    assert (
        main._document_upload_lock_key(
            8,
            "Policy.PDF"
        )
        !=
        main._document_upload_lock_key(
            7,
            "Policy.PDF"
        )
    )


def test_acquire_upload_lock_returns_connection_when_available(
    monkeypatch
):
    connection = (
        FakeConnection(
            (True,)
        )
    )

    monkeypatch.setattr(
        main,
        "get_connection",
        lambda:
            connection
    )

    result = (
        main.acquire_document_upload_lock(
            7,
            "policy.pdf"
        )
    )

    assert result is connection
    assert connection.autocommit is True
    assert connection.closed is False


def test_acquire_upload_lock_returns_none_when_busy(
    monkeypatch
):
    connection = (
        FakeConnection(
            (False,)
        )
    )

    monkeypatch.setattr(
        main,
        "get_connection",
        lambda:
            connection
    )

    result = (
        main.acquire_document_upload_lock(
            7,
            "policy.pdf"
        )
    )

    assert result is None
    assert connection.closed is True


def test_release_upload_lock_closes_connection():
    connection = (
        FakeConnection(
            (True,)
        )
    )

    main.release_document_upload_lock(
        connection,
        7,
        "policy.pdf"
    )

    assert connection.closed is True


class FakeUploadFile:
    filename = "policy.pdf"

    async def read(
        self,
        size
    ):
        return b""

    async def close(self):
        return None


def test_busy_same_document_upload_is_409(
    monkeypatch,
    tmp_path
):
    monkeypatch.setattr(
        main,
        "get_user_documents_dir",
        lambda user_id:
            tmp_path
    )

    monkeypatch.setattr(
        main,
        "acquire_document_upload_lock",
        lambda user_id, filename:
            None
    )

    with pytest.raises(
        HTTPException
    ) as error:
        asyncio.run(
            main.upload_document(
                FakeUploadFile(),
                current_user={
                    "id": 7
                }
            )
        )

    assert (
        error.value.status_code
        == 409
    )

    assert (
        "already in progress"
        in error.value.detail
    )
