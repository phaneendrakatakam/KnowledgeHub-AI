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


# ============================================================
# V1 TESTS
# ============================================================


def test_generate_answer_when_no_results(monkeypatch):

    monkeypatch.setattr(
        rag,
        "search_documents",
        lambda query, limit: []
    )

    result = rag.generate_answer(
        "Unknown question"
    )

    assert result == {
        "answer": (
            "I couldn't find relevant information "
            "in the knowledge base."
        ),
        "sources": []
    }


def test_generate_answer_when_results_are_not_relevant(
    monkeypatch
):

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

    result = rag.generate_answer(
        "Question with no relevant answer"
    )

    assert result == {
        "answer": (
            "I couldn't find that information "
            "in the provided documents."
        ),
        "sources": []
    }


def test_generate_answer_uses_relevant_results(
    monkeypatch
):

    fake_results = [
        (
            1,
            10,
            "story.pdf",
            0,
            (
                "The boy received the Hanuman idol "
                "from his grandfather."
            ),
            0.20
        )
    ]

    class FakeResponse:
        text = (
            "The boy received the Hanuman idol "
            "from his grandfather."
        )

    class FakeModels:

        def __init__(self):
            self.received_prompt = None

        def generate_content(
            self,
            model,
            contents
        ):

            self.received_prompt = contents

            assert model == (
                "gemini-3.1-flash-lite"
            )

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
        "The boy received the Hanuman idol "
        "from his grandfather."
    )

    assert result["sources"] == [
        {
            "document_id": 10,
            "filename": "story.pdf",
            "chunk_index": 0,
            "relevance": 0.8
        }
    ]

    assert (
        "story.pdf"
        in fake_models.received_prompt
    )

    assert (
        (
            "The boy received the Hanuman idol "
            "from his grandfather."
        )
        in fake_models.received_prompt
    )

    assert (
        "Who gave the boy the Hanuman idol?"
        in fake_models.received_prompt
    )


def test_generate_answer_filters_irrelevant_results(
    monkeypatch
):

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

        def generate_content(
            self,
            model,
            contents
        ):

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

    result = rag.generate_answer(
        "test question"
    )

    assert (
        result["answer"]
        == "Relevant information"
    )

    assert result["sources"] == [
        {
            "document_id": 10,
            "filename": "relevant.pdf",
            "chunk_index": 0,
            "relevance": 0.75
        }
    ]

    assert (
        "relevant.pdf"
        in fake_models.received_prompt
    )

    assert (
        "irrelevant.pdf"
        not in fake_models.received_prompt
    )


def test_generate_answer_returns_multiple_sources(
    monkeypatch
):

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
        text = (
            "Combined answer from both documents."
        )

    class FakeModels:

        def __init__(self):
            self.received_prompt = None

        def generate_content(
            self,
            model,
            contents
        ):

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

    result = rag.generate_answer(
        "combined question"
    )

    assert result["answer"] == (
        "Combined answer from both documents."
    )

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

    assert (
        "first.pdf"
        in fake_models.received_prompt
    )

    assert (
        "second.pdf"
        in fake_models.received_prompt
    )

    assert (
        "First relevant document content."
        in fake_models.received_prompt
    )

    assert (
        "Second relevant document content."
        in fake_models.received_prompt
    )


# ============================================================
# V2 CONVERSATION-AWARE RAG TESTS
# ============================================================


def test_build_retrieval_query_without_history():

    query = (
        "Which one requires human approval?"
    )

    result = rag.build_retrieval_query(
        query
    )

    assert result == query


def test_build_retrieval_query_with_history():

    history = [
        {
            "question": (
                "What is the difference between "
                "Continuous Delivery and "
                "Continuous Deployment?"
            ),
            "answer": (
                "Continuous Delivery usually "
                "requires manual production approval."
            )
        }
    ]

    result = rag.build_retrieval_query(
        "Which one requires human approval?",
        history
    )

    assert (
        "What is the difference between "
        "Continuous Delivery and "
        "Continuous Deployment?"
        in result
    )

    assert (
        "Which one requires human approval?"
        in result
    )


def test_build_retrieval_query_uses_only_questions():

    history = [
        {
            "question": (
                "What is Continuous Delivery?"
            ),
            "answer": (
                "THIS ANSWER SHOULD NOT BE PART "
                "OF THE RETRIEVAL QUERY."
            )
        }
    ]

    result = rag.build_retrieval_query(
        "Why does it require approval?",
        history
    )

    assert (
        "What is Continuous Delivery?"
        in result
    )

    assert (
        "Why does it require approval?"
        in result
    )

    assert (
        "THIS ANSWER SHOULD NOT BE PART"
        not in result
    )


