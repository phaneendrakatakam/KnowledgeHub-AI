import sys
from pathlib import Path

from db import get_connection
from process_document import process_document


def ingest_document(file_path: str):
    pdf_file = Path(file_path)

    if not pdf_file.exists():
        raise FileNotFoundError(
            f"File not found: {pdf_file}"
        )

    print(f"Processing: {pdf_file.name}")

    results = process_document(str(pdf_file))

    print(f"Created {len(results)} chunks.")

    with get_connection() as conn:
        with conn.cursor() as cur:

            # Check whether this document already exists
            cur.execute(
                """
                SELECT id
                FROM documents
                WHERE filename = %s
                """,
                (pdf_file.name,)
            )

            existing_document = cur.fetchone()

            if existing_document:
                document_id = existing_document[0]

                print(
                    f"Document already exists. "
                    f"Updating Document ID: {document_id}"
                )

                # Delete existing chunks
                cur.execute(
                    """
                    DELETE FROM document_chunks
                    WHERE document_id = %s
                    """,
                    (document_id,)
                )

            else:
                # Insert new document
                cur.execute(
                    """
                    INSERT INTO documents (filename)
                    VALUES (%s)
                    RETURNING id
                    """,
                    (pdf_file.name,)
                )

                document_id = cur.fetchone()[0]

                print(
                    f"New Document ID: {document_id}"
                )

            # Insert chunks and embeddings
            for result in results:

                print(
                    f"Saving chunk "
                    f"{result['chunk_id'] + 1}/{len(results)}..."
                )

                cur.execute(
                    """
                    INSERT INTO document_chunks
                    (
                        document_id,
                        chunk_index,
                        content,
                        embedding
                    )
                    VALUES (%s, %s, %s, %s)
                    """,
                    (
                        document_id,
                        result["chunk_id"],
                        result["text"],
                        result["embedding"],
                    )
                )

        conn.commit()

    print()
    print("===================================")
    print("Document successfully ingested! ✅")
    print("===================================")


if __name__ == "__main__":

    if len(sys.argv) != 2:
        print(
            "Usage: python ingest.py <path-to-pdf>"
        )
        sys.exit(1)

    ingest_document(sys.argv[1])