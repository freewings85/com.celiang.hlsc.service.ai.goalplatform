"""共享依赖：当前用户（前端通过 X-User-Id 头传）。"""
from __future__ import annotations

from typing import Optional

from fastapi import Depends, Header, HTTPException
from sqlmodel import Session

from db import get_session
from models import User


def current_user(
    x_user_id: Optional[int] = Header(default=None),
    session: Session = Depends(get_session),
) -> Optional[User]:
    if x_user_id is None:
        return None
    return session.get(User, x_user_id)
