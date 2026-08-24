from pathlib import Path
import json
import shutil
import secrets
from contextlib import asynccontextmanager

from fastapi import (
    Depends,
    FastAPI,
    File,
    HTTPException,
    UploadFile
)
from fastapi.middleware.cors import (
    CORSMiddleware
)

from auth import (
    AccountDisabledError,
    authenticate_user,
    create_access_token,
    get_current_user,
    register_user,
    require_admin,
    revoke_access_token,
    update_user_password
)
from db import (
    ensure_auth_schema,
    get_connection
)
from ingest import (
    ingest_document,
    prepare_document_for_ingestion
)
from rag import generate_answer


@asynccontextmanager
async def lifespan(
    app: FastAPI
):
    ensure_auth_schema()
    yield


app = FastAPI(
    title="KnowledgeHub AI V3",
    lifespan=lifespan
)


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


DOCUMENTS_DIR = Path(
    "../documents"
)

DOCUMENTS_DIR.mkdir(
    exist_ok=True
)


SUPPORTED_EXTENSIONS = {
    ".pdf",
    ".txt",
    ".md",
    ".markdown",
    ".docx",
}
MAX_UPLOAD_SIZE_BYTES = 25 * 1024 * 1024
UPLOAD_CHUNK_SIZE = 1024 * 1024

def get_file_type(
    filename: str
):
    extension = (
        Path(filename)
        .suffix
        .lower()
    )

    file_type_map = {
        ".pdf": "PDF",
        ".txt": "TXT",
        ".md": "Markdown",
        ".markdown": "Markdown",
        ".docx": "DOCX",
    }

    return file_type_map.get(
        extension,
        extension
        .lstrip(".")
        .upper()
    )


def get_user_documents_dir(
    user_id: int
) -> Path:
    user_dir = (
        DOCUMENTS_DIR
        / f"user_{user_id}"
    )

    user_dir.mkdir(
        parents=True,
        exist_ok=True
    )

    return user_dir


def public_user(
    user: dict
):
    return {
        "id": user["id"],
        "name": user["name"],
        "email": user["email"],
        "created_at": user["created_at"],
        "role": user.get(
            "role",
            "member"
        ),
        "is_active": user.get(
            "is_active",
            True
        ),
        "must_change_password": user.get(
            "must_change_password",
            False
        )
    }


@app.get("/")
def home():
    return {
        "message":
            "KnowledgeHub AI backend is running!"
    }


# ============================================================
# AUTHENTICATION
# ============================================================


@app.post("/auth/register")
def register(
    request: dict
):
    try:
        user, _is_first_user = (
            register_user(
                request.get(
                    "name",
                    ""
                ),
                request.get(
                    "email",
                    ""
                ),
                request.get(
                    "password",
                    ""
                )
            )
        )

    except ValueError as error:
        raise HTTPException(
            status_code=400,
            detail=str(error)
        )

    access_token = (
        create_access_token(
            user["id"]
        )
    )

    return {
        "success": True,
        "access_token":
            access_token,
        "token_type": "bearer",
        "user": public_user(
            user
        )
    }


@app.post("/auth/login")
def login(
    request: dict
):
    try:
        user = authenticate_user(
            request.get(
                "email",
                ""
            ),
            request.get(
                "password",
                ""
            )
        )

    except AccountDisabledError as error:
        raise HTTPException(
            status_code=403,
            detail=str(error)
        )

    if user is None:
        raise HTTPException(
            status_code=401,
            detail=(
                "Invalid email or password."
            )
        )

    access_token = (
        create_access_token(
            user["id"]
        )
    )

    return {
        "success": True,
        "access_token":
            access_token,
        "token_type": "bearer",
        "user": public_user(
            user
        )
    }


@app.get("/auth/me")
def auth_me(
    current_user: dict = Depends(
        get_current_user
    )
):
    return {
        "user": public_user(
            current_user
        )
    }


