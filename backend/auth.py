import base64
import hashlib
import hmac
import secrets
from datetime import (
    datetime,
    timedelta,
    timezone
)

from fastapi import (
    Depends,
    HTTPException
)
from fastapi.security import (
    HTTPAuthorizationCredentials,
    HTTPBearer
)

from db import get_connection


PASSWORD_ITERATIONS = 600_000
TOKEN_LIFETIME_DAYS = 7

security = HTTPBearer(
    auto_error=False
)


class AccountDisabledError(
    Exception
):
    pass


def normalize_email(
    email: str
) -> str:
    return (
        email
        .strip()
        .lower()
    )


def hash_password(
    password: str
) -> str:
    salt = secrets.token_bytes(16)

    derived_key = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt,
        PASSWORD_ITERATIONS
    )

    return (
        "pbkdf2_sha256"
        f"${PASSWORD_ITERATIONS}"
        f"${base64.b64encode(salt).decode('ascii')}"
        f"${base64.b64encode(derived_key).decode('ascii')}"
    )


def verify_password(
    password: str,
    stored_hash: str
) -> bool:
    try:
        (
            algorithm,
            iterations,
            salt_b64,
            hash_b64
        ) = stored_hash.split(
            "$",
            3
        )

        if algorithm != "pbkdf2_sha256":
            return False

        salt = base64.b64decode(
            salt_b64
        )

        expected_hash = (
            base64.b64decode(
                hash_b64
            )
        )

        candidate_hash = (
            hashlib.pbkdf2_hmac(
                "sha256",
                password.encode(
                    "utf-8"
                ),
                salt,
                int(iterations)
            )
        )

        return hmac.compare_digest(
            candidate_hash,
            expected_hash
        )

    except (
        ValueError,
        TypeError
    ):
        return False


def _hash_token(
    token: str
) -> str:
    return hashlib.sha256(
        token.encode("utf-8")
    ).hexdigest()


def create_access_token(
    user_id: int
) -> str:
    token = secrets.token_urlsafe(
        48
    )

    token_hash = _hash_token(
        token
    )

    expires_at = (
        datetime.now(
            timezone.utc
        )
        + timedelta(
            days=TOKEN_LIFETIME_DAYS
        )
    )

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                DELETE FROM auth_tokens
                WHERE expires_at
                    <= CURRENT_TIMESTAMP
                """
            )

            cur.execute(
                """
                INSERT INTO auth_tokens
                (
                    user_id,
                    token_hash,
                    expires_at
                )
                VALUES (
                    %s,
                    %s,
                    %s
                )
                """,
                (
                    user_id,
                    token_hash,
                    expires_at
                )
            )

        conn.commit()

    return token


def revoke_access_token(
    token: str
):
    token_hash = _hash_token(
        token
    )

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                DELETE FROM auth_tokens
                WHERE token_hash = %s
                """,
                (
                    token_hash,
                )
            )

        conn.commit()


def revoke_all_user_tokens(
    user_id: int
):
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


def authenticate_user(
    email: str,
    password: str
):
    normalized_email = (
        normalize_email(
            email
        )
    )

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT
                    id,
                    name,
                    email,
                    password_hash,
                    created_at,
                    role,
                    is_active,
                    disabled_at,
                    must_change_password
                FROM users
                WHERE LOWER(email) = %s
                """,
                (
                    normalized_email,
                )
            )

            row = cur.fetchone()

    if row is None:
        return None

    if not verify_password(
        password,
        row[3]
    ):
        return None

    if not row[6]:
        raise AccountDisabledError(
            "This account has been disabled. "
            "Contact your administrator."
        )

    return {
        "id": row[0],
        "name": row[1],
        "email": row[2],
        "created_at": row[4],
        "role": row[5],
        "is_active": row[6],
        "disabled_at": row[7],
        "must_change_password": row[8]
    }


def get_user_by_id(
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
                    created_at,
                    role,
                    is_active,
                    disabled_at,
                    must_change_password
                FROM users
                WHERE id = %s
                """,
                (
                    user_id,
                )
            )

            row = cur.fetchone()

    if row is None:
        return None

    return {
        "id": row[0],
        "name": row[1],
        "email": row[2],
        "created_at": row[3],
        "role": row[4],
        "is_active": row[5],
        "disabled_at": row[6],
        "must_change_password": row[7]
    }


