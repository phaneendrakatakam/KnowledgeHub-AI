from db import get_connection


def reset_auth_test_data():
    """
    ONE-TIME LOCAL DEVELOPMENT RESET.

    Deletes authentication-era user data so authentication
    can be tested from a genuinely fresh state.

    This removes:
    - chat messages through chat-session cascade
    - chat sessions
    - document chunks through document cascade
    - documents
    - auth tokens
    - users

    Run only when you intentionally want to restart local
    authentication testing from zero.
    """

    confirmation = input(
        "Type RESET to delete all local KnowledgeHub "
        "users, chats, documents, and auth tokens: "
    ).strip()

    if confirmation != "RESET":
        print("Reset cancelled.")
        return

    with get_connection() as conn:
        with conn.cursor() as cur:
            # Child rows in chat_messages and document_chunks
            # are removed by existing ON DELETE CASCADE rules.
            cur.execute(
                """
                DELETE FROM chat_sessions
                """
            )

            cur.execute(
                """
                DELETE FROM documents
                """
            )

            cur.execute(
                """
                DELETE FROM auth_tokens
                """
            )

            cur.execute(
                """
                DELETE FROM users
                """
            )

            # Reset identity sequences when available so the next
            # local test account starts cleanly from ID 1.
            for table_name, column_name in (
                ("users", "id"),
                ("auth_tokens", "id"),
                ("chat_sessions", "id"),
                ("documents", "id"),
            ):
                cur.execute(
                    """
                    SELECT pg_get_serial_sequence(
                        %s,
                        %s
                    )
                    """,
                    (
                        table_name,
                        column_name
                    )
                )

                sequence_row = cur.fetchone()

                if (
                    sequence_row
                    and sequence_row[0]
                ):
                    cur.execute(
                        f"ALTER SEQUENCE "
                        f"{sequence_row[0]} "
                        f"RESTART WITH 1"
                    )

        conn.commit()

    print()
    print("KnowledgeHub authentication test data reset.")
    print("Next registered user will start with:")
    print("- 0 documents")
    print("- 0 conversations")
    print("- a fresh private workspace")


if __name__ == "__main__":
    reset_auth_test_data()