@app.post("/auth/logout")
def logout(
    current_user: dict = Depends(
        get_current_user
    )
):
    revoke_access_token(
        current_user["_token"]
    )

    return {
        "success": True,
        "message":
            "Logged out successfully."
    }


@app.post("/auth/change-password")
def change_password(
    request: dict,
    current_user: dict = Depends(
        get_current_user
    )
):
    new_password = request.get(
        "new_password",
        ""
    )

    confirm_password = request.get(
        "confirm_password",
        ""
    )

    if new_password != confirm_password:
        raise HTTPException(
            status_code=400,
            detail=(
                "Password confirmation "
                "does not match."
            )
        )

    try:
        updated = update_user_password(
            current_user["id"],
            new_password,
            must_change_password=False
        )
    except ValueError as error:
        raise HTTPException(
            status_code=400,
            detail=str(error)
        )

    if not updated:
        raise HTTPException(
            status_code=404,
            detail="User not found."
        )

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                DELETE FROM auth_tokens
                WHERE user_id = %s
                """,
                (
                    current_user["id"],
                )
            )
        conn.commit()

    return {
        "success": True,
        "message": (
            "Password changed successfully. "
            "Please sign in again."
        )
    }


# ============================================================
# ADMIN / USER MANAGEMENT
# ============================================================


def _get_admin_target(
    user_id: int
):
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT
                    id,
                    name,
                    email,
                    role,
                    is_active,
                    created_at,
                    disabled_at
                FROM users
                WHERE id = %s
                """,
                (
                    user_id,
                )
            )

            row = cur.fetchone()

    if row is None:
        raise HTTPException(
            status_code=404,
            detail="User not found."
        )

    return {
        "id": row[0],
        "name": row[1],
        "email": row[2],
        "role": row[3],
        "is_active": row[4],
        "created_at": row[5],
        "disabled_at": row[6]
    }


def _ensure_admin_can_be_removed_or_disabled(
    target: dict
):
    if (
        target["role"] != "admin"
        or not target["is_active"]
    ):
        return

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT COUNT(*)
                FROM users
                WHERE
                    role = 'admin'
                    AND is_active = TRUE
                    AND id <> %s
                """,
                (
                    target["id"],
                )
            )

            other_active_admins = (
                cur.fetchone()[0]
            )

    if other_active_admins == 0:
        raise HTTPException(
            status_code=400,
            detail=(
                "You cannot disable or delete "
                "the last active administrator."
            )
        )


@app.get("/admin/users")
def get_admin_users(
    admin_user: dict = Depends(
        require_admin
    )
):
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT
                    u.id,
                    u.name,
                    u.email,
                    u.role,
                    u.is_active,
                    u.created_at,
                    u.disabled_at,
                    (
                        SELECT COUNT(*)
                        FROM documents d
                        WHERE d.user_id = u.id
                    ) AS document_count,
                    (
                        SELECT COUNT(*)
                        FROM chat_sessions cs
                        WHERE cs.user_id = u.id
                    ) AS chat_count,
                    (
                        SELECT COUNT(*)
                        FROM auth_tokens at
                        WHERE
                            at.user_id = u.id
                            AND at.expires_at
                                > CURRENT_TIMESTAMP
                    ) AS active_session_count
                FROM users u
                ORDER BY
                    u.created_at ASC,
                    u.id ASC
                """
            )

            rows = cur.fetchall()

    return {
        "users": [
            {
                "id": row[0],
                "name": row[1],
                "email": row[2],
                "role": row[3],
                "is_active": row[4],
                "created_at": row[5],
                "disabled_at": row[6],
                "document_count": row[7],
                "chat_count": row[8],
                "active_session_count":
                    row[9],
                "is_current_user":
                    row[0]
                    == admin_user["id"]
            }
            for row in rows
        ]
    }


