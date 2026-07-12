"""设置读写 + 用「当前登录用户的 Jira 用户名/密码」构造 JiraAuth。"""
from __future__ import annotations

from typing import Optional

from sqlmodel import Session

from models import AppSetting, User

# 默认站点（可在「用户 / 集成」页改）。指向自建 Jira Server。
DEFAULT_BASE_URL = "http://192.168.100.130:18080"
DEFAULT_ISSUE_TYPE = "任务"
LINK_TYPE = "Relates"


def get_setting(session: Session, key: str, default: str = "") -> str:
    row = session.get(AppSetting, key)
    return row.value if row and row.value else default


def set_setting(session: Session, key: str, value: str) -> None:
    row = session.get(AppSetting, key)
    if row:
        row.value = value
    else:
        row = AppSetting(key=key, value=value)
    session.add(row)
    session.commit()


def jira_base_url(session: Session) -> str:
    return get_setting(session, "jira_base_url", DEFAULT_BASE_URL).rstrip("/")


def jira_issue_type(session: Session) -> str:
    return get_setting(session, "jira_issue_type", DEFAULT_ISSUE_TYPE)


def auth_for_user(session: Session, user: Optional[User]):
    """Jira Server：Basic auth = 站点 + 该用户登录时存下的用户名/密码。"""
    from jira_client import JiraAuth
    from security import decrypt

    base = jira_base_url(session)
    if not user or not user.jira_username or not user.jira_password_enc:
        return JiraAuth(base_url="", username="", password="")
    try:
        pw = decrypt(user.jira_password_enc)
    except Exception:
        return JiraAuth(base_url="", username="", password="")
    return JiraAuth(base_url=base, username=user.jira_username, password=pw)
