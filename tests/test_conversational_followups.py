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


def test_how_many_were_there_is_follow_up():
    assert (
        rag.is_follow_up_query(
            "How many were there in February?"
        )
        is True
    )


def test_how_many_are_there_is_follow_up():
    assert (
        rag.is_follow_up_query(
            "How many are there in March?"
        )
        is True
    )


def test_follow_up_retrieval_query_includes_previous_chart_question():
    query = (
        "How many were there in February?"
    )

    history = [
        {
            "question":
                "Which month had the highest number "
                "of service requests?",
            "answer":
                "March had the highest number of "
                "service requests, with a total of 76."
        }
    ]

    retrieval_query = (
        rag.build_retrieval_query(
            query,
            history
        )
    )

    assert (
        "Which month had the highest number "
        "of service requests?"
        in retrieval_query
    )

    assert (
        "How many were there in February?"
        in retrieval_query
    )


def test_standalone_how_many_question_stays_standalone():
    query = (
        "How many service requests were "
        "recorded in February?"
    )

    assert (
        rag.is_follow_up_query(
            query
        )
        is False
    )