def test_build_retrieval_query_respects_history_limit():

    history = [
        {
            "question": f"Question {index}",
            "answer": f"Answer {index}"
        }
        for index in range(1, 7)
    ]

    result = rag.build_retrieval_query(
        "Current question",
        history
    )

    # MAX_HISTORY_MESSAGES = 4,
    # therefore Question 1 and 2
    # should no longer be included.

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
        "Question 4"
        in result
    )

    assert (
        "Question 5"
        in result
    )

    assert (
        "Question 6"
        in result
    )

    assert (
        "Current question"
        in result
    )


def test_build_conversation_context_without_history():

    result = rag.build_conversation_context()

    assert (
        result
        == "No previous conversation."
    )


def test_build_conversation_context_includes_questions_and_answers():

    history = [
        {
            "question": (
                "What is Continuous Delivery?"
            ),
            "answer": (
                "Continuous Delivery prepares "
                "changes for production release."
            )
        }
    ]

    result = rag.build_conversation_context(
        history
    )

    assert (
        "User: What is Continuous Delivery?"
        in result
    )

    assert (
        (
            "Assistant: Continuous Delivery "
            "prepares changes for production release."
        )
        in result
    )


def test_generate_answer_uses_history_for_retrieval(
    monkeypatch
):

    captured_query = {
        "value": None
    }

    fake_results = [
        (
            1,
            10,
            "cicd.pdf",
            4,
            (
                "Continuous Delivery requires "
                "human approval before production."
            ),
            0.20
        )
    ]

    def fake_search_documents(
        query,
        limit
    ):

        captured_query["value"] = query

        return fake_results


    class FakeResponse:

        text = (
            "Continuous Delivery requires "
            "human approval."
        )


    class FakeModels:

        def __init__(self):
            self.received_prompt = None

        def generate_content(
            self,
            model,
            contents
        ):

            self.received_prompt = contents

            return FakeResponse()


    fake_models = FakeModels()


    class FakeClient:
        models = fake_models


    monkeypatch.setattr(
        rag,
        "search_documents",
        fake_search_documents
    )

    monkeypatch.setattr(
        rag,
        "client",
        FakeClient()
    )


    history = [
        {
            "question": (
                "What is the difference between "
                "Continuous Delivery and "
                "Continuous Deployment?"
            ),
            "answer": (
                "Continuous Delivery normally "
                "requires manual approval."
            )
        }
    ]


    result = rag.generate_answer(
        "Which one requires human approval?",
        conversation_history=history
    )


    assert (
        "Continuous Delivery"
        in captured_query["value"]
    )


    assert (
        "Which one requires human approval?"
        in captured_query["value"]
    )


    assert (
        "RECENT CONVERSATION"
        in fake_models.received_prompt
    )


    assert (
        (
            "User: What is the difference between "
            "Continuous Delivery and "
            "Continuous Deployment?"
        )
        in fake_models.received_prompt
    )


    assert (
        "cicd.pdf"
        in fake_models.received_prompt
    )


    assert result["answer"] == (
        "Continuous Delivery requires "
        "human approval."
    )


def test_generate_answer_keeps_document_context_as_evidence(
    monkeypatch
):

    fake_results = [
        (
            1,
            10,
            "official.pdf",
            0,
            (
                "Continuous Delivery requires "
                "human approval before production."
            ),
            0.20
        )
    ]


    class FakeResponse:

        text = (
            "Continuous Delivery requires "
            "human approval."
        )


    class FakeModels:

        def __init__(self):
            self.received_prompt = None

        def generate_content(
            self,
            model,
            contents
        ):

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


    history = [
        {
            "question": (
                "Which process requires approval?"
            ),

            # Deliberately incorrect previous answer.
            "answer": (
                "Continuous Deployment requires "
                "manual approval."
            )
        }
    ]


    rag.generate_answer(
        "Which one is it?",
        conversation_history=history
    )


    prompt = (
        fake_models.received_prompt
    )


    # The old assistant answer may appear in
    # conversation context, but the prompt must
    # explicitly prohibit treating it as evidence.

    assert (
        "The recent conversation is NOT "
        "a factual knowledge source."
        in prompt
    )


    assert (
        "Do not treat previous assistant "
        "answers as evidence."
        in prompt
    )


    assert (
        (
            "Continuous Delivery requires "
            "human approval before production."
        )
        in prompt
    )