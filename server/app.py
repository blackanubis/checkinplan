#!/usr/bin/env python3
"""checkinplan 单容器服务：静态页面 + 极简状态同步 API（SQLite）。

只用 Python 标准库（http.server + sqlite3 + json），镜像里不用装任何包。
  GET  /api/state   -> {"ok":true,"ts":<毫秒>,"data":{key:value}}
  POST /api/state   -> 传入 {"ts":..., "data":{...}}，按 key 覆盖保存
  其它路径          -> 当作静态文件，从 CP_WWW 目录返回
"""
import json
import os
import sqlite3
import sys
import time
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse

WWW = os.environ.get("CP_WWW", "/app/html")
DATA = os.environ.get("CP_DATA", "/data")
PORT = int(os.environ.get("CP_PORT", "80"))
DB_PATH = os.path.join(DATA, "state.db")
SCHEMA = "CREATE TABLE IF NOT EXISTS kv (k TEXT PRIMARY KEY, v TEXT NOT NULL, ts REAL NOT NULL)"


def conn():
    os.makedirs(DATA, exist_ok=True)
    c = sqlite3.connect(DB_PATH, timeout=10)
    c.execute(SCHEMA)
    return c


def read_all():
    c = conn()
    try:
        rows = c.execute("SELECT k, v, ts FROM kv").fetchall()
    finally:
        c.close()
    data = {k: v for k, v, _ in rows}
    ts = max([t for _, _, t in rows], default=0)
    return {"ok": True, "ts": ts, "data": data}


def write_all(payload):
    ts = float(payload.get("ts") or (time.time() * 1000))
    data = payload.get("data") or {}
    c = conn()
    try:
        for k, v in data.items():
            if not isinstance(k, str) or not isinstance(v, str):
                continue
            c.execute(
                "INSERT INTO kv(k,v,ts) VALUES(?,?,?) "
                "ON CONFLICT(k) DO UPDATE SET v=excluded.v, ts=excluded.ts",
                (k, v, ts),
            )
        c.commit()
    finally:
        c.close()
    return {"ok": True, "ts": ts}


class Handler(SimpleHTTPRequestHandler):
    server_version = "checkinplan/1.0"

    def __init__(self, *a, **kw):
        super().__init__(*a, directory=WWW, **kw)

    # 让 .html 带上 charset，中文页面不会乱码
    def guess_type(self, path):
        t = super().guess_type(path)
        if t == "text/html":
            return "text/html; charset=utf-8"
        return t

    # 页面一律不缓存，改了页面刷新就是新的
    def end_headers(self):
        self.send_header("Cache-Control", "no-store, no-cache, must-revalidate")
        super().end_headers()

    def _json(self, obj, code=200):
        body = json.dumps(obj, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        if self.command != "HEAD":
            self.wfile.write(body)

    def _read_body(self):
        n = int(self.headers.get("Content-Length") or 0)
        if n <= 0:
            return {}
        try:
            return json.loads(self.rfile.read(n).decode("utf-8"))
        except Exception:
            return {}

    def _api(self):
        p = urlparse(self.path).path.rstrip("/")
        if p != "/api/state":
            return False
        try:
            if self.command == "GET":
                self._json(read_all())
            elif self.command == "POST":
                self._json(write_all(self._read_body()))
            else:
                self._json({"ok": False, "error": "method not allowed"}, 405)
        except Exception as e:  # 不让单个请求把服务打挂
            self._json({"ok": False, "error": str(e)}, 500)
        return True

    def do_GET(self):
        if not self._api():
            super().do_GET()

    def do_HEAD(self):
        if not self._api():
            super().do_HEAD()

    def do_POST(self):
        if not self._api():
            self._json({"ok": False, "error": "not found"}, 404)

    def log_message(self, fmt, *args):
        sys.stderr.write("%s - %s\n" % (self.log_date_time_string(), fmt % args))


def main():
    os.makedirs(DATA, exist_ok=True)
    srv = ThreadingHTTPServer(("0.0.0.0", PORT), Handler)
    print("checkinplan: www=%s port=%s data=%s" % (WWW, PORT, DB_PATH), flush=True)
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
