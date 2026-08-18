from rag import generate_answer


REJECTION_MESSAGES = {
    "I couldn't find relevant information in the knowledge base.",
    "I couldn't find that information in the provided documents."
}


TEST_CASES = [
    # ========================================================
    # ANSWERABLE
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
    # SHOULD BE REJECTED
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


def classify_result(result):

    answer = (
        result.get(
            "answer",
            ""
        )
        .strip()
    )

    if answer in REJECTION_MESSAGES:

        return "REJECT"

    return "ANSWER"


def evaluate_rag():

    total = len(TEST_CASES)

    passed = 0

    failed = 0


    print()

    print("=" * 90)

    print(
        "KNOWLEDGEHUB AI - END-TO-END RAG EVALUATION"
    )

    print("=" * 90)

    print()

    print(
        f"Total test cases: {total}"
    )

    print()


    for index, test in enumerate(
        TEST_CASES,
        start=1
    ):

        question = test["question"]

        expected = test["expected"]


        print("-" * 90)

        print(
            f"TEST #{index}"
        )

        print(
            f"QUESTION: {question}"
        )

        print(
            f"EXPECTED: {expected}"
        )

        print("-" * 90)


        try:

            result = generate_answer(
                question
            )

        except Exception as error:

            failed += 1

            print()

            print(
                "RESULT: ERROR"
            )

            print(
                f"ERROR: {error}"
            )

            print()

            continue


        actual = classify_result(
            result
        )


        answer = result.get(
            "answer",
            ""
        )


        sources = result.get(
            "sources",
            []
        )


        is_pass = (
            actual == expected
        )


        if is_pass:

            passed += 1

            status = "PASS"

        else:

            failed += 1

            status = "FAIL"


        print()

        print(
            f"ACTUAL: {actual}"
        )

        print(
            f"STATUS: {status}"
        )

        print()

        print(
            "ANSWER:"
        )

        print(
            answer
        )


        print()

        print(
            f"SOURCES RETURNED: {len(sources)}"
        )


        for source_index, source in enumerate(
            sources,
            start=1
        ):

            print(
                f"  Source #{source_index}: "
                f"{source.get('filename')} | "
                f"Chunk {source.get('chunk_index')} | "
                f"Relevance {source.get('relevance')}"
            )


        print()


    print("=" * 90)

    print(
        "EVALUATION SUMMARY"
    )

    print("=" * 90)

    print()

    print(
        f"Passed: {passed}"
    )

    print(
        f"Failed: {failed}"
    )

    print(
        f"Total:  {total}"
    )


    accuracy = (
        passed / total
    ) * 100


    print(
        f"Outcome accuracy: {accuracy:.2f}%"
    )

    print()


    if failed == 0:

        print(
            "END-TO-END RAG EVALUATION PASSED."
        )

    else:

        print(
            "END-TO-END RAG EVALUATION "
            "HAS FAILURES THAT REQUIRE REVIEW."
        )


    print()


if __name__ == "__main__":

    evaluate_rag()