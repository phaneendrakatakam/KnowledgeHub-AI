import sys
from pathlib import Path
from types import SimpleNamespace

import pytest


sys.path.insert(
    0,
    str(
        Path(__file__).resolve().parents[1]
        / "backend"
    )
)


import rag


def make_result(
    chunk_id=1,
    document_id=10,
    filename="test.pdf",
    chunk_index=0,
    content="Relevant document content.",
    distance=0.20
):
    return (
        chunk_id,
        document_id,
        filename,
        chunk_index,
        content,
        distance
    )


def mock_gemini_response(
    monkeypatch,
    text
):
    def fake_generate_content(
        *args,
        **kwargs
    ):
        return SimpleNamespace(
            text=text
        )

    monkeypatch.setattr(
        rag.client.models,
        "generate_content",
        fake_generate_content
    )


def test_generate_answer_when_no_results(
    monkeypatch
):
    monkeypatch.setattr(
        rag,
        "search_documents",
        lambda query, limit, user_id=None: []
    )

    result = rag.generate_answer(
        "What is Jenkins?"
    )

    assert result == {
        "answer":
            rag.NO_RESULTS_ANSWER,
        "sources":
            []
    }


def test_generate_answer_when_results_are_not_relevant(
    monkeypatch
):
    results = [
        make_result(
            distance=0.70
        )
    ]

    monkeypatch.setattr(
        rag,
        "search_documents",
        lambda query, limit, user_id=None: results
    )

    result = rag.generate_answer(
        "What is Jenkins?"
    )

    assert result == {
        "answer":
            rag.REJECTION_ANSWER,
        "sources":
            []
    }


def test_generate_answer_uses_relevant_results(
    monkeypatch
):
    results = [
        make_result(
            chunk_id=101,
            document_id=20,
            filename="jenkins_guide.txt",
            chunk_index=0,
            content=(
                "Jenkins is an open-source "
                "automation server."
            ),
            distance=0.20
        )
    ]

    monkeypatch.setattr(
        rag,
        "search_documents",
        lambda query, limit, user_id=None: results
    )

    mock_gemini_response(
        monkeypatch,
        (
            "Jenkins is an open-source "
            "automation server."
        )
    )

    result = rag.generate_answer(
        "What is Jenkins?"
    )

    assert result["answer"] == (
        "Jenkins is an open-source "
        "automation server."
    )

    assert len(
        result["sources"]
    ) == 1

    source = result["sources"][0]

    assert source[
        "document_id"
    ] == 20

    assert source[
        "filename"
    ] == "jenkins_guide.txt"

    assert source[
        "chunk_index"
    ] == 0

    assert source[
        "relevance"
    ] == pytest.approx(
        0.86
    )


def test_generate_answer_filters_irrelevant_results(
    monkeypatch
):
    results = [
        make_result(
            filename="relevant.pdf",
            content="Supported information.",
            distance=0.25
        ),
        make_result(
            filename="irrelevant.pdf",
            content="Unrelated information.",
            distance=0.80
        )
    ]

    monkeypatch.setattr(
        rag,
        "search_documents",
        lambda query, limit, user_id=None: results
    )

    mock_gemini_response(
        monkeypatch,
        "Supported answer."
    )

    result = rag.generate_answer(
        "Explain the supported information."
    )

    assert result[
        "answer"
    ] == "Supported answer."

    assert len(
        result["sources"]
    ) == 1


def test_generate_answer_returns_multiple_sources(
    monkeypatch
):
    results = [
        make_result(
            filename="document_a.pdf",
            distance=0.10
        ),
        make_result(
            filename="document_b.txt",
            distance=0.30
        )
    ]

    monkeypatch.setattr(
        rag,
        "search_documents",
        lambda query, limit, user_id=None: results
    )

    mock_gemini_response(
        monkeypatch,
        "Combined grounded answer."
    )

    result = rag.generate_answer(
        "Explain the topic."
    )

    assert len(
        result["sources"]
    ) == 2


def test_is_follow_up_query_rejects_standalone_question():
    assert (
        rag.is_follow_up_query(
            "What is Jenkins?"
        )
        is False
    )


def test_is_follow_up_query_detects_referential_question():
    assert (
        rag.is_follow_up_query(
            "How is it different?"
        )
        is True
    )


def test_is_follow_up_query_detects_possessive_reference():
    assert (
        rag.is_follow_up_query(
            "What are its key features?"
        )
        is True
    )


def test_is_follow_up_query_detects_plural_possessive_reference():
    assert (
        rag.is_follow_up_query(
            "What are their differences?"
        )
        is True
    )


