import sys
from pathlib import Path

sys.path.insert(
    0,
    str(
        Path(__file__).resolve().parents[1]
        / "backend"
    )
)

import search


def test_single_important_word_preserves_legacy_exact_score():
    score = search.lexical_score(
        "What is Jenkins?",
        "Jenkins is an open-source automation server."
    )

    assert score == 1.0


def test_partial_multiword_phrase_gets_proportional_credit():
    score = search.lexical_score(
        "How much does the Mango Shake cost?",
        "Visible text: Mango Shake Rs.120"
    )

    assert score == 0.5


def test_isolated_word_overlap_does_not_get_phrase_bonus():
    score = search.lexical_score(
        "How much does the Mango Shake cost?",
        "A mango orchard has seasonal costs."
    )

    assert score < 0.20


def test_full_multiword_phrase_still_gets_exact_score():
    score = search.lexical_score(
        "What is Pipeline as Code?",
        "Pipeline as Code lets teams version pipeline definitions."
    )

    assert score == 1.0
