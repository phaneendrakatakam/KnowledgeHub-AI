from db import get_connection
from embedding import create_embedding


def search_documents(query: str, limit: int = 3):
    query_embedding = create_embedding(query)

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT
                    dc.id,
                    dc.document_id,
                    d.filename,
                    dc.chunk_index,
                    dc.content,
                    dc.embedding <=> %s::vector AS distance
                FROM document_chunks dc
                JOIN documents d
                    ON dc.document_id = d.id
                ORDER BY dc.embedding <=> %s::vector
                LIMIT %s
                """,
                (
                    query_embedding,
                    query_embedding,
                    limit,
                )
            )

            return cur.fetchall()


if __name__ == "__main__":
    query = "Who gave the Hanuman idol to the boy?"

    results = search_documents(query)

    for result in results:
        (
            chunk_id,
            document_id,
            filename,
            chunk_index,
            content,
            distance
        ) = result

        print("\n--- RESULT ---")
        print("Document:", filename)
        print("Chunk:", chunk_index)
        print("Distance:", distance)
        print("Content:")
        print(content[:500])