"""全局设置：Jira 站点地址 + 建 issue 用的类型名。"""
from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlmodel import Session

from db import get_session
from jira_config import jira_base_url, jira_issue_type, set_setting
from schemas import JiraSettingsIn

router = APIRouter(prefix="/api/settings", tags=["settings"])


@router.get("/jira")
def get_jira(session: Session = Depends(get_session)):
    base = jira_base_url(session)
    return {"base_url": base, "issue_type": jira_issue_type(session), "configured": bool(base)}


@router.put("/jira")
def put_jira(payload: JiraSettingsIn, session: Session = Depends(get_session)):
    if payload.base_url is not None:
        set_setting(session, "jira_base_url", payload.base_url.strip())
    if payload.issue_type is not None:
        set_setting(session, "jira_issue_type", payload.issue_type.strip())
    return get_jira(session)
