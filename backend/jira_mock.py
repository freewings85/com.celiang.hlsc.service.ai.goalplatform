"""忠实还原 Jira Cloud REST v3 的本地 mock（仅供开发/验证）。

实现了本项目用到的端点，请求/响应形状对齐真实 Jira：
    GET  /rest/api/3/myself
    POST /rest/api/3/issue
    GET  /rest/api/3/issue/{key}
    POST /rest/api/3/issueLink

运行：.venv/bin/uvicorn jira_mock:app --host 127.0.0.1 --port 8099
把主服务的 jira_base_url 指向 http://127.0.0.1:8099 即可端到端跑真集成代码。
换真 Jira 时只改 base_url + 用户填真 token，客户端代码零改动。
"""
from __future__ import annotations

import base64
import itertools

from fastapi import FastAPI, Header, HTTPException, Request

app = FastAPI(title="Jira Mock (dev only)")

_ISSUES: dict[str, dict] = {}
_LINKS: list[dict] = []
_counter: dict[str, "itertools.count"] = {}


def _require_auth(authorization: str | None) -> str:
    """校验 Basic Auth 存在，返回 email（就像真 Jira 会认证一样）。"""
    if not authorization or not authorization.lower().startswith("basic "):
        raise HTTPException(401, "Unauthorized (missing basic auth)")
    try:
        decoded = base64.b64decode(authorization.split(" ", 1)[1]).decode()
        email = decoded.split(":", 1)[0]
    except Exception:
        raise HTTPException(401, "Bad auth header")
    if not email:
        raise HTTPException(401, "Empty email")
    return email


@app.get("/rest/api/3/myself")
def myself(authorization: str | None = Header(None)):
    email = _require_auth(authorization)
    return {
        "accountId": "acct-" + email.split("@")[0],
        "emailAddress": email,
        "displayName": email.split("@")[0],
        "active": True,
    }


@app.post("/rest/api/3/issue", status_code=201)
async def create_issue(request: Request, authorization: str | None = Header(None)):
    _require_auth(authorization)
    body = await request.json()
    fields = (body or {}).get("fields", {})
    project = (fields.get("project") or {}).get("key")
    if not project:
        raise HTTPException(400, "project is required")
    if not fields.get("summary"):
        raise HTTPException(400, "summary is required")
    c = _counter.setdefault(project, itertools.count(1))
    n = next(c)
    key = f"{project}-{n}"
    issue = {
        "id": str(10000 + n),
        "key": key,
        "self": f"http://127.0.0.1:8099/rest/api/3/issue/{key}",
        "fields": fields,
    }
    _ISSUES[key] = issue
    return {"id": issue["id"], "key": key, "self": issue["self"]}


@app.get("/rest/api/3/issue/{key}")
def get_issue(key: str, authorization: str | None = Header(None)):
    _require_auth(authorization)
    issue = _ISSUES.get(key)
    if not issue:
        raise HTTPException(404, f"Issue does not exist: {key}")
    return issue


@app.post("/rest/api/3/issueLink", status_code=201)
async def create_link(request: Request, authorization: str | None = Header(None)):
    _require_auth(authorization)
    body = await request.json()
    inward = (body.get("inwardIssue") or {}).get("key")
    outward = (body.get("outwardIssue") or {}).get("key")
    if not inward or not outward:
        raise HTTPException(400, "inwardIssue and outwardIssue required")
    _LINKS.append({"type": (body.get("type") or {}).get("name", "Relates"), "inward": inward, "outward": outward})
    return {}


@app.get("/_mock/state")
def state():
    """仅供测试断言：看 mock 里建了哪些 issue / link。"""
    return {"issues": list(_ISSUES.keys()), "links": _LINKS}