@app.patch(
    "/admin/users/{user_id}/status"
)
def set_user_status(
    user_id: int,
    request: dict,
    admin_user: dict = Depends(
        require_admin
    )
):
    target = _get_admin_target(
        user_id
    )

    requested_active = (
        request.get(
            "is_active"
        )
    )

    if not isinstance(
        requested_active,
        bool
    ):
        raise HTTPException(
            status_code=400,
            detail=(
                "is_active must be "
                "true or false."
            )
        )

    if (
        user_id == admin_user["id"]
        and not requested_active
    ):
        raise HTTPException(
            status_code=400,
            detail=(
                "You cannot disable your "
                "own administrator account."
            )
        )

    if not requested_active:
        _ensure_admin_can_be_removed_or_disabled(
            target
        )

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE users
                SET
                    is_active = %s,
                    disabled_at = CASE
                        WHEN %s = FALSE
                        THEN CURRENT_TIMESTAMP
                        ELSE NULL
                    END
                WHERE id = %s
                RETURNING
                    id,
                    name,
                    email,
                    role,
                    is_active,
                    created_at,
                    disabled_at
                """,
                (
                    requested_active,
                    requested_active,
                    user_id
                )
            )

            row = cur.fetchone()

            if not requested_active:
                cur.execute(
                    """
                    DELETE FROM auth_tokens
                    WHERE user_id = %s
                    """,
                    (
                        user_id,
                    )
                )

        conn.commit()

    return {
        "success": True,
        "user": {
            "id": row[0],
            "name": row[1],
            "email": row[2],
            "role": row[3],
            "is_active": row[4],
            "created_at": row[5],
            "disabled_at": row[6]
        },
        "message": (
            "User enabled successfully."
            if requested_active
            else (
                "User disabled and all "
                "sessions revoked."
            )
        )
    }


@app.post(
    "/admin/users/{user_id}/reset-password"
)
def admin_reset_password(
    user_id: int,
    admin_user: dict = Depends(
        require_admin
    )
):
    target = _get_admin_target(
        user_id
    )

    if user_id == admin_user["id"]:
        raise HTTPException(
            status_code=400,
            detail=(
                "Use your own account settings "
                "to change the administrator password."
            )
        )

    if not target["is_active"]:
        raise HTTPException(
            status_code=400,
            detail=(
                "Enable the user before "
                "resetting their password."
            )
        )

    alphabet = (
        "ABCDEFGHJKLMNPQRSTUVWXYZ"
        "abcdefghijkmnopqrstuvwxyz"
        "23456789"
        "!@#$%"
    )

    temporary_password = (
        "KH-"
        + "".join(
            secrets.choice(alphabet)
            for _ in range(14)
        )
    )

    update_user_password(
        user_id,
        temporary_password,
        must_change_password=True
    )

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                DELETE FROM auth_tokens
                WHERE user_id = %s
                """,
                (
                    user_id,
                )
            )
        conn.commit()

    return {
        "success": True,
        "user_id": user_id,
        "name": target["name"],
        "email": target["email"],
        "temporary_password":
            temporary_password,
        "must_change_password": True,
        "message": (
            "Temporary password generated. "
            "It will only be returned in this response."
        )
    }


