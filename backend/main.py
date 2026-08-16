from fastapi import FastAPI, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware

import json
import shutil
from pathlib import Path

from db import get_connection
from ingest import ingest_document
from rag import generate_answer


app = FastAPI()


# Allow the local frontend to communicate
# with the FastAPI backend.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


DOCUMENTS_DIR = Path("../documents")
DOCUMENTS_DIR.mkdir(exist_ok=True)


@app.get("/")
def home():
    return {
        "message": "KnowledgeHub AI backend is running!"
    }


# ============================================================
# DOCUMENT MANAGEMENT
# ============================================================


@app.post("/documents/upload")
async def upload_document(
    file: UploadFile = File(...)
):
    """
    Upload a PDF and run the existing ingestion pipeline.
    """

    # Validate file type
    if not file.filename.lower().endswith(".pdf"):
        return {
            "success": False,
            "message": "Only PDF files are supported."
        }

    file_path = DOCUMENTS_DIR / file.filename

    # Save uploaded PDF
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(
            file.file,
            buffer
        )

    try:
        # Run the existing ingestion pipeline.
        ingest_document(str(file_path))

        # Find the newly created document record.
        with get_connection() as conn:
            with conn.cursor() as cur:

                cur.execute(
                    """
                    SELECT
                        id,
                        filename,
                        created_at
                    FROM documents
                    WHERE filename = %s
                    """,
                    (file.filename,)
                )

                document = cur.fetchone()

        return {
            "success": True,
            "id": document[0] if document else None,
            "filename": file.filename,
            "created_at": document[2] if document else None,
            "message": (
                "Document uploaded and successfully "
                "ingested into KnowledgeHub."
            )
        }

    except Exception as error:
        return {
            "success": False,
            "filename": file.filename,
            "message": (
                "Document was uploaded, but ingestion failed."
            ),
            "error": str(error)
        }


@app.get("/documents")
def get_documents():
    """
    Return all uploaded documents.
    """

    with get_connection() as conn:
        with conn.cursor() as cur:

            cur.execute(
                """
                SELECT
                    id,
                    filename,
                    created_at
                FROM documents
                ORDER BY created_at DESC, id DESC
                """
            )

            rows = cur.fetchall()

    return {
        "documents": [
            {
                "id": row[0],
                "filename": row[1],
                "created_at": row[2]
            }
            for row in rows
        ]
    }


@app.delete("/documents/{document_id}")
def delete_document(document_id: int):
    """
    Delete a document from the database.

    Because document_chunks.document_id has
    ON DELETE CASCADE, all chunks belonging
    to this document are automatically deleted.

    The corresponding PDF file is also removed
    from the documents directory.
    """

    with get_connection() as conn:
        with conn.cursor() as cur:

            # First find the document.
            cur.execute(
                """
                SELECT
                    id,
                    filename
                FROM documents
                WHERE id = %s
                """,
                (document_id,)
            )

            document = cur.fetchone()

            if document is None:
                return {
                    "success": False,
                    "message": "Document not found."
                }

            filename = document[1]

            # Delete database record.
            # document_chunks are deleted automatically
            # because of ON DELETE CASCADE.
            cur.execute(
                """
                DELETE FROM documents
                WHERE id = %s
                RETURNING id
                """,
                (document_id,)
            )

            deleted = cur.fetchone()

        conn.commit()

    # Delete the physical PDF file.
    file_path = DOCUMENTS_DIR / filename

    file_deleted = True

    try:
        if file_path.exists():
            file_path.unlink()
    except Exception:
        file_deleted = False

    return {
        "success": True,
        "message": (
            "Document and its chunks were deleted successfully."
        ),
        "document_id": document_id,
        "filename": filename,
        "file_deleted": file_deleted
    }


# ============================================================
# CHAT MANAGEMENT
# ============================================================


@app.post("/chats")
def create_chat():
    """
    Create a new chat session.
    """

    with get_connection() as conn:
        with conn.cursor() as cur:

            cur.execute(
                """
                INSERT INTO chat_sessions (title)
                VALUES (%s)
                RETURNING id, title, created_at, updated_at
                """,
                ("New Chat",)
            )

            row = cur.fetchone()

        conn.commit()

    return {
        "id": row[0],
        "title": row[1],
        "created_at": row[2],
        "updated_at": row[3]
    }


