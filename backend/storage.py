import os
import secrets
from pathlib import Path


def _r2_enabled() -> bool:
    return os.getenv("STORAGE_BACKEND", "local").lower() == "r2"


def _r2_client():
    import boto3

    endpoint = os.getenv("R2_ENDPOINT")
    access_key = os.getenv("R2_ACCESS_KEY_ID")
    secret_key = os.getenv("R2_SECRET_ACCESS_KEY")

    if not endpoint or not access_key or not secret_key:
        raise RuntimeError(
            "R2 storage is enabled but R2_ENDPOINT, "
            "R2_ACCESS_KEY_ID, or R2_SECRET_ACCESS_KEY is missing."
        )

    return boto3.client(
        "s3",
        endpoint_url=endpoint,
        aws_access_key_id=access_key,
        aws_secret_access_key=secret_key,
        region_name="auto",
    )


def _bucket() -> str:
    bucket = os.getenv("R2_BUCKET")
    if not bucket:
        raise RuntimeError("R2_BUCKET is required when STORAGE_BACKEND=r2.")
    return bucket


def _object_key(user_id: int, filename: str) -> str:
    safe_name = Path(filename).name
    return f"users/{user_id}/{safe_name}"


def archive_document(user_id: int, filename: str, file_path: str) -> str | None:
    """Archive the original document in R2 when R2 storage is enabled.

    Returns the final object key. Local mode returns None so tests and
    development continue to use the existing filesystem behavior.
    """
    if not _r2_enabled():
        return None

    key = f"users/{user_id}/{secrets.token_hex(16)}/{Path(filename).name}"
    client = _r2_client()
    client.upload_file(file_path, _bucket(), key)
    return key


def delete_document_archive(user_id: int, object_key: str | None) -> bool:
    """Delete an exact persisted key; never derive a key from a filename."""
    if not _r2_enabled() or not object_key:
        return True
    if not object_key.startswith(f"users/{user_id}/"):
        raise ValueError("R2 key does not belong to the requested user")
    _r2_client().delete_object(Bucket=_bucket(), Key=object_key)
    return True


def delete_user_archive(user_id: int) -> int:
    if not _r2_enabled():
        return 0

    client = _r2_client()
    bucket = _bucket()
    prefix = f"users/{user_id}/"
    deleted = 0
    continuation = None

    while True:
        kwargs = {"Bucket": bucket, "Prefix": prefix}
        if continuation:
            kwargs["ContinuationToken"] = continuation

        response = client.list_objects_v2(**kwargs)
        objects = response.get("Contents", [])
        if objects:
            client.delete_objects(
                Bucket=bucket,
                Delete={"Objects": [{"Key": item["Key"]} for item in objects]},
            )
            deleted += len(objects)

        if not response.get("IsTruncated"):
            break
        continuation = response.get("NextContinuationToken")
        if not continuation:
            break

    return deleted


def ensure_storage_schema():
    """Run only when R2 is enabled; tracks immutable R2 object references."""
    if not _r2_enabled():
        return
    from db import get_connection
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("ALTER TABLE documents ADD COLUMN IF NOT EXISTS r2_object_key TEXT")
        conn.commit()
