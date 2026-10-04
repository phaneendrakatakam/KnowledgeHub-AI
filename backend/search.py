from db import get_connection
from embedding import create_embedding
import re


def normalize_text(text: str) -> str:
    """Normalize text for lexical matching."""
    return re.sub(
        r"[^a-z0-9\s]",
        " ",
        text.lower()
    )


def lexical_score(
    query: str,
    content: str
) -> float:
    """
    Returns a lexical relevance score between 0 and 1.

    70% -> Exact important phrase
    30% -> Important word coverage
    """

    normalized_query = (
        normalize_text(
            query
        )
    )

    normalized_content = (
        normalize_text(
            content
        )
    )

    stop_words = {
        "what",
        "is",
        "the",
        "a",
        "an",
        "how",
        "why",
        "where",
        "when",
        "who",
        "does",
        "do",
        "of",
        "in",
        "to"
    }

    important_words = [
        word
        for word
        in normalized_query.split()
        if word not in stop_words
    ]

    if not important_words:
        return 0.0

    phrase_score = 0.0

    # Preserve the original exact-match behavior when the
    # query reduces to a single important word.
    if len(important_words) == 1:
        if important_words[0] in normalized_content.split():
            phrase_score = 1.0

    else:
        # For multi-word queries, reward the longest contiguous
        # sequence of important query words that appears in the
        # content. Exact full phrases still receive 1.0, while
        # meaningful subphrases receive proportional credit.
        for phrase_length in range(
            len(important_words),
            1,
            -1
        ):
            found_phrase = False

            for start in range(
                len(important_words)
                - phrase_length
                + 1
            ):
                candidate_phrase = " ".join(
                    important_words[
                        start:
                        start + phrase_length
                    ]
                )

                if candidate_phrase in normalized_content:
                    phrase_score = (
                        phrase_length
                        / len(important_words)
                    )
                    found_phrase = True
                    break

            if found_phrase:
                break

    content_words = set(
        normalized_content.split()
    )

    matched = sum(
        1
        for word
        in important_words
        if word in content_words
    )

    word_score = (
        matched
        / len(important_words)
    )

    return (
        0.70 * phrase_score
        + 0.30 * word_score
    )


def calculate_hybrid_score(
    query: str,
    content: str,
    distance: float
) -> float:
    """
    Hybrid relevance score.

    Combines:
    - Semantic similarity (70%)
    - Lexical relevance (30%)
    """

    lexical = lexical_score(
        query,
        content
    )

    vector_similarity = (
        1.0
        - float(distance)
    )

    return (
        0.70 * vector_similarity
        + 0.30 * lexical
    )


def search_documents(
    query: str,
    limit: int = 3,
    user_id: int | None = None
):
    """
    Hybrid retrieval.

    Stage 1:
        Retrieve a wider semantic candidate pool.

    Stage 2:
        Rerank using hybrid relevance.

    When user_id is supplied, only chunks belonging
    to that user's documents are searchable.
    """

    query_embedding = (
        create_embedding(
            query
        )
    )

    candidate_limit = max(
        limit,
        50
    )

    with get_connection() as conn:
        with conn.cursor() as cur:
            if user_id is None:
                cur.execute(
                    """
                    SELECT
                        dc.id,
                        dc.document_id,
                        d.filename,
                        dc.chunk_index,
                        dc.content,
                        dc.embedding
                            <=> %s::vector
                            AS distance,
                        dc.page_number,
                        dc.section,
                        dc.metadata
                    FROM document_chunks dc
                    JOIN documents d
                        ON dc.document_id = d.id
                    ORDER BY
                        dc.embedding
                            <=> %s::vector
                    LIMIT %s
                    """,
                    (
                        query_embedding,
                        query_embedding,
                        candidate_limit
                    )
                )

            else:
                cur.execute(
                    """
                    SELECT
                        dc.id,
                        dc.document_id,
                        d.filename,
                        dc.chunk_index,
                        dc.content,
                        dc.embedding
                            <=> %s::vector
                            AS distance,
                        dc.page_number,
                        dc.section,
                        dc.metadata
                    FROM document_chunks dc
                    JOIN documents d
                        ON dc.document_id = d.id
                    WHERE d.user_id = %s
                    ORDER BY
                        dc.embedding
                            <=> %s::vector
                    LIMIT %s
                    """,
                    (
                        query_embedding,
                        user_id,
                        query_embedding,
                        candidate_limit
                    )
                )

            candidates = (
                cur.fetchall()
            )

    reranked = []

    for result in candidates:
        content = result[4]
        distance = result[5]

        score = (
            calculate_hybrid_score(
                query,
                content,
                distance
            )
        )

        reranked.append(
            (
                result,
                score
            )
        )

    reranked.sort(
        key=lambda item:
            item[1],
        reverse=True
    )

    return [
        item[0]
        for item
        in reranked[:limit]
    ]


if __name__ == "__main__":
    query = (
        "What is Pipeline as Code?"
    )

    results = search_documents(
        query,
        limit=10
    )

    print("=" * 80)
    print(
        "HYBRID RETRIEVAL RESULTS"
    )
    print("=" * 80)

    for rank, result in enumerate(
        results,
        start=1
    ):
        (
            _,
            _,
            filename,
            chunk,
            content,
            distance
        ) = result

        lexical = lexical_score(
            query,
            content
        )

        hybrid = (
            calculate_hybrid_score(
                query,
                content,
                distance
            )
        )

        print(
            rank,
            filename,
            "chunk:",
            chunk,
            "distance:",
            round(
                float(distance),
                4
            ),
            "lexical:",
            round(
                lexical,
                4
            ),
            "hybrid:",
            round(
                hybrid,
                4
            )
        )