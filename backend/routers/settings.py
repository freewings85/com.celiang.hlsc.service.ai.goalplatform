"""全局设置：Jira 站点 URL。"""
from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlmodel import Session

from db import get_session
from jira_config import JIRA_BASE_URL_KEY, get_base_url, set_setting
from schemas import JiraSettingIn

router = APIRouter(prefix="/api/settings", tags=["settings"])


@router.get("/jira")
def get_jira_setting(session: Session = Depends(get_session)):
    return {"jira_base_url": get_base_url(session)}


@router.put("/jira")
def put_jira_setting(payload: JiraSettingIn, session: Session = Depends(get_session)):
    set_setting(session, JIRA_BASE_URL_KEY, payload.jira_base_url.strip())
    return {"jira_base_url": get_base_url(session)}
