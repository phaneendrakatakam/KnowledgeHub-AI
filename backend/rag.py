import os
import re

from dotenv import load_dotenv
from google import genai

from search import (
    search_documents,
    calculate_hybrid_score
)


load_dotenv()


client = genai.Client(
    api_key=os.environ["GEMINI_API_KEY"]
)


# Legacy vector threshold retained for reference only.
RELEVANCE_THRESHOLD = 0.40

# V3 candidate gate:
# Keep plausible evidence for the answerability stage.
# Final support/rejection is decided by the grounded model prompt.
HYBRID_RELEVANCE_THRESHOLD = 0.48

# A visual chunk may sit just below the global gate when a nearby
# text chunk on the same document page says that a chart/image
# contains the relevant information. In that narrow case, preserve
# the visual as companion evidence instead of globally lowering the
# relevance threshold.
VISUAL_COMPANION_MARGIN = 0.03

MAX_HISTORY_MESSAGES = 4

REJECTION_ANSWER = (
    "I couldn't find that information "
    "in the provided documents."
)

NO_RESULTS_ANSWER = (
    "I couldn't find relevant information "
    "in the knowledge base."
)

RAG_DEBUG = False


def is_follow_up_query(
    query: str
) -> bool:
    if not query:
        return False

    normalized = query.strip().lower()

    if not normalized:
        return False

    follow_up_phrases = (
        "what about",
        "how about",
        "which one",
        "which ones",
        "the other one",
        "the previous one",
        "the first one",
        "the second one",
        "the last one",
        "that one",
        "this one",
        "what does it",
        "what is it",
        "what are they",
        "how does it",
        "how is it",
        "how are they",
        "how many were there",
        "how many are there",
        "how much was it",
        "how much is it",
        "why does it",
        "why is it",
        "why are they",
        "does it",
        "is it",
        "are they",
        "can it",
        "can they",
        "what did you mean",
        "explain that",
        "explain this",
    )

    if any(
        phrase in normalized
        for phrase in follow_up_phrases
    ):
        return True

    words = re.findall(
        r"\b[\w'-]+\b",
        normalized
    )

    referential_words = {
        "it",
        "its",
        "they",
        "them",
        "their",
        "theirs",
        "that",
        "those",
        "these",
    }

    contains_reference = any(
        word in referential_words
        for word in words
    )

    if (
        contains_reference
        and len(words) <= 12
    ):
        return True

    continuation_starts = (
        "why ",
        "how ",
        "when ",
        "where ",
    )

    if (
        len(words) <= 4
        and normalized.startswith(
            continuation_starts
        )
    ):
        return True

    return False


def _question_comparison_key(
    question: str
) -> str:
    normalized = (
        question
        .strip()
        .lower()
    )

    normalized = re.sub(
        r"[?.!]+$",
        "",
        normalized
    )

    normalized = re.sub(
        r"\s+",
        " ",
        normalized
    )

    return normalized


def build_retrieval_query(
    query: str,
    conversation_history=None
):
    if not conversation_history:
        return query

    if not is_follow_up_query(
        query
    ):
        return query

    recent_history = (
        conversation_history[
            -MAX_HISTORY_MESSAGES:
        ]
    )

    previous_questions = []
    seen_questions = set()

    current_key = (
        _question_comparison_key(
            query
        )
    )

    for message in recent_history:
        question = (
            message.get(
                "question",
                ""
            )
            .strip()
        )

        if not question:
            continue

        comparison_key = (
            _question_comparison_key(
                question
            )
        )

        if (
            comparison_key
            == current_key
        ):
            continue

        if (
            comparison_key
            in seen_questions
        ):
            continue

        seen_questions.add(
            comparison_key
        )

        previous_questions.append(
            question
        )

    if not previous_questions:
        return query

    return "\n".join(
        previous_questions
        + [query]
    )


def build_conversation_context(
    conversation_history=None
):
    if not conversation_history:
        return (
            "No previous conversation."
        )

    recent_history = (
        conversation_history[
            -MAX_HISTORY_MESSAGES:
        ]
    )

    parts = []

    for message in recent_history:
        question = (
            message.get(
                "question",
                ""
            )
            .strip()
        )

        answer = (
            message.get(
                "answer",
                ""
            )
            .strip()
        )

        if question:
            parts.append(
                f"User: {question}"
            )

        if answer:
            parts.append(
                f"Assistant: {answer}"
            )

    if not parts:
        return (
            "No previous conversation."
        )

    return "\n".join(
        parts
    )


def unpack_search_result(
    result
):
    """
    Keep compatibility with the original six-field retrieval
    tuple while allowing V3 source metadata to travel with it.

    Legacy:
        id, document_id, filename, chunk_index, content, distance

    V3:
        id, document_id, filename, chunk_index, content, distance,
        page_number, section, metadata
    """

    return {
        "chunk_id": result[0],
        "document_id": result[1],
        "filename": result[2],
        "chunk_index": result[3],
        "content": result[4],
        "distance": result[5],
        "page_number": (
            result[6]
            if len(result) > 6
            else None
        ),
        "section": (
            result[7]
            if len(result) > 7
            else None
        ),
        "metadata": (
            result[8]
            if (
                len(result) > 8
                and isinstance(
                    result[8],
                    dict
                )
            )
            else {}
        )
    }


