import sys
from pathlib import Path

import pytest
from fastapi import HTTPException

sys.path.insert(
    0,
    str(
        Path(__file__).resolve().parents[1]
        / "backend"
    )
)

import auth


def test_require_admin_accepts_admin():
    user = {
        "id": 1,
        "role": "admin"
    }

    assert (
        auth.require_admin(
            user
        )
        == user
    )


def test_require_admin_rejects_member():
    with pytest.raises(
        HTTPException
    ) as exc:
        auth.require_admin(
            {
                "id": 2,
                "role": "member"
            }
        )

    assert exc.value.status_code == 403


def test_disabled_account_error_is_specific():
    error = auth.AccountDisabledError(
        "disabled"
    )

    assert str(error) == "disabled"



def test_update_user_password_rejects_short_password():
    with pytest.raises(
        ValueError
    ):
        auth.update_user_password(
            1,
            "short",
            must_change_password=True
        )