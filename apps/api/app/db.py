"""SQLite 持久化：账号、会话、错题、学情事件。

刻意用标准库 sqlite3，不引入 ORM——数据模型很小，手写 SQL 更透明。
"""
from __future__ import annotations

import json
import sqlite3
import time
import uuid
from pathlib import Path
from typing import Any

from .config import DB_PATH

_SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    account      TEXT PRIMARY KEY,
    pwd_hash     TEXT NOT NULL,
    created_at   REAL NOT NULL,
    records      TEXT NOT NULL DEFAULT '{}'
);
CREATE TABLE IF NOT EXISTS conversations (
    id           TEXT PRIMARY KEY,
    account      TEXT NOT NULL,
    module_key   TEXT NOT NULL DEFAULT '__global__',
    title        TEXT NOT NULL DEFAULT '',
    updated_at   REAL NOT NULL
);
CREATE TABLE IF NOT EXISTS messages (
    id           TEXT PRIMARY KEY,
    conv_id      TEXT NOT NULL,
    role         TEXT NOT NULL,
    content      TEXT NOT NULL,
    payload      TEXT NOT NULL DEFAULT '{}',
    created_at   REAL NOT NULL
);
CREATE TABLE IF NOT EXISTS wrongbook (
    id           TEXT PRIMARY KEY,
    account      TEXT NOT NULL,
    question     TEXT NOT NULL,
    wrong_answer TEXT DEFAULT '',
    root_cause   TEXT DEFAULT '',
    trace_ref    TEXT DEFAULT '',
    correct      TEXT DEFAULT '',
    pitfall      TEXT DEFAULT '',
    kp_ids       TEXT DEFAULT '[]',
    source       TEXT DEFAULT '',
    created_at   REAL NOT NULL
);
CREATE TABLE IF NOT EXISTS events (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    account      TEXT NOT NULL,
    kind         TEXT NOT NULL,
    payload      TEXT NOT NULL DEFAULT '{}',
    created_at   REAL NOT NULL
);
CREATE TABLE IF NOT EXISTS mastery (
    account      TEXT NOT NULL,
    kp_id        TEXT NOT NULL,
    score        REAL NOT NULL DEFAULT 0,
    attempts     INTEGER NOT NULL DEFAULT 0,
    correct      INTEGER NOT NULL DEFAULT 0,
    state        TEXT NOT NULL DEFAULT '未学',
    last_signal  TEXT DEFAULT '',
    last_at      REAL NOT NULL,
    PRIMARY KEY (account, kp_id)
);
CREATE INDEX IF NOT EXISTS idx_msg_conv ON messages(conv_id, created_at);
CREATE INDEX IF NOT EXISTS idx_ev_account ON events(account, created_at);
"""


def _hash_pwd(pwd: str, salt: str = "reactor-physics") -> str:
    import hashlib

    return hashlib.sha256((salt + pwd).encode("utf-8")).hexdigest()


class Store:
    def __init__(self, path: Path | str | None = None):
        self.path = Path(path or DB_PATH)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(str(self.path), check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._conn.executescript(_SCHEMA)
        self._conn.commit()

    # ---------------- 账号
    def login_or_register(self, account: str, password: str) -> dict:
        """首次输入自动建号（对齐参考作品的"学号/姓名即账号"）。"""
        account = account.strip()
        row = self._conn.execute("SELECT * FROM users WHERE account=?", (account,)).fetchone()
        if row is None:
            self._conn.execute(
                "INSERT INTO users(account,pwd_hash,created_at) VALUES(?,?,?)",
                (account, _hash_pwd(password), time.time()),
            )
            self._conn.commit()
            return {"account": account, "created": True, "records": {}}
        if row["pwd_hash"] != _hash_pwd(password):
            raise PermissionError("密码不正确")
        return {
            "account": account,
            "created": False,
            "records": json.loads(row["records"] or "{}"),
        }

    def get_records(self, account: str) -> dict:
        row = self._conn.execute("SELECT records FROM users WHERE account=?", (account,)).fetchone()
        return json.loads(row["records"]) if row else {}

    def put_records(self, account: str, data: dict) -> int:
        cur = self._conn.execute(
            "UPDATE users SET records=? WHERE account=?",
            (json.dumps(data, ensure_ascii=False), account),
        )
        self._conn.commit()
        return cur.rowcount

    # ---------------- 会话
    def new_conversation(self, account: str, module_key: str, title: str) -> str:
        cid = f"conv:{module_key}:{uuid.uuid4().hex[:10]}"
        self._conn.execute(
            "INSERT INTO conversations(id,account,module_key,title,updated_at) VALUES(?,?,?,?,?)",
            (cid, account, module_key, title[:80], time.time()),
        )
        self._conn.commit()
        return cid

    def get_or_create_conversation(self, account: str, module_key: str, title: str) -> str:
        """当天同一模块复用同一个会话（避免每问一句就新建一条会话记录）。"""
        import time as _t

        day_start = _t.time() - 24 * 3600
        row = self._conn.execute(
            "SELECT id FROM conversations WHERE account=? AND module_key=? AND updated_at>=? "
            "ORDER BY updated_at DESC LIMIT 1",
            (account, module_key, day_start),
        ).fetchone()
        if row:
            return row["id"]
        return self.new_conversation(account, module_key, title)

    def append_message(self, conv_id: str, role: str, content: str, payload: dict | None = None) -> str:
        mid = "m_" + uuid.uuid4().hex[:12]
        self._conn.execute(
            "INSERT INTO messages(id,conv_id,role,content,payload,created_at) VALUES(?,?,?,?,?,?)",
            (mid, conv_id, role, content, json.dumps(payload or {}, ensure_ascii=False), time.time()),
        )
        self._conn.execute("UPDATE conversations SET updated_at=? WHERE id=?", (time.time(), conv_id))
        self._conn.commit()
        return mid

    def messages(self, conv_id: str, limit: int = 200) -> list[dict]:
        rows = self._conn.execute(
            "SELECT * FROM messages WHERE conv_id=? ORDER BY created_at LIMIT ?", (conv_id, limit)
        ).fetchall()
        return [
            {
                "id": r["id"],
                "role": r["role"],
                "content": r["content"],
                "payload": json.loads(r["payload"] or "{}"),
                "created_at": r["created_at"],
            }
            for r in rows
        ]

    # ---------------- 历史会话
    def list_conversations(self, account: str, limit: int = 30) -> list[dict]:
        rows = self._conn.execute(
            """SELECT c.id, c.module_key, c.title, c.updated_at,
                      (SELECT COUNT(*) FROM messages m WHERE m.conv_id=c.id) AS count
               FROM conversations c WHERE c.account=?
               ORDER BY c.updated_at DESC LIMIT ?""",
            (account, limit),
        ).fetchall()
        return [dict(r) for r in rows]

    def conversation_owner(self, conv_id: str) -> str | None:
        row = self._conn.execute(
            "SELECT account FROM conversations WHERE id=?", (conv_id,)
        ).fetchone()
        return row["account"] if row else None

    # ---------------- 学习者模型（掌握度）
    def list_mastery(self, account: str) -> dict:
        rows = self._conn.execute(
            "SELECT * FROM mastery WHERE account=?", (account,)
        ).fetchall()
        out: dict[str, dict] = {}
        for r in rows:
            out[r["kp_id"]] = {
                "score": r["score"],
                "attempts": r["attempts"],
                "correct": r["correct"],
                "state": r["state"],
                "last_signal": r["last_signal"] or "",
                "last_at": r["last_at"],
            }
        return out

    def upsert_mastery(self, account: str, items: dict[str, dict]) -> None:
        for kp_id, item in items.items():
            self._conn.execute(
                """INSERT INTO mastery(account,kp_id,score,attempts,correct,state,last_signal,last_at)
                   VALUES(?,?,?,?,?,?,?,?)
                   ON CONFLICT(account,kp_id) DO UPDATE SET
                     score=excluded.score, attempts=excluded.attempts, correct=excluded.correct,
                     state=excluded.state, last_signal=excluded.last_signal, last_at=excluded.last_at""",
                (
                    account,
                    kp_id,
                    float(item.get("score") or 0),
                    int(item.get("attempts") or 0),
                    int(item.get("correct") or 0),
                    str(item.get("state") or "未学"),
                    str(item.get("last_signal") or ""),
                    float(item.get("last_at") or time.time()),
                ),
            )
        self._conn.commit()

    # ---------------- 错题本
    def add_wrong(self, account: str, rec: dict) -> str:
        wid = "w_" + uuid.uuid4().hex[:12]
        self._conn.execute(
            """INSERT INTO wrongbook(id,account,question,wrong_answer,root_cause,trace_ref,
                                     correct,pitfall,kp_ids,source,created_at)
               VALUES(?,?,?,?,?,?,?,?,?,?,?)""",
            (
                wid,
                account,
                rec.get("question", ""),
                rec.get("wrong_answer", ""),
                rec.get("root_cause", ""),
                rec.get("trace_ref", ""),
                rec.get("correct", ""),
                rec.get("pitfall", ""),
                json.dumps(rec.get("kp_ids") or [], ensure_ascii=False),
                rec.get("source", ""),
                time.time(),
            ),
        )
        self._conn.commit()
        return wid

    def wrong_exists(self, account: str, question: str, trace_ref: str) -> bool:
        row = self._conn.execute(
            "SELECT 1 FROM wrongbook WHERE account=? AND question=? AND trace_ref=? LIMIT 1",
            (account, question, trace_ref),
        ).fetchone()
        return row is not None
    def list_wrong(self, account: str, limit: int = 50) -> list[dict]:
        rows = self._conn.execute(
            "SELECT * FROM wrongbook WHERE account=? ORDER BY created_at DESC LIMIT ?",
            (account, limit),
        ).fetchall()
        out = []
        for r in rows:
            d = dict(r)
            d["kp_ids"] = json.loads(d.get("kp_ids") or "[]")
            out.append(d)
        return out

    # ---------------- 学情埋点
    def log_event(self, account: str, kind: str, payload: dict | None = None) -> None:
        self._conn.execute(
            "INSERT INTO events(account,kind,payload,created_at) VALUES(?,?,?,?)",
            (account, kind, json.dumps(payload or {}, ensure_ascii=False), time.time()),
        )
        self._conn.commit()

    def event_stats(self, account: str) -> dict:
        rows = self._conn.execute(
            "SELECT kind, COUNT(*) n FROM events WHERE account=? GROUP BY kind", (account,)
        ).fetchall()
        return {r["kind"]: r["n"] for r in rows}

    # ---------------- 教师端聚合（跨账号）
    def admin_overview(self) -> dict:
        c = self._conn

        def one(sql: str, default=0):
            r = c.execute(sql).fetchone()
            return (r[0] if r and r[0] is not None else default)

        kinds = {
            r["kind"]: r["n"]
            for r in c.execute("SELECT kind, COUNT(*) n FROM events GROUP BY kind").fetchall()
        }
        roots = [
            {"root_cause": r["root_cause"] or "未标注", "n": r["n"]}
            for r in c.execute(
                "SELECT root_cause, COUNT(*) n FROM wrongbook GROUP BY root_cause ORDER BY n DESC"
            ).fetchall()
        ]
        recent_wrong = [
            dict(r) for r in c.execute(
                "SELECT id, account, question, root_cause, created_at FROM wrongbook "
                "ORDER BY created_at DESC LIMIT 8"
            ).fetchall()
        ]
        # 拒绝率 & 覆盖率分布
        # ⚠ 口径说明：只有 kb_search 事件同时记录 gated 与 coverage，
        # 所以两个指标都只统计 kb_search，保证分母一致。
        # （之前混入 answer 事件，导致"拒答率 100% + 覆盖率 0%"这种自相矛盾的展示。）
        rows = c.execute(
            "SELECT payload FROM events WHERE kind='kb_search'"
        ).fetchall()
        gated = total = 0
        covs: list[float] = []
        for r in rows:
            try:
                p = json.loads(r["payload"] or "{}")
            except json.JSONDecodeError:
                continue
            if isinstance(p.get("coverage"), (int, float)):
                total += 1
                covs.append(float(p["coverage"]))
                if p.get("gated"):
                    gated += 1
        # 账号数：注册表 + 只走 X-Account 提问的账号（对话不会自动建 users 行）
        registered = one("SELECT COUNT(*) FROM users")
        active = one("SELECT COUNT(DISTINCT account) FROM conversations")
        total_accounts = one(
            "SELECT COUNT(*) FROM (SELECT account FROM users UNION SELECT account FROM conversations)"
        )
        # 学习者模型：掌握度状态分布 + 最需要关注的知识点
        mastery_states = {
            (r["state"] or "未学"): r["n"]
            for r in c.execute(
                "SELECT state, COUNT(*) n FROM mastery GROUP BY state"
            ).fetchall()
        }
        mastery_top = [
            {"kp_id": r["kp_id"], "state": r["state"], "score": r["score"],
             "attempts": r["attempts"], "accounts": r["accounts"]}
            for r in c.execute(
                "SELECT kp_id, state, MAX(score) score, SUM(attempts) attempts, COUNT(*) accounts "
                "FROM mastery WHERE state IN ('需复习','在学') "
                "GROUP BY kp_id ORDER BY attempts DESC LIMIT 8"
            ).fetchall()
        ]
        return {
            "users": total_accounts,
            "users_registered": registered,
            "users_active": active,
            "conversations": one("SELECT COUNT(*) FROM conversations"),
            "messages": one("SELECT COUNT(*) FROM messages"),
            "wrongbook": one("SELECT COUNT(*) FROM wrongbook"),
            "mastery_states": mastery_states,
            "mastery_top": mastery_top,
            "events": kinds,
            "events_total": sum(kinds.values()),
            "root_causes": roots,
            "recent_wrong": recent_wrong,
            "gate": {
                "samples": total,
                "gated": gated,
                "reject_rate": round(gated / total, 3) if total else None,
                "coverage_avg": round(sum(covs) / len(covs), 3) if covs else None,
                "coverage_min": round(min(covs), 3) if covs else None,
                "coverage_max": round(max(covs), 3) if covs else None,
            },
        }

    def admin_users(self) -> list[dict]:
        rows = self._conn.execute(
            "SELECT u.account, u.created_at, "
            " (SELECT COUNT(*) FROM events e WHERE e.account=u.account) ev, "
            " (SELECT COUNT(*) FROM wrongbook w WHERE w.account=u.account) wb "
            "FROM users u ORDER BY ev DESC LIMIT 50"
        ).fetchall()
        return [dict(r) for r in rows]

    def close(self) -> None:
        self._conn.close()
