import os

import psycopg
from dotenv import load_dotenv


load_dotenv()


def get_connection():
    return psycopg.connect(
        host=os.getenv(
            "POSTGRES_HOST",
            "localhost"
        ),
        port=os.getenv(
            "POSTGRES_PORT",
            "5432"
        ),
        dbname=os.getenv(
            "POSTGRES_DB",
            "knowledgehub"
        ),
        user=os.getenv(
            "POSTGRES_USER",
            "postgres"
        ),
        password=os.getenv(
            "POSTGRES_PASSWORD"
        ),
    )


def ensure_auth_schema():
    """
    Upgrade an existing KnowledgeHub database for local
    multi-user authentication and user administration.

    Existing pre-authentication rows may remain unowned
    (user_id IS NULL). New accounts never automatically
    inherit legacy documents or chat sessions.

    The oldest existing user is promoted to admin only when
    the database currently has no admin account.
    """

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS users (
                    id BIGSERIAL PRIMARY KEY,
                    name TEXT NOT NULL,
                    email TEXT NOT NULL,
                    password_hash TEXT NOT NULL,
                    created_at TIMESTAMPTZ NOT NULL
                        DEFAULT CURRENT_TIMESTAMP
                )
                """
            )

            cur.execute(
                """
                ALTER TABLE users
                ADD COLUMN IF NOT EXISTS
                    role TEXT NOT NULL
                    DEFAULT 'member'
                """
            )

            cur.execute(
                """
                ALTER TABLE users
                ADD COLUMN IF NOT EXISTS
                    is_active BOOLEAN NOT NULL
                    DEFAULT TRUE
                """
            )

            cur.execute(
                """
                ALTER TABLE users
                ADD COLUMN IF NOT EXISTS
                    disabled_at TIMESTAMPTZ
                """
            )
            cur.execute(
                """
                ALTER TABLE users
                ADD COLUMN IF NOT EXISTS
                    must_change_password BOOLEAN NOT NULL
                    DEFAULT FALSE
                """
            )

            cur.execute(
                """
                CREATE UNIQUE INDEX IF NOT EXISTS
                    users_email_lower_uidx
                ON users (LOWER(email))
                """
            )

            cur.execute(
                """
                CREATE INDEX IF NOT EXISTS
                    users_role_idx
                ON users (role)
                """
            )

            cur.execute(
                """
                CREATE INDEX IF NOT EXISTS
                    users_is_active_idx
                ON users (is_active)
                """
            )

            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS auth_tokens (
                    id BIGSERIAL PRIMARY KEY,
                    user_id BIGINT NOT NULL
                        REFERENCES users(id)
                        ON DELETE CASCADE,
                    token_hash TEXT NOT NULL UNIQUE,
                    created_at TIMESTAMPTZ NOT NULL
                        DEFAULT CURRENT_TIMESTAMP,
                    expires_at TIMESTAMPTZ NOT NULL
                )
                """
            )

            cur.execute(
                """
                CREATE INDEX IF NOT EXISTS
                    auth_tokens_user_id_idx
                ON auth_tokens (user_id)
                """
            )

            cur.execute(
                """
                ALTER TABLE documents
                ADD COLUMN IF NOT EXISTS user_id BIGINT
                """
            )

            cur.execute(
                """
                ALTER TABLE chat_sessions
                ADD COLUMN IF NOT EXISTS user_id BIGINT
                """
            )
            cur.execute(
                """
                ALTER TABLE document_chunks
                ADD COLUMN IF NOT EXISTS
                    page_number INTEGER
                """
            )

            cur.execute(
                """
                ALTER TABLE document_chunks
                ADD COLUMN IF NOT EXISTS
                    section TEXT
                """
            )

            cur.execute(
                """
                ALTER TABLE document_chunks
                ADD COLUMN IF NOT EXISTS
                    metadata JSONB NOT NULL
                    DEFAULT '{}'::jsonb
                """
            )


            cur.execute(
                """
                DO $$
                BEGIN
                    IF NOT EXISTS (
                        SELECT 1
                        FROM pg_constraint
                        WHERE conname =
                            'documents_user_id_fkey'
                    ) THEN
                        ALTER TABLE documents
                        ADD CONSTRAINT
                            documents_user_id_fkey
                        FOREIGN KEY (user_id)
                        REFERENCES users(id)
                        ON DELETE CASCADE;
                    END IF;
                END
                $$;
                """
            )

            cur.execute(
                """
                DO $$
                BEGIN
                    IF NOT EXISTS (
                        SELECT 1
                        FROM pg_constraint
                        WHERE conname =
                            'chat_sessions_user_id_fkey'
                    ) THEN
                        ALTER TABLE chat_sessions
                        ADD CONSTRAINT
                            chat_sessions_user_id_fkey
                        FOREIGN KEY (user_id)
                        REFERENCES users(id)
                        ON DELETE CASCADE;
                    END IF;
                END
                $$;
                """
            )

            # Older KnowledgeHub versions may have a global
            # UNIQUE(filename) constraint. Multi-user V3 needs
            # uniqueness only inside each user's knowledge base.
            cur.execute(
                """
                DO $$
                DECLARE
                    constraint_record RECORD;
                BEGIN
                    FOR constraint_record IN
                        SELECT
                            con.conname
                        FROM pg_constraint con
                        JOIN pg_class rel
                            ON rel.oid = con.conrelid
                        JOIN pg_namespace nsp
                            ON nsp.oid = rel.relnamespace
                        WHERE
                            rel.relname = 'documents'
                            AND con.contype = 'u'
                            AND pg_get_constraintdef(
                                con.oid
                            ) ~
                            '^UNIQUE \\(filename\\)$'
                    LOOP
                        EXECUTE format(
                            'ALTER TABLE documents '
                            'DROP CONSTRAINT %I',
                            constraint_record.conname
                        );
                    END LOOP;
                END
                $$;
                """
            )

            cur.execute(
                """
                CREATE UNIQUE INDEX IF NOT EXISTS
                    documents_user_filename_uidx
                ON documents (user_id, filename)
                """
            )

            cur.execute(
                """
                CREATE INDEX IF NOT EXISTS
                    documents_user_id_idx
                ON documents (user_id)
                """
            )

            cur.execute(
                """
                CREATE INDEX IF NOT EXISTS
                    chat_sessions_user_id_idx
                ON chat_sessions (user_id)
                """
            )

            # Existing installations already have users created
            # before the admin feature existed. Ensure there is
            # exactly an initial management account when no admin
            # has been assigned yet.
            cur.execute(
                """
                SELECT COUNT(*)
                FROM users
                WHERE role = 'admin'
                """
            )

            admin_count = (
                cur.fetchone()[0]
            )

            if admin_count == 0:
                cur.execute(
                    """
                    UPDATE users
                    SET role = 'admin'
                    WHERE id = (
                        SELECT id
                        FROM users
                        ORDER BY id
                        LIMIT 1
                    )
                    """
                )

        conn.commit()