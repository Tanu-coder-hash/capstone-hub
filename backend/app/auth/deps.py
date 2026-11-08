from dataclasses import dataclass
from fastapi import Header


@dataclass
class CurrentUser:
    id: int
    role: str


def get_current_user(
    x_user_id: int = Header(1),
    x_user_role: str = Header("student")
):
    return CurrentUser(
        id=x_user_id,
        role=x_user_role
    )