@app.get("/chats")
def get_chats():
    """
    Return all chat sessions.
    """

    with get_connection() as conn:
        with conn.cursor() as cur:

            cur.execute(
                """
                SELECT
                    id,
                    title,
                    created_at,
                    updated_at
                FROM chat_sessions
                ORDER BY updated_at DESC
                """
            )

            rows = cur.fetchall()

    return {
        "chats": [
            {
                "id": row[0],
                "title": row[1],
                "created_at": row[2],
                "updated_at": row[3]
            }
            for row in rows
        ]
    }


@app.get("/chats/{session_id}")
def get_chat(session_id: int):
    """
    Return one chat session and all its messages.
    """

    with get_connection() as conn:
        with conn.cursor() as cur:

            cur.execute(
                """
                SELECT
                    id,
                    title,
                    created_at,
                    updated_at
                FROM chat_sessions
                WHERE id = %s
                """,
                (session_id,)
            )

            session = cur.fetchone()

            if session is None:
                return {
                    "success": False,
                    "message": "Chat not found."
                }

            cur.execute(
                """
                SELECT
                    id,
                    question,
                    answer,
                    sources,
                    created_at
                FROM chat_messages
                WHERE session_id = %s
                ORDER BY created_at ASC, id ASC
                """,
                (session_id,)
            )

            messages = cur.fetchall()

    return {
        "id": session[0],
        "title": session[1],
        "created_at": session[2],
        "updated_at": session[3],
        "messages": [
            {
                "id": row[0],
                "question": row[1],
                "answer": row[2],
                "sources": row[3],
                "created_at": row[4]
            }
            for row in messages
        ]
    }


@app.delete("/chats/{session_id}")
def delete_chat(session_id: int):
    """
    Delete a chat and all its messages.
    """

    with get_connection() as conn:
        with conn.cursor() as cur:

            cur.execute(
                """
                DELETE FROM chat_sessions
                WHERE id = %s
                RETURNING id
                """,
                (session_id,)
            )

            deleted = cur.fetchone()

        conn.commit()

    if deleted is None:
        return {
            "success": False,
            "message": "Chat not found."
        }

    return {
        "success": True,
        "message": "Chat deleted successfully."
    }


# ============================================================
# QUESTION / RAG
# ============================================================


@app.post("/ask")
async def ask_question(request: dict):

    question = request.get(
        "question",
        ""
    ).strip()

    session_id = request.get(
        "session_id"
    )

    if not question:
        return {
            "question": "",
            "answer": "Please provide a question.",
            "sources": []
        }

    # If no session was supplied, create one.
    if session_id is None:

        with get_connection() as conn:
            with conn.cursor() as cur:

                cur.execute(
                    """
                    INSERT INTO chat_sessions (title)
                    VALUES (%s)
                    RETURNING id
                    """,
                    ("New Chat",)
                )

                session_id = cur.fetchone()[0]

            conn.commit()

    # Make sure the supplied session exists.
    else:

        with get_connection() as conn:
            with conn.cursor() as cur:

                cur.execute(
                    """
                    SELECT id
                    FROM chat_sessions
                    WHERE id = %s
                    """,
                    (session_id,)
                )

                session = cur.fetchone()

        if session is None:
            return {
                "question": question,
                "answer": "Chat session not found.",
                "sources": [],
                "session_id": session_id
            }

    # Generate RAG answer.
    result = generate_answer(question)

    answer = result["answer"]
    sources = result["sources"]

    # Save question + answer + sources.
    with get_connection() as conn:
        with conn.cursor() as cur:

            cur.execute(
                """
                INSERT INTO chat_messages
                (
                    session_id,
                    question,
                    answer,
                    sources
                )
                VALUES (%s, %s, %s, %s::jsonb)
                """,
                (
                    session_id,
                    question,
                    answer,
                    json.dumps(sources)
                )
            )

            # Give a new chat a useful title
            # based on its first question.
            cur.execute(
                """
                UPDATE chat_sessions
                SET
                    title = CASE
                        WHEN title = 'New Chat'
                        THEN %s
                        ELSE title
                    END,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = %s
                """,
                (
                    question[:80],
                    session_id
                )
            )

        conn.commit()

    return {
        "question": question,
        "answer": answer,
        "sources": sources,
        "session_id": session_id
    }