def test_build_retrieval_query_without_history():
    query = (
        "What is Jenkins?"
    )

    result = (
        rag.build_retrieval_query(
            query
        )
    )

    assert result == query


def test_standalone_query_does_not_use_history():
    history = [
        {
            "question":
                "What is Continuous Delivery?",
            "answer":
                "Previous answer."
        }
    ]

    result = (
        rag.build_retrieval_query(
            "What is Jenkins?",
            history
        )
    )

    assert result == (
        "What is Jenkins?"
    )


def test_follow_up_query_uses_history():
    history = [
        {
            "question":
                (
                    "What is the difference between "
                    "Continuous Delivery and "
                    "Continuous Deployment?"
                ),
            "answer":
                "Previous answer."
        }
    ]

    result = (
        rag.build_retrieval_query(
            "Which one requires human approval?",
            history
        )
    )

    assert (
        "Continuous Delivery"
        in result
    )

    assert result.endswith(
        "Which one requires human approval?"
    )


def test_possessive_follow_up_query_uses_history():
    history = [
        {
            "question":
                "What is Jenkins?",
            "answer":
                "Jenkins answer."
        }
    ]

    result = (
        rag.build_retrieval_query(
            "What are its key features?",
            history
        )
    )

    assert (
        "What is Jenkins?"
        in result
    )

    assert result.endswith(
        "What are its key features?"
    )


def test_build_retrieval_query_uses_only_questions():
    history = [
        {
            "question":
                "What is Jenkins?",
            "answer":
                (
                    "THIS ANSWER MUST NOT "
                    "ENTER RETRIEVAL."
                )
        }
    ]

    result = (
        rag.build_retrieval_query(
            "What are its key features?",
            history
        )
    )

    assert (
        "THIS ANSWER MUST NOT ENTER RETRIEVAL."
        not in result
    )


def test_build_retrieval_query_respects_history_limit():
    history = [
        {
            "question":
                f"Question {index}",
            "answer":
                f"Answer {index}"
        }
        for index in range(
            1,
            7
        )
    ]

    result = (
        rag.build_retrieval_query(
            "Which one?",
            history
        )
    )

    assert (
        "Question 1\n"
        not in result
    )

    assert (
        "Question 2\n"
        not in result
    )

    assert (
        "Question 3"
        in result
    )

    assert (
        "Question 6"
        in result
    )


def test_build_retrieval_query_deduplicates_history():
    history = [
        {
            "question":
                "what is jenkins",
            "answer":
                "First answer."
        },
        {
            "question":
                "What is Jenkins?",
            "answer":
                "Second answer."
        }
    ]

    result = (
        rag.build_retrieval_query(
            "What are its key features?",
            history
        )
    )

    assert (
        result.lower().count(
            "what is jenkins"
        )
        == 1
    )


def test_build_retrieval_query_excludes_previous_same_follow_up():
    history = [
        {
            "question":
                "What is Jenkins?",
            "answer":
                "Jenkins answer."
        },
        {
            "question":
                "What are its key features?",
            "answer":
                rag.REJECTION_ANSWER
        }
    ]

    result = (
        rag.build_retrieval_query(
            "What are its key features?",
            history
        )
    )

    assert result == (
        "What is Jenkins?\n"
        "What are its key features?"
    )


def test_build_conversation_context_without_history():
    assert (
        rag.build_conversation_context()
        == "No previous conversation."
    )


def test_build_conversation_context_includes_questions_and_answers():
    history = [
        {
            "question":
                "What is Jenkins?",
            "answer":
                "Jenkins is an automation server."
        }
    ]

    result = (
        rag.build_conversation_context(
            history
        )
    )

    assert (
        "User: What is Jenkins?"
        in result
    )

    assert (
        "Assistant: Jenkins is an automation server."
        in result
    )


def test_generate_answer_uses_history_for_follow_up_retrieval(
    monkeypatch
):
    captured = {}

    def fake_search(
        query,
        limit,
        user_id=None
    ):
        captured[
            "query"
        ] = query

        return [
            make_result(
                filename="jenkins_guide.txt",
                content=(
                    "Jenkins offers a rich plugin "
                    "ecosystem and Pipeline as Code."
                ),
                distance=0.20
            )
        ]

    monkeypatch.setattr(
        rag,
        "search_documents",
        fake_search
    )

    mock_gemini_response(
        monkeypatch,
        (
            "Jenkins provides a rich plugin "
            "ecosystem and Pipeline as Code."
        )
    )

    history = [
        {
            "question":
                "What is Jenkins?",
            "answer":
                "Jenkins is an automation server."
        }
    ]

    result = rag.generate_answer(
        "What are its key features?",
        conversation_history=history
    )

    assert (
        "What is Jenkins?"
        in captured["query"]
    )

    assert (
        result["sources"][0][
            "filename"
        ]
        == "jenkins_guide.txt"
    )