@app.post(
    "/admin/users/{user_id}/revoke-sessions"
)
def revoke_user_sessions(
    user_id: int,
    admin_user: dict = Depends(
        require_admin
    )
):
    target = _get_admin_target(
        user_id
    )

    if user_id == admin_user["id"]:
        raise HTTPException(
            status_code=400,
            detail=(
                "Use Sign out to revoke "
                "your current administrator session."
            )
        )

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                DELETE FROM auth_tokens
                WHERE user_id = %s
                """,
                (
                    user_id,
                )
            )

        conn.commit()

    return {
        "success": True,
        "message": (
            f"All sessions revoked for "
            f"{target['email']}."
        )
    }


@app.delete(
    "/admin/users/{user_id}"
)
def delete_user_account(
    user_id: int,
    admin_user: dict = Depends(
        require_admin
    )
):
    target = _get_admin_target(
        user_id
    )

    if user_id == admin_user["id"]:
        raise HTTPException(
            status_code=400,
            detail=(
                "You cannot delete your "
                "own administrator account."
            )
        )

    _ensure_admin_can_be_removed_or_disabled(
        target
    )

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                DELETE FROM users
                WHERE id = %s
                RETURNING id
                """,
                (
                    user_id,
                )
            )

            deleted = cur.fetchone()

        conn.commit()

    if deleted is None:
        raise HTTPException(
            status_code=404,
            detail="User not found."
        )

    user_directory = (
        DOCUMENTS_DIR
        / f"user_{user_id}"
    )

    files_removed = True

    try:
        if user_directory.exists():
            shutil.rmtree(
                user_directory
            )
    except Exception:
        files_removed = False

    return {
        "success": True,
        "message": (
            "User account and owned "
            "application data deleted."
        ),
        "user_id": user_id,
        "email": target["email"],
        "files_removed":
            files_removed
    }


def _document_upload_lock_key(
    user_id: int,
    filename: str
) -> str:
    return (
        "knowledgehub-upload:"
        f"{user_id}:"
        f"{filename.lower()}"
    )


def acquire_document_upload_lock(
    user_id: int,
    filename: str
):
    """
    Acquire a PostgreSQL session-level advisory lock for one
    user's logical document filename.

    Returns the open connection holding the lock, or None when
    another upload/re-upload for the same document is already
    in progress.

    PostgreSQL automatically releases the lock if the connection
    is lost, so a hard application crash does not leave a stale
    filesystem lock behind.
    """

    connection = get_connection()
    connection.autocommit = True

    try:
        with connection.cursor() as cur:
            cur.execute(
                """
                SELECT pg_try_advisory_lock(
                    hashtextextended(
                        %s,
                        0
                    )
                )
                """,
                (
                    _document_upload_lock_key(
                        user_id,
                        filename
                    ),
                )
            )

            acquired = bool(
                cur.fetchone()[0]
            )

    except Exception:
        connection.close()
        raise

    if not acquired:
        connection.close()
        return None

    return connection


def release_document_upload_lock(
    connection,
    user_id: int,
    filename: str
):
    if connection is None:
        return

    try:
        with connection.cursor() as cur:
            cur.execute(
                """
                SELECT pg_advisory_unlock(
                    hashtextextended(
                        %s,
                        0
                    )
                )
                """,
                (
                    _document_upload_lock_key(
                        user_id,
                        filename
                    ),
                )
            )

    except Exception as error:
        print(
            "Document upload lock release "
            "failed:",
            repr(
                error
            )
        )

    finally:
        try:
            connection.close()
        except Exception:
            pass


# ============================================================
# DOCUMENT MANAGEMENT
# ============================================================


