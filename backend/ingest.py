import sys
import json
from pathlib import Path

from db import get_connection
from process_document import (
    process_document
)


def prepare_document_for_ingestion(
    file_path: str
):
    """
    Parse, chunk, and embed a document without changing the database.

    This gives callers a safe two-phase upload flow:
    1. fully validate/process a temporary file
    2. persist the already-prepared chunks only after the physical
       file has been safely placed

    No database rows are modified by this function.
    """

    document_file = Path(
        file_path
    )

    if not document_file.exists():
        raise FileNotFoundError(
            f"File not found: "
            f"{document_file}"
        )

    print(
        f"Processing: "
        f"{document_file.name}"
    )

    results = process_document(
        str(document_file)
    )

    if not results:
        raise ValueError(
            "No indexable content was produced "
            "from the document."
        )

    print(
        f"Created "
        f"{len(results)} chunks."
    )

    return results


def ingest_document(
    file_path: str,
    user_id: int | None = None,
    logical_filename: str | None = None,
    prepared_results=None
):
    """
    Ingest a supported document into KnowledgeHub.

    When user_id is supplied, the document is stored inside that
    user's isolated knowledge base.

    logical_filename lets a temporary physical file be indexed under
    the user's real/original filename.

    prepared_results can be supplied by a caller that already ran
    prepare_document_for_ingestion(). This avoids parsing/embedding
    the same upload twice and supports failure-safe file replacement.
    """

    document_file = Path(
        file_path
    )

    if not document_file.exists():
        raise FileNotFoundError(
            f"File not found: "
            f"{document_file}"
        )

    database_filename = Path(
        logical_filename
        or document_file.name
    ).name

    if not database_filename:
        raise ValueError(
            "A document filename is required."
        )

    results = (
        prepared_results
        if prepared_results is not None
        else prepare_document_for_ingestion(
            str(document_file)
        )
    )

    if not results:
        raise ValueError(
            "No indexable content was produced "
            "from the document."
        )

    with get_connection() as conn:
        with conn.cursor() as cur:
            if user_id is None:
                cur.execute(
                    """
                    SELECT id
                    FROM documents
                    WHERE
                        filename = %s
                        AND user_id IS NULL
                    """,
                    (
                        database_filename,
                    )
                )
            else:
                cur.execute(
                    """
                    SELECT id
                    FROM documents
                    WHERE
                        filename = %s
                        AND user_id = %s
                    """,
                    (
                        database_filename,
                        user_id
                    )
                )

            existing_document = (
                cur.fetchone()
            )

            if existing_document:
                document_id = (
                    existing_document[0]
                )

                print(
                    "Document already exists. "
                    "Updating Document ID: "
                    f"{document_id}"
                )

                cur.execute(
                    """
                    DELETE FROM document_chunks
                    WHERE document_id = %s
                    """,
                    (
                        document_id,
                    )
                )

            else:
                cur.execute(
                    """
                    INSERT INTO documents
                    (
                        filename,
                        user_id
                    )
                    VALUES (
                        %s,
                        %s
                    )
                    RETURNING id
                    """,
                    (
                        database_filename,
                        user_id
                    )
                )

                document_id = (
                    cur.fetchone()[0]
                )

                print(
                    f"New Document ID: "
                    f"{document_id}"
                )

            for result in results:
                print(
                    "Saving chunk "
                    f"{result['chunk_id'] + 1}"
                    f"/{len(results)}..."
                )

                cur.execute(
                    """
                    INSERT INTO document_chunks
                    (
                        document_id,
                        chunk_index,
                        content,
                        embedding,
                        page_number,
                        section,
                        metadata
                    )
                    VALUES
                    (
                        %s,
                        %s,
                        %s,
                        %s,
                        %s,
                        %s,
                        %s::jsonb
                    )
                    """,
                    (
                        document_id,
                        result["chunk_id"],
                        result["text"],
                        result["embedding"],
                        result.get(
                            "page_number"
                        ),
                        result.get(
                            "section"
                        ),
                        json.dumps(
                            result.get(
                                "metadata"
                            )
                            or {}
                        ),
                    )
                )

        conn.commit()

    print()
    print(
        "==================================="
    )
    print(
        "Document successfully ingested! ✅"
    )
    print(
        "==================================="
    )

    return document_id


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print(
            "Usage: "
            "python ingest.py "
            "<path-to-document>"
        )
        sys.exit(1)

    ingest_document(
        sys.argv[1]
    )