def test_generate_answer_standalone_query_ignores_history(
    monkeypatch
):
    captured = {}

    def fake_search(
        query,
        limit,
        user_id=None
    ):
        captured[
            "query"
        ] = query

        return [
            make_result(
                filename="jenkins_guide.txt",
                content=(
                    "Jenkins is a leading open-source "
                    "automation server."
                ),
                distance=0.261
            )
        ]

    monkeypatch.setattr(
        rag,
        "search_documents",
        fake_search
    )

    mock_gemini_response(
        monkeypatch,
        (
            "Jenkins is a leading open-source "
            "automation server."
        )
    )

    history = [
        {
            "question":
                "Explain Continuous Delivery.",
            "answer":
                "Unrelated answer."
        }
    ]

    result = rag.generate_answer(
        "What is Jenkins?",
        conversation_history=history
    )

    assert (
        captured["query"]
        == "What is Jenkins?"
    )

    assert (
        result["sources"][0][
            "filename"
        ]
        == "jenkins_guide.txt"
    )


def test_generate_answer_grounded_rejection_removes_sources(
    monkeypatch
):
    results = [
        make_result(
            filename="related.pdf",
            content=(
                "Semantically related but "
                "does not answer the question."
            ),
            distance=0.20
        )
    ]

    monkeypatch.setattr(
        rag,
        "search_documents",
        lambda query, limit, user_id=None: results
    )

    mock_gemini_response(
        monkeypatch,
        rag.REJECTION_ANSWER
    )

    result = rag.generate_answer(
        "What unsupported fact am I asking for?"
    )

    assert result == {
        "answer":
            rag.REJECTION_ANSWER,
        "sources":
            []
    }


def test_generate_answer_keeps_document_context_as_evidence(
    monkeypatch
):
    captured = {}

    results = [
        make_result(
            filename="jenkins_guide.txt",
            content=(
                "Jenkins supports Pipeline as Code "
                "through Jenkinsfile."
            ),
            distance=0.20
        )
    ]

    monkeypatch.setattr(
        rag,
        "search_documents",
        lambda query, limit, user_id=None: results
    )

    def fake_generate_content(
        *args,
        **kwargs
    ):
        captured[
            "prompt"
        ] = kwargs[
            "contents"
        ]

        return SimpleNamespace(
            text=(
                "Jenkins supports Pipeline as Code."
            )
        )

    monkeypatch.setattr(
        rag.client.models,
        "generate_content",
        fake_generate_content
    )

    history = [
        {
            "question":
                "What is Jenkins?",
            "answer":
                "Jenkins is an automation server."
        }
    ]

    rag.generate_answer(
        "What are its key features?",
        conversation_history=history
    )

    prompt = captured[
        "prompt"
    ]

    assert (
        "DOCUMENT CONTEXT:"
        in prompt
    )

    assert (
        "Jenkins supports Pipeline as Code"
        in prompt
    )

    assert (
        "RECENT CONVERSATION:"
        in prompt
    )

def test_generate_answer_forwards_authenticated_user_id(
    monkeypatch
):
    captured = {}

    def fake_search(
        query,
        limit,
        user_id=None
    ):
        captured["query"] = query
        captured["limit"] = limit
        captured["user_id"] = user_id

        return []

    monkeypatch.setattr(
        rag,
        "search_documents",
        fake_search
    )

    result = rag.generate_answer(
        "What is Jenkins?",
        user_id=42
    )

    assert captured["query"] == "What is Jenkins?"
    assert captured["limit"] == 3
    assert captured["user_id"] == 42

    assert (
        result["answer"]
        == rag.NO_RESULTS_ANSWER
    )

    assert result["sources"] == []


def test_generate_answer_without_authenticated_user_keeps_legacy_none_scope(
    monkeypatch
):
    captured = {}

    def fake_search(
        query,
        limit,
        user_id=None
    ):
        captured["user_id"] = user_id
        return []

    monkeypatch.setattr(
        rag,
        "search_documents",
        fake_search
    )

    rag.generate_answer(
        "What is Jenkins?"
    )

    assert captured["user_id"] is None