@app.post("/documents/upload")
async def upload_document(
    file: UploadFile = File(...),
    current_user: dict = Depends(
        get_current_user
    )
):
    filename = Path(
        file.filename or ""
    ).name

    if not filename:
        raise HTTPException(
            status_code=400,
            detail="A filename is required."
        )

    extension = (
        Path(filename)
        .suffix
        .lower()
    )

    if extension not in SUPPORTED_EXTENSIONS:
        raise HTTPException(
            status_code=415,
            detail=(
                "Unsupported file type. "
                "Supported formats: "
                "PDF, TXT, Markdown, DOCX."
            )
        )

    user_dir = get_user_documents_dir(
        current_user["id"]
    )

    upload_lock_connection = (
        acquire_document_upload_lock(
            current_user["id"],
            filename
        )
    )

    if upload_lock_connection is None:
        raise HTTPException(
            status_code=409,
            detail=(
                "An upload or replacement for "
                "this document is already in progress. "
                "Please wait and try again."
            )
        )

    final_path = (
        user_dir
        / filename
    )

    temp_path = (
        user_dir
        / (
            f".upload_{secrets.token_hex(8)}"
            f"{extension}"
        )
    )

    backup_path = None
    total_size = 0

    try:
        # Stage 1: stream the upload to a temporary file while
        # enforcing the per-file size limit.
        with open(
            temp_path,
            "wb"
        ) as buffer:
            while True:
                chunk = await file.read(
                    UPLOAD_CHUNK_SIZE
                )

                if not chunk:
                    break

                total_size += len(chunk)

                if (
                    total_size
                    > MAX_UPLOAD_SIZE_BYTES
                ):
                    raise HTTPException(
                        status_code=413,
                        detail=(
                            "File is too large. "
                            "Maximum upload size "
                            "is 25 MB."
                        )
                    )

                buffer.write(
                    chunk
                )

        if total_size == 0:
            raise HTTPException(
                status_code=400,
                detail=(
                    "The uploaded file is empty."
                )
            )

        # Stage 2: fully parse/chunk/embed the temporary file before
        # touching a previously valid file or database document.
        prepared_results = (
            prepare_document_for_ingestion(
                str(temp_path)
            )
        )

        # Stage 3: safely place the physical file. If this is a
        # replacement, keep the previous good file as a temporary
        # backup until the database transaction succeeds.
        if final_path.exists():
            backup_path = (
                user_dir
                / (
                    f".backup_{secrets.token_hex(8)}"
                    f"{extension}"
                )
            )

            final_path.replace(
                backup_path
            )

        temp_path.replace(
            final_path
        )

        try:
            # Stage 4: persist the already-prepared chunks using the
            # user's logical/original filename. The DB transaction in
            # ingest_document() rolls back automatically on failure.
            document_id = ingest_document(
                str(final_path),
                user_id=current_user["id"],
                logical_filename=filename,
                prepared_results=
                    prepared_results
            )

        except Exception:
            # Database persistence failed. Restore the previous good
            # physical file (if one existed) so filesystem and DB stay
            # aligned with the pre-upload state.
            try:
                if final_path.exists():
                    final_path.unlink()
            except Exception:
                pass

            if (
                backup_path is not None
                and backup_path.exists()
            ):
                try:
                    backup_path.replace(
                        final_path
                    )
                except Exception:
                    pass

            raise

        # Database persistence succeeded. The backup is no longer
        # needed. A cleanup failure is non-fatal and is logged only.
        if (
            backup_path is not None
            and backup_path.exists()
        ):
            try:
                backup_path.unlink()
            except Exception as cleanup_error:
                print(
                    "Old document backup cleanup "
                    "failed:",
                    repr(
                        cleanup_error
                    )
                )

        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT
                        id,
                        filename,
                        created_at
                    FROM documents
                    WHERE
                        id = %s
                        AND user_id = %s
                    """,
                    (
                        document_id,
                        current_user["id"]
                    )
                )

                document = (
                    cur.fetchone()
                )

        return {
            "success": True,
            "id": (
                document[0]
                if document
                else None
            ),
            "filename":
                filename,
            "file_type":
                get_file_type(
                    filename
                ),
            "created_at": (
                document[2]
                if document
                else None
            ),
            "message": (
                "Document uploaded and "
                "successfully ingested "
                "into KnowledgeHub."
            )
        }

    except HTTPException:
        try:
            if temp_path.exists():
                temp_path.unlink()
        except Exception:
            pass

        # If an HTTP error somehow occurs after a backup was created,
        # restore the old file before returning the error.
        if (
            backup_path is not None
            and backup_path.exists()
            and not final_path.exists()
        ):
            try:
                backup_path.replace(
                    final_path
                )
            except Exception:
                pass

        raise

    except Exception as error:
        print(
            "Document upload or ingestion "
            "failed:",
            repr(
                error
            )
        )

        try:
            if temp_path.exists():
                temp_path.unlink()
        except Exception:
            pass

        # Best-effort recovery for any failure that occurred after
        # the previous file was backed up but before success.
        if (
            backup_path is not None
            and backup_path.exists()
        ):
            try:
                if final_path.exists():
                    final_path.unlink()

                backup_path.replace(
                    final_path
                )
            except Exception as recovery_error:
                print(
                    "Document file recovery "
                    "failed:",
                    repr(
                        recovery_error
                    )
                )

        raise HTTPException(
            status_code=500,
            detail=(
                "Document upload or "
                "ingestion failed."
            )
        )

    finally:
        try:
            release_document_upload_lock(
                upload_lock_connection,
                current_user["id"],
                filename
            )
        finally:
            await file.close()


@app.get("/documents")
def get_documents(
    current_user: dict = Depends(
        get_current_user
    )
):
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT
                    id,
                    filename,
                    created_at
                FROM documents
                WHERE user_id = %s
                ORDER BY
                    created_at DESC,
                    id DESC
                """,
                (
                    current_user["id"],
                )
            )

            rows = cur.fetchall()

    return {
        "documents": [
            {
                "id": row[0],
                "filename": row[1],
                "file_type":
                    get_file_type(
                        row[1]
                    ),
                "created_at": row[2]
            }
            for row in rows
        ]
    }