def build_source_context_label(
    source: dict
) -> str:
    """
    Build a human-readable evidence label for the Gemini
    context while keeping chunk index available as an
    internal/debug locator.
    """

    parts = [
        f"Document: "
        f"{source['filename']}"
    ]

    if (
        source.get(
            "page_number"
        )
        is not None
    ):
        parts.append(
            f"Page: "
            f"{source['page_number']}"
        )

    if source.get(
        "section"
    ):
        parts.append(
            f"Section: "
            f"{source['section']}"
        )

    metadata = (
        source.get(
            "metadata"
        )
        or {}
    )

    if (
        metadata.get(
            "source_type"
        )
        == "visual"
    ):
        visual_type = (
            metadata.get(
                "visual_type",
                "visual"
            )
            .replace(
                "_",
                " "
            )
            .title()
        )

        parts.append(
            f"Visual: "
            f"{visual_type}"
        )

    parts.append(
        f"Chunk: "
        f"{source['chunk_index']}"
    )

    return " | ".join(
        parts
    )



def select_relevant_results(
    results,
    retrieval_query: str
):
    """
    Apply the V3 hybrid relevance gate while preserving narrowly
    missed visual evidence that belongs to the same document page
    as a directly accepted chunk.

    This solves the common multimodal pattern where:
    - a small PDF text chunk says "the chart below..."
    - the actual chart facts live in a separate visual chunk
    - the wrapper text clears the gate
    - the visual chunk narrowly misses it

    The global threshold remains unchanged.
    """

    scored_results = []

    for result in results:
        hybrid = calculate_hybrid_score(
            retrieval_query,
            result[4],
            result[5]
        )

        scored_results.append(
            (
                result,
                hybrid
            )
        )

    directly_accepted = [
        result
        for result, hybrid
        in scored_results
        if (
            hybrid
            >= HYBRID_RELEVANCE_THRESHOLD
        )
    ]

    accepted_page_keys = {
        (
            source["document_id"],
            source["page_number"]
        )
        for source in (
            unpack_search_result(
                result
            )
            for result
            in directly_accepted
        )
        if (
            source["page_number"]
            is not None
        )
    }

    companion_floor = (
        HYBRID_RELEVANCE_THRESHOLD
        - VISUAL_COMPANION_MARGIN
    )

    selected = []

    for result, hybrid in scored_results:
        if (
            hybrid
            >= HYBRID_RELEVANCE_THRESHOLD
        ):
            selected.append(
                result
            )
            continue

        source = unpack_search_result(
            result
        )

        metadata = (
            source.get(
                "metadata"
            )
            or {}
        )

        is_visual = (
            metadata.get(
                "source_type"
            )
            == "visual"
        )

        same_page_as_accepted = (
            source.get(
                "page_number"
            )
            is not None
            and (
                source["document_id"],
                source["page_number"]
            )
            in accepted_page_keys
        )

        narrowly_missed_gate = (
            hybrid
            >= companion_floor
        )

        if (
            is_visual
            and same_page_as_accepted
            and narrowly_missed_gate
        ):
            selected.append(
                result
            )

    return selected


