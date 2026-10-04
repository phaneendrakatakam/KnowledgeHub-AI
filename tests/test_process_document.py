import sys
from pathlib import Path

import fitz

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

import process_document
from process_document import create_chunks, extract_text


def test_create_chunks_returns_empty_list_for_empty_text():
    result = create_chunks("")

    assert result == []


def test_create_chunks_returns_single_chunk_for_short_text():
    text = "Hello KnowledgeHub"

    result = create_chunks(text)

    assert len(result) == 1
    assert result[0] == text


def test_create_chunks_respects_chunk_size():
    text = "A" * 2500

    result = create_chunks(text)

    assert all(len(chunk) <= 1000 for chunk in result)


def test_create_chunks_preserves_overlap():
    text = "".join(str(i % 10) for i in range(2000))

    result = create_chunks(text)

    assert len(result) >= 2
    assert result[0][-300:] == result[1][:300]


def test_create_chunks_ignores_whitespace_only_text():
    result = create_chunks("   \n\n   ")

    assert result == []


def test_extract_text_from_pdf(tmp_path):
    pdf_path = tmp_path / "test_document.pdf"

    document = fitz.open()

    page = document.new_page()

    page.insert_text(
        (72, 72),
        "KnowledgeHub AI test document"
    )

    document.save(pdf_path)
    document.close()

    result = extract_text(str(pdf_path))

    assert "KnowledgeHub AI test document" in result


def test_process_document_returns_chunks_with_embeddings(
    tmp_path,
    monkeypatch
):
    pdf_path = tmp_path / "test_document.pdf"

    document = fitz.open()

    page = document.new_page()

    page.insert_text(
        (72, 72),
        "KnowledgeHub AI processing test document"
    )

    document.save(pdf_path)
    document.close()

    def fake_create_embedding(text):
        return [0.1, 0.2, 0.3]

    monkeypatch.setattr(
        process_document,
        "create_embedding",
        fake_create_embedding
    )

    result = process_document.process_document(
        str(pdf_path)
    )

    assert len(result) == 1

    assert result[0]["chunk_id"] == 0

    assert (
        "KnowledgeHub AI processing test document"
        in result[0]["text"]
    )

    assert result[0]["embedding"] == [
        0.1,
        0.2,
        0.3
    ]


def test_process_document_creates_embedding_for_each_chunk(
    tmp_path,
    monkeypatch
):
    pdf_path = tmp_path / "large_test_document.pdf"

    document = fitz.open()

    for _ in range(5):
        page = document.new_page()

        page.insert_textbox(
            fitz.Rect(50, 50, 550, 750),
            "KnowledgeHub AI test content. " * 100
        )

    document.save(pdf_path)
    document.close()

    embedding_calls = []

    def fake_create_embedding(text):
        embedding_calls.append(text)
        return [0.1, 0.2, 0.3]

    monkeypatch.setattr(
        process_document,
        "create_embedding",
        fake_create_embedding
    )

    result = process_document.process_document(
        str(pdf_path)
    )

    assert len(result) == len(embedding_calls)

    assert len(result) > 1

    for index, item in enumerate(result):
        assert item["chunk_id"] == index
        assert item["embedding"] == [
            0.1,
            0.2,
            0.3
        ]