def register_user(
    name: str,
    email: str,
    password: str
):
    clean_name = (
        name.strip()
    )

    normalized_email = (
        normalize_email(
            email
        )
    )

    if not clean_name:
        raise ValueError(
            "Name is required."
        )

    if (
        not normalized_email
        or "@" not in normalized_email
    ):
        raise ValueError(
            "Please provide a valid email address."
        )

    if len(password) < 8:
        raise ValueError(
            "Password must contain at least 8 characters."
        )

    password_hash = (
        hash_password(
            password
        )
    )

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT COUNT(*)
                FROM users
                """
            )

            user_count = (
                cur.fetchone()[0]
            )

            role = (
                "admin"
                if user_count == 0
                else "member"
            )

            cur.execute(
                """
                SELECT id
                FROM users
                WHERE LOWER(email) = %s
                """,
                (
                    normalized_email,
                )
            )

            if (
                cur.fetchone()
                is not None
            ):
                raise ValueError(
                    "An account with this email "
                    "already exists."
                )

            cur.execute(
                """
                INSERT INTO users
                (
                    name,
                    email,
                    password_hash,
                    role,
                    is_active
                )
                VALUES (
                    %s,
                    %s,
                    %s,
                    %s,
                    TRUE
                )
               RETURNING
    id,
    name,
    email,
    created_at,
    role,
    is_active,
    disabled_at,
    must_change_password
                """,
                (
                    clean_name,
                    normalized_email,
                    password_hash,
                    role
                )
            )

            row = cur.fetchone()

        conn.commit()

    return (
        {
            "id": row[0],
            "name": row[1],
            "email": row[2],
            "created_at": row[3],
            "role": row[4],
            "is_active": row[5],
            "disabled_at": row[6],
            "must_change_password": row[7]
        },
        user_count == 0
    )


def get_current_user(
    credentials:
        HTTPAuthorizationCredentials
        | None = Depends(
            security
        )
):
    if (
        credentials is None
        or credentials.scheme.lower()
        != "bearer"
    ):
        raise HTTPException(
            status_code=401,
            detail=(
                "Authentication required."
            )
        )

    token = (
        credentials.credentials
    )

    token_hash = (
        _hash_token(
            token
        )
    )

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT
                    u.id,
                    u.name,
                    u.email,
                    u.created_at,
                    u.role,
                    u.is_active,
                    u.disabled_at,
                    u.must_change_password
                FROM auth_tokens t
                JOIN users u
                    ON u.id = t.user_id
                WHERE
                    t.token_hash = %s
                    AND t.expires_at
                        > CURRENT_TIMESTAMP
                    AND u.is_active = TRUE
                """,
                (
                    token_hash,
                )
            )

            row = cur.fetchone()

    if row is None:
        raise HTTPException(
            status_code=401,
            detail=(
                "Invalid, expired, or disabled "
                "access token."
            )
        )

    return {
        "id": row[0],
        "name": row[1],
        "email": row[2],
        "created_at": row[3],
        "role": row[4],
        "is_active": row[5],
        "disabled_at": row[6],
        "must_change_password": row[7],
        "_token": token
    }


def update_user_password(
    user_id: int,
    new_password: str,
    *,
    must_change_password: bool
):
    if len(new_password) < 8:
        raise ValueError(
            "Password must contain at least 8 characters."
        )

    password_hash = hash_password(
        new_password
    )

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE users
                SET
                    password_hash = %s,
                    must_change_password = %s
                WHERE id = %s
                RETURNING id
                """,
                (
                    password_hash,
                    must_change_password,
                    user_id
                )
            )

            row = cur.fetchone()

        conn.commit()

    return row is not None


def require_admin(
    current_user: dict = Depends(
        get_current_user
    )
):
    if (
        current_user.get(
            "role"
        )
        != "admin"
    ):
        raise HTTPException(
            status_code=403,
            detail=(
                "Administrator access required."
            )
        )

    return current_user