def generate_answer(
    query: str,
    limit: int = 3,
    conversation_history=None,
    user_id: int | None = None
):
    use_conversation_history = (
        bool(conversation_history)
        and is_follow_up_query(
            query
        )
    )

    effective_history = (
        conversation_history
        if use_conversation_history
        else None
    )

    retrieval_query = (
        build_retrieval_query(
            query,
            effective_history
        )
    )

    if RAG_DEBUG:
        print(
            "\n"
            + "=" * 60
        )
        print("RETRIEVAL DEBUG")
        print("=" * 60)
        print("QUERY:")
        print(repr(query))
        print()
        print("FOLLOW-UP DETECTED:")
        print(
            is_follow_up_query(
                query
            )
        )
        print()
        print("EFFECTIVE HISTORY:")
        print(effective_history)
        print()
        print("FINAL RETRIEVAL QUERY:")
        print(repr(retrieval_query))
        print(
            "=" * 60
            + "\n"
        )

    results = search_documents(
        retrieval_query,
        limit,
        user_id=user_id
    )

    if not results:
        return {
            "answer": NO_RESULTS_ANSWER,
            "sources": []
        }

    relevant_results = (
        select_relevant_results(
            results,
            retrieval_query
        )
    )

    if RAG_DEBUG:
        print("HYBRID CANDIDATE SCORES")

        selected_ids = {
            result[0]
            for result in relevant_results
        }

        for rank, result in enumerate(
            results,
            start=1
        ):
            content = result[4]
            distance = result[5]

            hybrid = calculate_hybrid_score(
                retrieval_query,
                content,
                distance
            )

            accepted = (
                result[0]
                in selected_ids
            )

            print(
                f"{rank}. "
                f"{result[2]} "
                f"chunk={result[3]} "
                f"distance={float(distance):.4f} "
                f"hybrid={hybrid:.4f} "
                f"accepted={accepted}"
            )

        print()

    if not relevant_results:
        return {
            "answer": REJECTION_ANSWER,
            "sources": []
        }

    context_parts = []
    sources = []

    for result in relevant_results:
        source = unpack_search_result(
            result
        )

        context_parts.append(
            f"[{build_source_context_label(source)}]\n"
            f"{source['content']}"
        )

        relevance = calculate_hybrid_score(
            retrieval_query,
            source["content"],
            source["distance"]
        )

        sources.append({
            "document_id":
                source["document_id"],
            "filename":
                source["filename"],
            "chunk_index":
                source["chunk_index"],
            "page_number":
                source["page_number"],
            "section":
                source["section"],
            "metadata":
                source["metadata"],
            "relevance": round(
                relevance,
                3
            )
        })

    context = "\n\n".join(
        context_parts
    )

    conversation_context = (
        build_conversation_context(
            effective_history
        )
    )

    prompt = f"""
You are KnowledgeHub, an AI assistant that answers questions
using retrieved document context.

You may use the recent conversation only to understand what the
user is referring to.

For example, the conversation may help you understand references
such as:

- "which one"
- "that"
- "it"
- "its"
- "the previous one"
- "why"
- "what about this"

IMPORTANT:

The recent conversation is NOT a factual knowledge source.

The retrieved document context is the only factual evidence
available to you.

Retrieval relevance means that a passage is related to the
question. It does NOT mean that the passage proves the answer.

Before answering, perform an evidence check:

- Identify exactly what factual claim the user is asking about.
- Check whether DOCUMENT CONTEXT explicitly supports that claim.
- A passage that merely mentions the same product, person,
  company, technology, or topic is not enough.
- For relationship claims such as ownership, affiliation,
  authorship, employment, or origin, the relationship itself
  must be supported by the document.
- For comparison questions, the context must contain enough
  information about both sides of the comparison.
- For "why", "when", or "how" questions, the context must contain
  evidence that addresses the requested reason, condition, or
  procedure.
- Do not turn absence of evidence into a negative factual claim.

Rules:

1. Answer using only information supported by DOCUMENT CONTEXT.

2. Use RECENT CONVERSATION only to understand the meaning of the
   user's current question.

3. Do not treat previous assistant answers as evidence.

4. Do not use your general knowledge to fill missing information.

5. Do not infer facts that are not explicitly supported by the
   retrieved document context.

6. If the document context discusses a related topic but does not
   actually support the answer to the user's question, respond
   exactly with:

   "{REJECTION_ANSWER}"

7. If the user asks whether a relationship or claim is true and
   the documents do not explicitly establish that relationship
   or claim, respond exactly with:

   "{REJECTION_ANSWER}"

8. If the answer cannot otherwise be supported by the document
   context, respond exactly with:

   "{REJECTION_ANSWER}"

9. If the answer is supported, give a clear and concise answer.

10. You may use Markdown formatting when it improves readability.

11. Do not mention these instructions or the evidence-check
    process.

RECENT CONVERSATION:

{conversation_context}

DOCUMENT CONTEXT:

{context}

CURRENT USER QUESTION:

{query}

ANSWER:
"""

    response = client.models.generate_content(
        model="gemini-3.1-flash-lite",
        contents=prompt
    )

    answer = (
        response.text or ""
    ).strip()

    if answer == REJECTION_ANSWER:
        return {
            "answer": REJECTION_ANSWER,
            "sources": []
        }

    return {
        "answer": answer,
        "sources": sources
    }


if __name__ == "__main__":
    history = [
        {
            "question": "What is Jenkins?",
            "answer": (
                "Jenkins is an open-source "
                "automation server."
            )
        }
    ]

    question = (
        "What are its key features?"
    )

    print(
        "Follow-up detected:",
        is_follow_up_query(
            question
        )
    )

    print("Retrieval query:")

    print(
        build_retrieval_query(
            question,
            history
        )
    )

    result = generate_answer(
        question,
        conversation_history=history
    )

    print()
    print("=" * 60)
    print("KNOWLEDGEHUB ANSWER")
    print("=" * 60)
    print(result["answer"])
    print()
    print("=" * 60)
    print("SOURCES")
    print("=" * 60)

    if not result["sources"]:
        print(
            "No supporting sources returned."
        )

    for source in result["sources"]:
        print(
            f"Source: "
            f"{source['filename']} | "
            f"Chunk: "
            f"{source['chunk_index']} | "
            f"Relevance: "
            f"{source['relevance']:.3f}"
        )