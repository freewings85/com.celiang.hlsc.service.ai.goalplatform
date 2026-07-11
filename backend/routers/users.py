"""用户 + 各自的 Jira 身份。Token 加密存、只写不读。"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select

from db import get_session
from jira_client import JiraError, myself
from jira_config import auth_for_user
from models import Goal, User
from schemas import JiraTokenIn, UserIn, UserUpdate
from security import encrypt
from serializers import user_dict

router = APIRouter(prefix="/api/users", tags=["users"])


@router.get("")
def list_users(session: Session = Depends(get_session)):
    users = session.exec(select(User).order_by(User.id)).all()
    return [user_dict(u) for u in users]


@router.post("", status_code=201)
def create_user(payload: UserIn, session: Session = Depends(get_session)):
    u = User(**payload.model_dump())
    session.add(u)
    session.commit()
    session.refresh(u)
    return user_dict(u)


@router.patch("/{user_id}")
def update_user(user_id: int, payload: UserUpdate, session: Session = Depends(get_session)):
    u = session.get(User, user_id)
    if not u:
        raise HTTPException(404, "用户不存在")
    for k, v in payload.model_dump(exclude_unset=True).items():
        setattr(u, k, v)
    session.add(u)
    session.commit()
    session.refresh(u)
    return user_dict(u)


@router.delete("/{user_id}", status_code=204)
def delete_user(user_id: int, session: Session = Depends(get_session)):
    u = session.get(User, user_id)
    if not u:
        raise HTTPException(404, "用户不存在")
    # 解除目标对该用户的引用，避免悬空外键
    for g in session.exec(select(Goal).where(Goal.owner_user_id == user_id)).all():
        g.owner_user_id = None
        session.add(g)
    session.delete(u)
    session.commit()


@router.put("/{user_id}/jira-token")
def set_jira_token(user_id: int, payload: JiraTokenIn, session: Session = Depends(get_session)):
    """设置或清除该用户的 Jira API Token（加密存）。空字符串 = 清除。"""
    u = session.get(User, user_id)
    if not u:
        raise HTTPException(404, "用户不存在")
    u.jira_token_enc = encrypt(payload.token) if payload.token else ""
    if not payload.token:
        u.jira_account_id = ""
    session.add(u)
    session.commit()
    session.refresh(u)
    return user_dict(u)


@router.post("/{user_id}/jira/test")
def test_jira(user_id: int, session: Session = Depends(get_session)):
    """用该用户的凭据调 /myself 测连接，成功则回填 accountId。"""
    u = session.get(User, user_id)
    if not u:
        raise HTTPException(404, "用户不存在")
    auth = auth_for_user(session, u)
    if not auth.base_url:
        raise HTTPException(400, "尚未配置 Jira 站点（去设置里填 jira_base_url）")
    if not auth.ok:
        raise HTTPException(400, "该用户还没配 Jira 邮箱 / Token")
    try:
        me = myself(auth)
    except JiraError as e:
        raise HTTPException(502, f"连接 Jira 失败：{e.message}")
    except Exception as e:
        raise HTTPException(502, f"连接 Jira 失败：{e}")
    u.jira_account_id = me.get("accountId", "")
    session.add(u)
    session.commit()
    return {"ok": True, "account_id": u.jira_account_id, "display_name": me.get("displayName", "")}
