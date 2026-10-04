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


def _result(
    chunk_id,
    document_id,
    filename,
    chunk_index,
    content,
    distance,
    page_number,
    metadata
):
    return (
        chunk_id,
        document_id,
        filename,
        chunk_index,
        content,
        distance,
        page_number,
        None,
        metadata,
    )


def test_visual_companion_is_kept_when_same_page_narrowly_misses_gate(
    monkeypatch
):
    text_result = _result(
        1,
        10,
        "report.pdf",
        0,
        "The chart summarizes API availability.",
        0.20,
        1,
        {
            "source_type": "pdf"
        },
    )

    visual_result = _result(
        2,
        10,
        "report.pdf",
        1,
        (
            "Visual type: chart. "
            "Checkout 99.98%, Orders 99.92%, "
            "Inventory 99.87%, Payments 99.95%."
        ),
        0.30,
        1,
        {
            "source_type": "visual",
            "visual_type": "chart",
        },
    )

    scores = {
        1: 0.55,
        2: 0.4679,
    }

    monkeypatch.setattr(
        rag,
        "calculate_hybrid_score",
        lambda query, content, distance:
            scores[
                1
                if content.startswith(
                    "The chart"
                )
                else 2
            ]
    )

    selected = (
        rag.select_relevant_results(
            [
                text_result,
                visual_result,
            ],
            "Which service had the highest availability?",
        )
    )

    assert text_result in selected
    assert visual_result in selected


def test_visual_companion_is_not_kept_when_too_far_below_gate(
    monkeypatch
):
    text_result = _result(
        1,
        10,
        "report.pdf",
        0,
        "The chart summarizes API availability.",
        0.20,
        1,
        {
            "source_type": "pdf"
        },
    )

    weak_visual = _result(
        2,
        10,
        "report.pdf",
        1,
        "Unrelated visual evidence.",
        0.50,
        1,
        {
            "source_type": "visual",
            "visual_type": "chart",
        },
    )

    monkeypatch.setattr(
        rag,
        "calculate_hybrid_score",
        lambda query, content, distance:
            0.55
            if content.startswith(
                "The chart"
            )
            else 0.40
    )

    selected = (
        rag.select_relevant_results(
            [
                text_result,
                weak_visual,
            ],
            "Which service had the highest availability?",
        )
    )

    assert text_result in selected
    assert weak_visual not in selected


def test_visual_companion_requires_same_document_page(
    monkeypatch
):
    accepted_text = _result(
        1,
        10,
        "report.pdf",
        0,
        "The chart summarizes API availability.",
        0.20,
        1,
        {
            "source_type": "pdf"
        },
    )

    other_page_visual = _result(
        2,
        10,
        "report.pdf",
        1,
        "Chart values.",
        0.30,
        2,
        {
            "source_type": "visual",
            "visual_type": "chart",
        },
    )

    monkeypatch.setattr(
        rag,
        "calculate_hybrid_score",
        lambda query, content, distance:
            0.55
            if content.startswith(
                "The chart"
            )
            else 0.4679
    )

    selected = (
        rag.select_relevant_results(
            [
                accepted_text,
                other_page_visual,
            ],
            "Which service had the highest availability?",
        )
    )

    assert accepted_text in selected
    assert other_page_visual not in selected


def test_non_visual_chunk_does_not_receive_companion_exception(
    monkeypatch
):
    accepted_text = _result(
        1,
        10,
        "report.pdf",
        0,
        "The chart summarizes API availability.",
        0.20,
        1,
        {
            "source_type": "pdf"
        },
    )

    ordinary_text = _result(
        2,
        10,
        "report.pdf",
        1,
        "Some ordinary text.",
        0.30,
        1,
        {
            "source_type": "pdf"
        },
    )

    monkeypatch.setattr(
        rag,
        "calculate_hybrid_score",
        lambda query, content, distance:
            0.55
            if content.startswith(
                "The chart"
            )
            else 0.4679
    )

    selected = (
        rag.select_relevant_results(
            [
                accepted_text,
                ordinary_text,
            ],
            "Which service had the highest availability?",
        )
    )

    assert accepted_text in selected
    assert ordinary_text not in selected