@app.get(
    "/documents/{document_id}/chunks/{chunk_index}"
)
def get_document_chunk(
    document_id: int,
    chunk_index: int,
    current_user: dict = Depends(
        get_current_user
    )
):
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
                    dc.page_number,
                    dc.section,
                    dc.metadata
                FROM document_chunks dc
                JOIN documents d
                    ON d.id = dc.document_id
                WHERE
                    dc.document_id = %s
                    AND dc.chunk_index = %s
                    AND d.user_id = %s
                """,
                (
                    document_id,
                    chunk_index,
                    current_user["id"]
                )
            )

            row = cur.fetchone()

    if row is None:
        return {
            "success": False,
            "message": (
                "Supporting document "
                "passage not found."
            )
        }

    return {
        "success": True,
        "chunk_id": row[0],
        "document_id": row[1],
        "filename": row[2],
        "file_type":
            get_file_type(
                row[2]
            ),
        "chunk_index": row[3],
        "content": row[4],
        "page_number": (
            row[5]
            if len(row) > 5
            else None
        ),
        "section": (
            row[6]
            if len(row) > 6
            else None
        ),
        "metadata": (
            row[7]
            if len(row) > 7
            and isinstance(
                row[7],
                dict
            )
            else {}
        )
    }


@app.delete(
    "/documents/{document_id}"
)
def delete_document(
    document_id: int,
    current_user: dict = Depends(
        get_current_user
    )
):
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT
                    id,
                    filename
                FROM documents
                WHERE
                    id = %s
                    AND user_id = %s
                """,
                (
                    document_id,
                    current_user["id"]
                )
            )

            document = cur.fetchone()

            if document is None:
                raise HTTPException(
                    status_code=404,
                    detail="Document not found."
                )

            filename = document[1]

            cur.execute(
                """
                DELETE FROM documents
                WHERE
                    id = %s
                    AND user_id = %s
                RETURNING id
                """,
                (
                    document_id,
                    current_user["id"]
                )
            )

            cur.fetchone()

        conn.commit()

    file_path = (
        get_user_documents_dir(
            current_user["id"]
        )
        / filename
    )

    file_deleted = True

    try:
        if file_path.exists():
            file_path.unlink()
    except Exception:
        file_deleted = False

    return {
        "success": True,
        "message": (
            "Document and its chunks "
            "were deleted successfully."
        ),
        "document_id":
            document_id,
        "filename":
            filename,
        "file_type":
            get_file_type(
                filename
            ),
        "file_deleted":
            file_deleted
    }


# ============================================================
# CHAT MANAGEMENT
# ============================================================


