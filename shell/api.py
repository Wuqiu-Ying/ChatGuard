#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ChatGuard BFF（本地小后端）
- 提供静态页面
- POST /api/analyze 实现"上传 → OCR 智能体 → 研判工作流"三步聚合
- API Key 只存在服务端，前端拿不到
小程序端只要调同一个 POST /api/analyze 即可复用。

用法：
    python api.py            # 默认 http://127.0.0.1:8080
    PORT=9000 python api.py
"""

import json, os, sys, time, uuid, base64, urllib.request, urllib.error
import threading, webbrowser, socket, sqlite3, tempfile
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler

BASE = "https://agent.teleai.com.cn"
# 平台 API Key 从环境变量读取；仓库中不保存任何密钥。
# 本地运行时：复制 .env.example 为 .env 并填入自己的 Key，或直接 export。
OCR_KEY = os.environ.get("CG_OCR_KEY", "")
WF_KEY  = os.environ.get("CG_WF_KEY", "")
PORT    = int(os.environ.get("PORT", "15000"))
ROOT    = os.path.dirname(os.path.abspath(__file__))
TIMEOUT = 180

# 样例模式：由控制面板显式开启（断网 / 额度不足时用）。
# 关闭时，平台不可用会**显式报错**，不静默降级。
SAMPLE_MODE = False

# 允许控制台注入带日志的 Server 子类
SERVER_CLASS = ThreadingHTTPServer

# ---- 真实数据（live）：SQLite 持久化 ----
# 只落盘"脱敏结构化事件"（类型 / 等级 / 时间 / 建议 / 载体），**从不保存聊天原文**。
_DB_LOCK = threading.Lock()
_DB = {"path": None}
DB_SCHEMA = """
CREATE TABLE IF NOT EXISTS events(
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  ts TEXT NOT NULL, anon TEXT, type TEXT, level TEXT,
  victim_state TEXT, action TEXT, mode TEXT, carriers TEXT
);
CREATE INDEX IF NOT EXISTS idx_events_ts ON events(ts);
"""
DB_KEEP = 500


def _db_path():
    """优先放在程序目录，不可写时退回系统临时目录。"""
    if _DB["path"]:
        return _DB["path"]
    base = ROOT or os.path.dirname(os.path.abspath(__file__))
    for cand in (os.path.join(base, "events.db"),
                 os.path.join(tempfile.gettempdir(), "chatguard_events.db"),
                 ":memory:"):
        try:
            con = sqlite3.connect(cand, timeout=5)
            con.executescript(DB_SCHEMA)
            con.commit()
            con.close()
            _DB["path"] = cand
            return cand
        except Exception:
            continue
    _DB["path"] = ":memory:"
    return _DB["path"]


def _db():
    con = sqlite3.connect(_db_path(), timeout=5)
    con.row_factory = sqlite3.Row
    try:
        con.executescript(DB_SCHEMA)
    except Exception:
        pass
    return con


def _load_events(newest_first=True, limit=DB_KEEP):
    try:
        with _DB_LOCK:
            con = _db()
            try:
                sql = "SELECT * FROM events ORDER BY id %s LIMIT ?" % ("DESC" if newest_first else "ASC")
                rows = con.execute(sql, (limit,)).fetchall()
            finally:
                con.close()
    except Exception:
        return []
    out = []
    for r in rows:
        try:
            carriers = json.loads(r["carriers"] or "[]")
        except Exception:
            carriers = []
        out.append({"id": "L%04d" % r["id"], "anon": r["anon"], "type": r["type"],
                    "level": r["level"], "at": r["ts"], "victim_state": r["victim_state"],
                    "action": r["action"], "status": "pending", "timeline": [],
                    "carriers": carriers, "mode": r["mode"]})
    return out


def clear_events():
    """清空真实数据（测试者用）。返回删除条数。"""
    with _DB_LOCK:
        con = _db()
        try:
            n = con.execute("SELECT COUNT(*) FROM events").fetchone()[0]
            con.execute("DELETE FROM events")
            con.commit()
            return n
        finally:
            con.close()


def set_root(path):
    """打包成 exe 后静态资源在临时解压目录，需要重设根目录。"""
    global ROOT
    ROOT = path


def _sample_scenario(payload):
    """样例模式下按关键词挑一个更像的样例"""
    t = (payload.get("text") or "")
    if any(k in t for k in ("垫付", "刷单", "返利", "三单")):
        return "scam"
    return "suspicious"


def _post_json(path, key, payload):
    req = urllib.request.Request(
        BASE + path,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Authorization": "Bearer " + key, "Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
        return json.loads(r.read().decode("utf-8"))


def _upload(image_bytes, filename="shot.jpg"):
    b = "----CG" + uuid.uuid4().hex
    parts = []
    parts.append(("--%s\r\nContent-Disposition: form-data; name=\"file\"; filename=\"%s\"\r\n"
                  "Content-Type: image/jpeg\r\n\r\n" % (b, filename)).encode("utf-8"))
    parts.append(image_bytes)
    parts.append(("\r\n--%s\r\nContent-Disposition: form-data; name=\"user\"\r\n\r\nu_web\r\n--%s--\r\n" % (b, b)).encode("utf-8"))
    body = b"".join(parts)
    req = urllib.request.Request(
        BASE + "/v1/files/upload", data=body,
        headers={"Authorization": "Bearer " + OCR_KEY,
                 "Content-Type": "multipart/form-data; boundary=" + b},
        method="POST")
    with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
        return json.loads(r.read().decode("utf-8"))


def _strip_fence(s):
    s = (s or "").strip()
    if s.startswith("```"):
        s = s[3:]
        if s[:4].lower() == "json":
            s = s[4:]
        s = s.lstrip("\n")
    if s.endswith("```"):
        s = s[:-3]
    return s.strip()


def _json_in(s):
    a, b = s.find("["), s.rfind("]")
    if 0 <= a < b:
        try:
            return json.loads(s[a:b + 1])
        except Exception:
            pass
    a, b = s.find("{"), s.rfind("}")
    if 0 <= a < b:
        try:
            return json.loads(s[a:b + 1])
        except Exception:
            pass
    return None


def analyze(payload):
    # 样例模式：由控制面板显式开启（断网/额度不足时用），返回预置样例并**明确标注**
    if SAMPLE_MODE or payload.get("demo"):
        import mock_data
        out = mock_data.get(payload.get("scenario") or _sample_scenario(payload))
        out.setdefault("meta", {})["sample"] = True
        out["meta"].pop("demo", None)
        return out

    t0 = time.time()
    mode = payload.get("mode", "text")
    transcript, rules = None, None

    if mode == "image":
        b64 = payload.get("image_base64") or ""
        if not b64:
            return {"ok": False, "error": "没有收到图片"}
        raw = base64.b64decode(b64)
        up = _upload(raw)
        if not up.get("id"):
            return {"ok": False, "error": "图片上传失败"}
        o1 = _post_json("/v1/chat-messages", OCR_KEY, {
            "inputs": {}, "query": "把这张聊天截图逐条转录成 JSON，只输出 JSON",
            "response_mode": "blocking", "user": "u_web",
            "files": [{"type": "image", "transfer_method": "local_file",
                       "upload_file_id": up["id"]}],
        })
        ocr_text = _strip_fence(o1.get("answer", ""))
        parsed = _json_in(ocr_text)
        if isinstance(parsed, dict) and parsed.get("error"):
            return {"ok": False, "error": "识别失败：" + str(parsed.get("error"))}
        if not isinstance(parsed, list):
            return {"ok": False, "error": "没能从截图里认出对话，换一张更清晰的试试"}
        transcript = {"count": len(parsed), "messages": parsed}
        chat_text = ocr_text
    else:
        chat_text = (payload.get("text") or "").strip()
        if len(chat_text) < 10:
            return {"ok": False, "error": "内容太短了，至少贴几句对话"}

    o2 = _post_json("/v1/chat-messages", WF_KEY, {
        "inputs": {"chat_text": chat_text}, "query": "分析这段对话",
        "response_mode": "blocking", "user": "u_web",
    })
    judge = _json_in(_strip_fence(o2.get("answer", "")))
    if not isinstance(judge, dict) or "verdict" not in judge:
        return {"ok": False, "error": "研判结果解析失败", "raw": (o2.get("answer") or "")[:300]}

    return {"ok": True, "transcript": transcript, "rules": rules,
            "judgment": judge, "meta": {"secs": round(time.time() - t0, 1)}}


def _record_event(out, payload):
    """分析成功后写一条匿名事件（只有脱敏字段，不含聊天原文）"""
    j = out.get("judgment") or {}
    if not j:
        return
    hits = (out.get("rules") or {}).get("hits") or []
    hs = j.get("hypotheses") or []
    etype = hits[0] if hits else (hs[0].get("name") if hs else (j.get("verdict") or "未分类"))
    try:
        with _DB_LOCK:
            con = _db()
            try:
                con.execute(
                    "INSERT INTO events(ts,anon,type,level,victim_state,action,mode,carriers)"
                    " VALUES(?,?,?,?,?,?,?,?)",
                    (time.strftime("%m-%d %H:%M"),
                     "S-%04X" % (abs(hash(str(time.time()))) % 0xFFFF),
                     etype, j.get("level") or "low",
                     j.get("victim_state") or "none",
                     (j.get("what_to_do") or ["建议人工复核"])[0],
                     payload.get("mode"),
                     json.dumps(out.get("carriers") or [], ensure_ascii=False)))
                con.commit()
                con.execute("DELETE FROM events WHERE id NOT IN "
                            "(SELECT id FROM events ORDER BY id DESC LIMIT %d)" % DB_KEEP)
                con.commit()
            finally:
                con.close()
    except Exception:
        pass


def _live_b():
    evs = _load_events(newest_first=True)
    high = [e for e in evs if e["level"] in ("high", "critical")]
    return {
        "ok": True, "source": "live",
        "school": "某大学 · 学生工作处",
        "stats": {"week_total": len(evs), "pending": sum(1 for e in evs if e["status"] == "pending"),
                  "high": len(high), "students": len({e["anon"] for e in evs}), "delta": "—"},
        "events": evs,
    }


def _live_g(view):
    evs = _load_events(newest_first=False, limit=DB_KEEP)
    from collections import Counter
    types = Counter(e["type"] for e in evs)
    carriers = {}
    for e in evs:
        for c in e.get("carriers") or []:
            v = c.get("value")
            if v:
                carriers[v] = carriers.get(v, 0) + 1
    out = {"ok": True, "source": "live", "view": view, "updated": time.strftime("%Y-%m-%d %H:%M"),
           "role": {"title": {"telecom": "运营商 · 涉诈载体线索", "police": "反诈中心 · 态势与线索",
                              "edu": "教育主管 · 高校反诈态势"}.get(view, "数据视图"),
                    "sub": "数据来自本机实际分析记录（不含聊天原文）",
                    "visible": ["载体值", "类型", "被报告次数"], "hidden": ["当事人身份", "聊天原文"]}}
    if view == "telecom":
        out["carriers"] = [{"v": k, "t": "链接/号码", "n": n, "first": "—", "last": "—",
                            "forge": "—", "note": "来自实际分析"} for k, n in
                           sorted(carriers.items(), key=lambda x: -x[1])[:20]]
    elif view == "police":
        out["types"] = [{"type": k, "count": n, "delta": "—"} for k, n in types.most_common(8)]
        out["variants"] = [{"name": k, "type": "实际命中", "seen": n} for k, n in types.most_common(5)]
        out["carriers"] = [{"v": k, "t": "链接/号码", "n": n, "first": "—", "last": "—",
                            "forge": "—", "note": ""} for k, n in sorted(carriers.items(), key=lambda x: -x[1])[:4]]
    else:
        out["schools"] = [{"name": "某大学", "n": len(evs), "warn": sum(1 for e in evs if e["level"] in ("high", "critical")),
                           "done": 0, "rate": "—"}]
        out["quarter"] = [{"m": "本月", "n": len(evs)}]
    return out


class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *a, **kw):
        super().__init__(*a, directory=ROOT, **kw)

    def end_headers(self):
        # 允许被任意来源（含 https 平台页）读取静态文件，便于把资料推到平台
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Cache-Control", "no-store, no-cache, must-revalidate")
        self.send_header("Access-Control-Allow-Private-Network", "true")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "*")
        super().end_headers()

    def do_OPTIONS(self):
        self.send_response(204)
        self.end_headers()

    def log_message(self, fmt, *args):
        # 注意：--noconsole 打包后 sys.stderr 为 None，
        # 而 send_response() 会调用本方法；不判空会导致每个请求都抛异常、
        # 连接被直接关闭（浏览器表现为 ERR_EMPTY_RESPONSE）。
        try:
            if sys.stderr:
                sys.stderr.write("%s - %s\n" % (self.address_string(), fmt % args))
        except Exception:
            pass

    def _send(self, code, obj=None, raw=None, ctype="application/json; charset=utf-8"):
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        if raw is not None:
            self.wfile.write(raw)
        elif obj is not None:
            self.wfile.write(json.dumps(obj, ensure_ascii=False).encode("utf-8"))

    def _want_live(self):
        return "source=live" in (self.path or "")

    def do_POST(self):
        if self.path.split("?")[0] != "/api/analyze":
            return self._send(404, {"ok": False, "error": "not found"})
        try:
            n = int(self.headers.get("Content-Length") or 0)
            payload = json.loads(self.rfile.read(n).decode("utf-8"))
            out = analyze(payload)
            try:
                if out.get("ok") and not out.get("meta", {}).get("sample"):
                    _record_event(out, payload)
            except Exception:
                pass
            self._send(200 if out.get("ok") else 400, out)
        except urllib.error.HTTPError as e:
            body = e.read().decode("utf-8", "ignore")[:300]
            self._send(502, {"ok": False, "error": "平台返回 %s" % e.code, "detail": body})
        except Exception as e:
            self._send(500, {"ok": False, "error": "%s: %s" % (type(e).__name__, e)})

    def do_GET(self):
        p = self.path.split("?")[0]
        if p == "/api/health":
            return self._send(200, {"ok": True, "ocr_key": bool(OCR_KEY), "wf_key": bool(WF_KEY)})
        if p == "/api/scenarios":
            try:
                import mock_data
                return self._send(200, {"ok": True, "scenarios": list(mock_data.SCENARIOS.keys())})
            except Exception as e:
                return self._send(200, {"ok": False, "error": str(e)})
        # ---- B 端（学校工作台）----
        # 只返回事件与统计，不含任何聊天原文；学生以匿名 ID 表示
        if p == "/api/b/events":
            try:
                if self._want_live():
                    return self._send(200, _live_b())
                import mock_data
                return self._send(200, mock_data.get_b_events())
            except Exception as e:
                return self._send(200, {"ok": False, "error": str(e)})
        if p == "/api/b/reset":
            if "confirm=1" not in (self.path or ""):
                return self._send(400, {"ok": False, "error": "需要 confirm=1"})
            try:
                n = clear_events()
                return self._send(200, {"ok": True, "cleared": n})
            except Exception as e:
                return self._send(500, {"ok": False, "error": str(e)})
        if p == "/api/b/weekly":
            try:
                if self._want_live():
                    return self._send(200, {"ok": True, "school": "某大学 · 学生工作处", "weekly": {
                        "range": "本月", "top_scripts": [], "by_type": [], "done": {}}})
                import mock_data
                return self._send(200, mock_data.get_b_weekly())
            except Exception as e:
                return self._send(200, {"ok": False, "error": str(e)})
        # ---- G 端（执法/运营商/监管）：只读，按 view 裁字段 ----
        if p == "/api/g/report":
            try:
                import urllib.parse as _up
                q = _up.parse_qs(self.path.split("?", 1)[1] if "?" in self.path else "")
                view = (q.get("view") or ["telecom"])[0]
                if self._want_live():
                    return self._send(200, _live_g(view))
                import mock_data
                return self._send(200, mock_data.get_g(view))
            except Exception as e:
                return self._send(200, {"ok": False, "error": str(e)})
        return super().do_GET()



def _port_free(p):
    """端口是否空闲：能连上说明已被占用。比 bind 更可靠（Windows 上 bind 会成功）。"""
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(0.25)
    try:
        s.connect(("127.0.0.1", p))
        return False
    except OSError:
        return True
    finally:
        s.close()


def start_server(host="127.0.0.1", start_port=None):
    """启动服务并返回 (httpd, port, url)。供命令行与 GUI 控制面板共用。"""
    sp = start_port or PORT
    for p in range(sp, sp + 30):
        if not _port_free(p):
            continue
        try:
            httpd = SERVER_CLASS((host, p), Handler)
            return httpd, p, "http://%s:%d/" % (host, p)
        except OSError:
            continue
    raise RuntimeError("端口 %d-%d 都被占用" % (sp, sp + 29))


def serve(open_browser=False):
    httpd, port, url = start_server()
    print("=" * 56)
    print("  ChatGuard 已启动")
    print("=" * 56)
    print("  演示入口（推荐从这里开始）: %sdemo.html" % url)
    print("  学生端                    : %s" % url)
    print("  校园端（区域管理员）        : %sadmin.html" % url)
    print("  数据视图（运营商/监管）     : %sreport.html?view=telecom" % url)
    print("-" * 56)
    print("  样例模式：%s" % ("开" if SAMPLE_MODE else "关"))
    print("  关闭这个窗口即可停止服务  (Ctrl+C)")
    print("=" * 56)
    sys.stdout.flush()
    if open_browser:
        threading.Timer(1.2, lambda: webbrowser.open(url + "demo.html")).start()
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\n已停止。")


if __name__ == "__main__":
    SAMPLE_MODE = "--sample" in sys.argv
    serve(open_browser="--open" in sys.argv)
