import rag


TEST_QUESTIONS = [
    {
        "question": "What is Continuous Integration?",
        "expected": "ANSWER"
    },
    {
        "question": "What is Continuous Delivery?",
        "expected": "ANSWER"
    },
    {
        "question": "What is Continuous Deployment?",
        "expected": "ANSWER"
    },
    {
        "question": (
            "What is the difference between Continuous "
            "Delivery and Continuous Deployment?"
        ),
        "expected": "ANSWER"
    },
    {
        "question": "Who is the CEO of Microsoft?",
        "expected": "REJECT"
    },
    {
        "question": "What is the capital of France?",
        "expected": "REJECT"
    },
    {
        "question": "Who won the FIFA World Cup?",
        "expected": "REJECT"
    },
    {
        "question": "How do I make biryani?",
        "expected": "REJECT"
    },
    {
        "question": (
            "When should a team use manual approval "
            "before production?"
        ),
        "expected": "ANSWER"
    },
    {
        "question": (
            "How can a failed deployment be rolled back?"
        ),
        "expected": "ANSWER"
    },
    {
        "question": (
            "Why should secrets not be stored "
            "in pipeline files?"
        ),
        "expected": "ANSWER"
    },
    {
        "question": (
            "What monitoring should happen "
            "after deployment?"
        ),
        "expected": "ANSWER"
    },
    {
        "question": (
            "What database does this application use?"
        ),
        "expected": "REJECT"
    },
    {
        "question": (
            "Does Jenkins belong to Microsoft?"
        ),
        "expected": "REJECT"
    },
    {
        "question": (
            "What programming language should I learn?"
        ),
        "expected": "REJECT"
    },
    {
        "question": (
            "Should I deploy my application "
            "on AWS or Azure?"
        ),
        "expected": "REJECT"
    },
    {
        "question": "What is Pipeline as Code?",
        "expected": "ANSWER"
    }
]


def predicted_label(answer: str) -> str:
    normalized = (
        answer or ""
    ).strip()

    if normalized in {
        rag.REJECTION_ANSWER,
        rag.NO_RESULTS_ANSWER
    }:
        return "REJECT"

    return "ANSWER"


def evaluate_rag():
    rag.RAG_DEBUG = False

    print()
    print("=" * 80)
    print(
        "KNOWLEDGEHUB AI V3 - END-TO-END RAG EVALUATION"
    )
    print("=" * 80)
    print()
    print(
        f"Total evaluation questions: "
        f"{len(TEST_QUESTIONS)}"
    )
    print(
        "Candidate boundary: "
        f"hybrid >= "
        f"{rag.HYBRID_RELEVANCE_THRESHOLD:.2f}"
    )
    print()

    passed = 0
    failed = 0

    for index, test in enumerate(
        TEST_QUESTIONS,
        start=1
    ):
        question = test["question"]
        expected = test["expected"]

        print("-" * 80)
        print(
            f"{index}. QUESTION: {question}"
        )
        print(
            f"EXPECTED: {expected}"
        )

        try:
            result = rag.generate_answer(
                question
            )

            answer = result.get(
                "answer",
                ""
            )

            predicted = predicted_label(
                answer
            )

            print(
                f"PREDICTED: {predicted}"
            )
            print(
                f"ANSWER: {answer}"
            )

            sources = result.get(
                "sources",
                []
            )

            if sources:
                source_text = ", ".join(
                    (
                        f"{source['filename']}"
                        f" [chunk "
                        f"{source['chunk_index']}, "
                        f"{source['relevance']:.3f}]"
                    )
                    for source in sources
                )
                print(
                    f"SOURCES: {source_text}"
                )
            else:
                print(
                    "SOURCES: none"
                )

            if predicted == expected:
                print(
                    "EVALUATION: PASS"
                )
                passed += 1
            else:
                print(
                    "EVALUATION: FAIL"
                )
                failed += 1

        except Exception as exc:
            print(
                f"ERROR: "
                f"{type(exc).__name__}: "
                f"{exc}"
            )
            print(
                "EVALUATION: FAIL"
            )
            failed += 1

        print()

    total = len(TEST_QUESTIONS)

    print("=" * 80)
    print("EVALUATION SUMMARY")
    print("=" * 80)
    print(f"Total:  {total}")
    print(f"Passed: {passed}")
    print(f"Failed: {failed}")
    print(
        f"Accuracy: "
        f"{(passed / total) * 100:.1f}%"
    )
    print("=" * 80)


if __name__ == "__main__":
    evaluate_rag()