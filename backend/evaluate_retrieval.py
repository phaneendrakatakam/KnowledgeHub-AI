from search import search_documents


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
    # inside the CI/CD document.
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
    }
]


def evaluate_retrieval():

    print()
    print("=" * 80)
    print(
        "KNOWLEDGEHUB AI - RETRIEVAL EVALUATION"
    )
    print("=" * 80)

    print()
    print(
        f"Total evaluation questions: "
        f"{len(TEST_QUESTIONS)}"
    )

    print(
        "Current evaluation boundary: "
        "distance <= 0.40"
    )

    print()


    for test in TEST_QUESTIONS:

        question = test["question"]
        expected = test["expected"]

        print()
        print("-" * 80)

        print(
            f"QUESTION: {question}"
        )

        print(
            f"EXPECTED: {expected}"
        )

        print("-" * 80)


        results = search_documents(
            question,
            limit=3
        )


        if not results:

            print(
                "No results returned."
            )

            continue


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


            distance_value = float(
                distance
            )


            relevance = max(
                0.0,
                min(
                    1.0,
                    1.0 - distance_value
                )
            )


            passes_threshold = (
                distance_value <= 0.40
            )


            print()

            print(
                f"RESULT #{rank}"
            )

            print(
                f"Document: {filename}"
            )

            print(
                f"Chunk: {chunk_index}"
            )

            print(
                f"Distance: "
                f"{distance_value:.4f}"
            )

            print(
                f"Display relevance: "
                f"{relevance:.4f}"
            )

            print(
                "Passes 0.40 threshold: "
                f"{passes_threshold}"
            )


            preview = (
                content
                .replace("\n", " ")
                .strip()
            )


            print(
                f"Preview: "
                f"{preview[:250]}"
            )


    print()
    print("=" * 80)
    print(
        "EVALUATION COMPLETE"
    )
    print("=" * 80)


if __name__ == "__main__":

    evaluate_retrieval()