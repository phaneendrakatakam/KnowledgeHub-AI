from search import (
    search_documents,
    calculate_hybrid_score
)


HYBRID_RELEVANCE_THRESHOLD = 0.60


TEST_QUESTIONS = [
    # ========================================================
    # DIRECTLY ANSWERABLE QUESTIONS
    # ========================================================
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

    # ========================================================
    # CLEARLY UNRELATED QUESTIONS
    # ========================================================
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

    # ========================================================
    # HARDER ANSWERABLE QUESTIONS
    # ========================================================
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

    # ========================================================
    # HARDER REJECTION QUESTIONS
    #
    # These intentionally contain words that may appear
    # inside the CI/CD documents.
    # ========================================================
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

    # ========================================================
    # V3 REGRESSION CASE
    #
    # This was the retrieval failure that motivated
    # hybrid reranking.
    # ========================================================
    {
        "question": "What is Pipeline as Code?",
        "expected": "ANSWER"
    }
]


def evaluate_retrieval():
    print()
    print("=" * 80)
    print("KNOWLEDGEHUB AI V3 - HYBRID RETRIEVAL EVALUATION")
    print("=" * 80)

    print()
    print(
        f"Total evaluation questions: "
        f"{len(TEST_QUESTIONS)}"
    )

    print(
        "Current evaluation boundary: "
        f"hybrid >= {HYBRID_RELEVANCE_THRESHOLD:.2f}"
    )

    print()

    total = len(TEST_QUESTIONS)
    passed = 0
    failed = 0

    for test in TEST_QUESTIONS:
        question = test["question"]
        expected = test["expected"]

        print()
        print("-" * 80)
        print(f"QUESTION: {question}")
        print(f"EXPECTED: {expected}")
        print("-" * 80)

        results = search_documents(
            question,
            limit=3
        )

        if not results:
            predicted = "REJECT"

            print("No results returned.")
            print(f"PREDICTED: {predicted}")

            if predicted == expected:
                print("EVALUATION: PASS")
                passed += 1
            else:
                print("EVALUATION: FAIL")
                failed += 1

            continue

        scored_results = []

        for rank, result in enumerate(
            results,
            start=1
        ):
            (
                chunk_id,
                document_id,
                filename,
                chunk_index,
                content,
                distance
            ) = result

            distance_value = float(distance)

            vector_similarity = max(
                0.0,
                min(
                    1.0,
                    1.0 - distance_value
                )
            )

            hybrid = calculate_hybrid_score(
                question,
                content,
                distance_value
            )

            passes_threshold = (
                hybrid >=
                HYBRID_RELEVANCE_THRESHOLD
            )

            scored_results.append(
                {
                    "rank": rank,
                    "filename": filename,
                    "chunk_index": chunk_index,
                    "content": content,
                    "distance": distance_value,
                    "vector_similarity":
                        vector_similarity,
                    "hybrid": hybrid,
                    "passes_threshold":
                        passes_threshold
                }
            )

        for item in scored_results:
            print()
            print(
                f"RESULT #{item['rank']}"
            )
            print(
                f"Document: "
                f"{item['filename']}"
            )
            print(
                f"Chunk: "
                f"{item['chunk_index']}"
            )
            print(
                f"Distance: "
                f"{item['distance']:.4f}"
            )
            print(
                f"Vector similarity: "
                f"{item['vector_similarity']:.4f}"
            )
            print(
                f"Hybrid relevance: "
                f"{item['hybrid']:.4f}"
            )
            print(
                f"Passes "
                f"{HYBRID_RELEVANCE_THRESHOLD:.2f} "
                f"hybrid threshold: "
                f"{item['passes_threshold']}"
            )

            preview = (
                item["content"]
                .replace("\n", " ")
                .strip()
            )

            print(
                f"Preview: "
                f"{preview[:250]}"
            )

        any_relevant = any(
            item["passes_threshold"]
            for item in scored_results
        )

        predicted = (
            "ANSWER"
            if any_relevant
            else "REJECT"
        )

        print()
        print(f"PREDICTED: {predicted}")

        if predicted == expected:
            print("EVALUATION: PASS")
            passed += 1
        else:
            print("EVALUATION: FAIL")
            failed += 1

    print()
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
    evaluate_retrieval()