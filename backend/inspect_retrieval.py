from search import search_documents


QUESTION = (
    "What is the difference between "
    "Continuous Delivery and Continuous Deployment?"
)


def inspect_retrieval():

    print()
    print("=" * 80)
    print("KNOWLEDGEHUB AI - RETRIEVAL INSPECTOR")
    print("=" * 80)

    print()
    print(f"QUESTION:")
    print(QUESTION)

    results = search_documents(
        QUESTION,
        limit=5
    )

    print()
    print(
        f"Retrieved {len(results)} chunks."
    )


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


        print()
        print("=" * 80)

        print(
            f"RESULT #{rank}"
        )

        print(
            f"Document: {filename}"
        )

        print(
            f"Chunk ID: {chunk_id}"
        )

        print(
            f"Chunk Index: {chunk_index}"
        )

        print(
            f"Distance: {distance_value:.4f}"
        )

        print(
            f"Display Relevance: {relevance:.4f}"
        )

        print(
            f"Character Count: {len(content)}"
        )

        print("-" * 80)

        print("FULL CHUNK CONTENT:")

        print("-" * 80)

        print(content)

        print("=" * 80)


if __name__ == "__main__":
    inspect_retrieval()