@app.post("/chats")
def create_chat(
    current_user: dict = Depends(
        get_current_user
    )
):
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO chat_sessions
                (
                    title,
                    user_id
                )
                VALUES (
                    %s,
                    %s
                )
                RETURNING
                    id,
                    title,
                    created_at,
                    updated_at
                """,
                (
                    "New Chat",
                    current_user["id"]
                )
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
def get_chats(
    current_user: dict = Depends(
        get_current_user
    )
):
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
                WHERE user_id = %s
                ORDER BY
                    updated_at DESC
                """,
                (
                    current_user["id"],
                )
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
def get_chat(
    session_id: int,
    current_user: dict = Depends(
        get_current_user
    )
):
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
                WHERE
                    id = %s
                    AND user_id = %s
                """,
                (
                    session_id,
                    current_user["id"]
                )
            )

            session = cur.fetchone()

            if session is None:
                raise HTTPException(
                    status_code=404,
                    detail="Chat not found."
                )

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
                ORDER BY
                    created_at ASC,
                    id ASC
                """,
                (
                    session_id,
                )
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
def delete_chat(
    session_id: int,
    current_user: dict = Depends(
        get_current_user
    )
):
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                DELETE FROM chat_sessions
                WHERE
                    id = %s
                    AND user_id = %s
                RETURNING id
                """,
                (
                    session_id,
                    current_user["id"]
                )
            )

            deleted = cur.fetchone()

        conn.commit()

    if deleted is None:
        raise HTTPException(
            status_code=404,
            detail="Chat not found."
        )

    return {
        "success": True,
        "message":
            "Chat deleted successfully."
    }


# ============================================================
# QUESTION / RAG
# ============================================================


@app.post("/ask")
async def ask_question(
    request: dict,
    current_user: dict = Depends(
        get_current_user
    )
):
    question = (
        request.get(
            "question",
            ""
        )
        .strip()
    )

    session_id = request.get(
        "session_id"
    )

    if not question:
        raise HTTPException(
            status_code=400,
            detail="Please provide a question."
        )

    if session_id is None:
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO chat_sessions
                    (
                        title,
                        user_id
                    )
                    VALUES (
                        %s,
                        %s
                    )
                    RETURNING id
                    """,
                    (
                        "New Chat",
                        current_user["id"]
                    )
                )

                session_id = (
                    cur.fetchone()[0]
                )

            conn.commit()

    else:
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT id
                    FROM chat_sessions
                    WHERE
                        id = %s
                        AND user_id = %s
                    """,
                    (
                        session_id,
                        current_user["id"]
                    )
                )

                session = cur.fetchone()

        if session is None:
            raise HTTPException(
                status_code=404,
                detail="Chat session not found."
            )

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT
                    question,
                    answer
                FROM chat_messages
                WHERE session_id = %s
                ORDER BY
                    created_at DESC,
                    id DESC
                LIMIT 4
                """,
                (
                    session_id,
                )
            )

            rows = cur.fetchall()

    rows.reverse()

    conversation_history = [
        {
            "question": row[0],
            "answer": row[1]
        }
        for row in rows
    ]

    result = generate_answer(
        question,
        conversation_history=
            conversation_history,
        user_id=current_user["id"]
    )

    answer = result["answer"]
    sources = result["sources"]

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
                VALUES (
                    %s,
                    %s,
                    %s,
                    %s::jsonb
                )
                """,
                (
                    session_id,
                    question,
                    answer,
                    json.dumps(
                        sources
                    )
                )
            )

            cur.execute(
                """
                UPDATE chat_sessions
                SET
                    title = CASE
                        WHEN title =
                            'New Chat'
                        THEN %s
                        ELSE title
                    END,
                    updated_at =
                        CURRENT_TIMESTAMP
                WHERE
                    id = %s
                    AND user_id = %s
                """,
                (
                    question[:80],
                    session_id,
                    current_user["id"]
                )
            )

        conn.commit()

    return {
        "question":
            question,
        "answer":
            answer,
        "sources":
            sources,
        "session_id":
            session_id
    }