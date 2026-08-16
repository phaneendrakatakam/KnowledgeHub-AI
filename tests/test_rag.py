import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

import rag


def test_generate_answer_when_no_results(monkeypatch):
    monkeypatch.setattr(
        rag,
        "search_documents",
        lambda query, limit: []
    )

    result = rag.generate_answer("Unknown question")

    assert result == {
        "answer": "I couldn't find relevant information in the knowledge base.",
        "sources": []
    }


def test_generate_answer_when_results_are_not_relevant(monkeypatch):
    fake_results = [
        (
            1,
            10,
            "test.pdf",
            0,
            "Some unrelated content",
            0.75
        ),
        (
            2,
            10,
            "test.pdf",
            1,
            "More unrelated content",
            0.60
        )
    ]

    monkeypatch.setattr(
        rag,
        "search_documents",
        lambda query, limit: fake_results
    )

    result = rag.generate_answer("Question with no relevant answer")

    assert result == {
        "answer": "I couldn't find that information in the provided documents.",
        "sources": []
    }


def test_generate_answer_uses_relevant_results(monkeypatch):
    fake_results = [
        (
            1,
            10,
            "story.pdf",
            0,
            "The boy received the Hanuman idol from his grandfather.",
            0.20
        )
    ]

    class FakeResponse:
        text = "The boy received the Hanuman idol from his grandfather."

    class FakeModels:
        def __init__(self):
            self.received_prompt = None

        def generate_content(self, model, contents):
            self.received_prompt = contents

            assert model == "gemini-3.1-flash-lite"

            return FakeResponse()

    fake_models = FakeModels()

    class FakeClient:
        models = fake_models

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
        "Who gave the boy the Hanuman idol?"
    )

    assert result["answer"] == (
        "The boy received the Hanuman idol from his grandfather."
    )

    assert result["sources"] == [
        {
            "document_id": 10,
            "filename": "story.pdf",
            "chunk_index": 0,
            "relevance": 0.8
        }
    ]

    assert "story.pdf" in fake_models.received_prompt

    assert (
        "The boy received the Hanuman idol from his grandfather."
        in fake_models.received_prompt
    )

    assert "Who gave the boy the Hanuman idol?" in fake_models.received_prompt


def test_generate_answer_filters_irrelevant_results(monkeypatch):
    fake_results = [
        (
            1,
            10,
            "relevant.pdf",
            0,
            "Relevant information",
            0.25
        ),
        (
            2,
            10,
            "irrelevant.pdf",
            1,
            "Irrelevant information",
            0.65
        )
    ]

    class FakeResponse:
        text = "Relevant information"

    class FakeModels:
        def __init__(self):
            self.received_prompt = None

        def generate_content(self, model, contents):
            self.received_prompt = contents
            return FakeResponse()

    fake_models = FakeModels()

    class FakeClient:
        models = fake_models

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

    result = rag.generate_answer("test question")

    assert result["answer"] == "Relevant information"

    assert result["sources"] == [
        {
            "document_id": 10,
            "filename": "relevant.pdf",
            "chunk_index": 0,
            "relevance": 0.75
        }
    ]

    assert "relevant.pdf" in fake_models.received_prompt
    assert "irrelevant.pdf" not in fake_models.received_prompt


def test_generate_answer_returns_multiple_sources(monkeypatch):
    fake_results = [
        (
            1,
            10,
            "first.pdf",
            0,
            "First relevant document content.",
            0.10
        ),
        (
            2,
            20,
            "second.pdf",
            2,
            "Second relevant document content.",
            0.30
        )
    ]

    class FakeResponse:
        text = "Combined answer from both documents."

    class FakeModels:
        def __init__(self):
            self.received_prompt = None

        def generate_content(self, model, contents):
            self.received_prompt = contents
            return FakeResponse()

    fake_models = FakeModels()

    class FakeClient:
        models = fake_models

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

    result = rag.generate_answer("combined question")

    assert result["answer"] == "Combined answer from both documents."

    assert result["sources"] == [
        {
            "document_id": 10,
            "filename": "first.pdf",
            "chunk_index": 0,
            "relevance": 0.9
        },
        {
            "document_id": 20,
            "filename": "second.pdf",
            "chunk_index": 2,
            "relevance": 0.7
        }
    ]

    assert "first.pdf" in fake_models.received_prompt
    assert "second.pdf" in fake_models.received_prompt
    assert "First relevant document content." in fake_models.received_prompt
    assert "Second relevant document content." in fake_models.received_prompt