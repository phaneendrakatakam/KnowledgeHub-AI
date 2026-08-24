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


class FakeUploadFile:
    def __init__(
        self,
        filename,
        chunks
    ):
        self.filename = filename
        self._chunks = list(
            chunks
        )
        self.closed = False

    async def read(
        self,
        size
    ):
        if not self._chunks:
            return b""

        return self._chunks.pop(0)

    async def close(self):
        self.closed = True


class DummyLock:
    pass


def _patch_upload_environment(
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
            DummyLock()
    )

    monkeypatch.setattr(
        main,
        "release_document_upload_lock",
        lambda connection, user_id, filename:
            None
    )


def test_unsupported_upload_type_is_415(
    tmp_path
):
    file = FakeUploadFile(
        "notes.exe",
        [
            b"not relevant"
        ]
    )

    with pytest.raises(
        HTTPException
    ) as error:
        asyncio.run(
            main.upload_document(
                file,
                current_user={
                    "id": 7
                }
            )
        )

    assert (
        error.value.status_code
        == 415
    )


def test_empty_upload_is_400(
    monkeypatch,
    tmp_path
):
    _patch_upload_environment(
        monkeypatch,
        tmp_path
    )

    file = FakeUploadFile(
        "empty.txt",
        []
    )

    with pytest.raises(
        HTTPException
    ) as error:
        asyncio.run(
            main.upload_document(
                file,
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
        == "The uploaded file is empty."
    )

    assert file.closed is True


def test_oversized_upload_is_413(
    monkeypatch,
    tmp_path
):
    _patch_upload_environment(
        monkeypatch,
        tmp_path
    )

    monkeypatch.setattr(
        main,
        "MAX_UPLOAD_SIZE_BYTES",
        4
    )

    file = FakeUploadFile(
        "too_big.txt",
        [
            b"12345"
        ]
    )

    with pytest.raises(
        HTTPException
    ) as error:
        asyncio.run(
            main.upload_document(
                file,
                current_user={
                    "id": 7
                }
            )
        )

    assert (
        error.value.status_code
        == 413
    )

    assert file.closed is True

    assert not any(
        tmp_path.iterdir()
    )


def test_unexpected_ingestion_error_returns_sanitized_500(
    monkeypatch,
    tmp_path
):
    _patch_upload_environment(
        monkeypatch,
        tmp_path
    )

    def fail_processing(
        file_path
    ):
        raise RuntimeError(
            "postgresql://secret-user:"
            "secret-password@localhost/"
            "knowledgehub"
        )

    monkeypatch.setattr(
        main,
        "prepare_document_for_ingestion",
        fail_processing
    )

    file = FakeUploadFile(
        "policy.txt",
        [
            b"valid non-empty content"
        ]
    )

    with pytest.raises(
        HTTPException
    ) as error:
        asyncio.run(
            main.upload_document(
                file,
                current_user={
                    "id": 7
                }
            )
        )

    assert (
        error.value.status_code
        == 500
    )

    assert (
        error.value.detail
        == "Document upload or ingestion failed."
    )

    assert (
        "secret-password"
        not in error.value.detail
    )

    assert file.closed is True
