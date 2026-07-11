"""从「全局设置(base_url) + 当前用户(email/token)」解析出一个 JiraAuth。"""
from __future__ import annotations

from typing import Optional

from sqlmodel import Session

from jira_client import JiraAuth
from models import AppSetting, User
from security import decrypt

JIRA_BASE_URL_KEY = "jira_base_url"


def get_setting(session: Session, key: str, default: str = "") -> str:
    row = session.get(AppSetting, key)
    return row.value if row else default


def set_setting(session: Session, key: str, value: str) -> None:
    row = session.get(AppSetting, key)
    if row:
        row.value = value
    else:
        row = AppSetting(key=key, value=value)
    session.add(row)
    session.commit()


def get_base_url(session: Session) -> str:
    return get_setting(session, JIRA_BASE_URL_KEY)


def auth_for_user(session: Session, user: Optional[User]) -> JiraAuth:
    base = get_base_url(session)
    if not user or not user.jira_token_enc:
        return JiraAuth(base_url=base, email=user.jira_email if user else "", token="")
    try:
        token = decrypt(user.jira_token_enc)
    except Exception:
        token = ""
    return JiraAuth(base_url=base, email=user.jira_email, token=token)
