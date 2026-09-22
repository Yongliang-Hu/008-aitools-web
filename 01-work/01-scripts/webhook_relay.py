# webhook_relay.py
# 008-aitools-web 远程执行中继（局域网 webhook，零依赖）
#
# 作用：手机 POST 命令 -> 桌面常驻服务 -> git pull -> 执行 -> commit -> push
# 把「每小时轮询」升级为「秒级事件触发」，不依赖 WorkBuddy 会话在线。
#
# 运行（桌面终端，需保持开机 + 此进程常驻）：
#   cd "D:\AI program\workbuddy dic\008-aitools-web\01-work\01-scripts"
#   python webhook_relay.py
#
# 安全：必须修改下方 TOKEN；服务仅监听局域网，请勿暴露到公网（除非套隧道+token）。

import http.server
import json
import os
import subprocess
import threading
import urllib.parse
from datetime import datetime

# ============ 配置（使用前请改 TOKEN）============
PORT = 8765
TOKEN = "hutouhunao"   # ← 改成你自己的强 token！不要用默认值
PROJECT_DIR = r"D:\AI program\workbuddy dic\008-aitools-web"
SCRIPTS_DIR = os.path.join(PROJECT_DIR, "01-work", "01-scripts")
COMMAND_FILE = os.path.join(PROJECT_DIR, "00-in", "00-brief", "COMMAND.md")
# =================================================

_lock = threading.Lock()

# 手机控制面板（GET / 返回，同源访问，无需跨域）
CONTROL_PANEL_HTML = f"""<!doctype html>
<html lang="zh">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>008 远程控制面板</title>
<style>
  body{{font-family:system-ui,-apple-system,"Microsoft YaHei",sans-serif;max-width:520px;margin:0 auto;padding:18px;background:#f5f6f8;color:#222}}
  h1{{font-size:20px;margin:0 0 4px}} .sub{{color:#888;font-size:13px;margin-bottom:18px}}
  label{{display:block;font-size:13px;margin:12px 0 4px;font-weight:600}}
  input,textarea,select{{width:100%;box-sizing:border-box;padding:11px;font-size:15px;border:1px solid #ccd;border-radius:9px;background:#fff}}
  textarea{{min-height:84px;resize:vertical}}
  button{{width:100%;padding:14px;font-size:16px;font-weight:700;color:#fff;background:#2b7de9;border:none;border-radius:11px;margin-top:18px}}
  button:active{{background:#1c63c0}}
  #out{{margin-top:16px;padding:12px;background:#111;color:#0f0;font-family:monospace;font-size:12px;border-radius:9px;min-height:40px;white-space:pre-wrap;word-break:break-all}}
</style>
</head>
<body>
  <h1>008 远程控制面板</h1>
  <div class="sub">局域网触发 · 服务端口 {PORT}</div>
  <form method="POST" action="/run">
    <label>Token</label>
    <input name="token" value="{TOKEN}">
    <label>动作</label>
    <select name="action">
      <option value="append">append · 追加一行到文件</option>
      <option value="command">command · 写 COMMAND.md（异步）</option>
      <option value="sync">sync · 仅 git 提交推送</option>
    </select>
    <label>目标文件（append 用，相对项目根）</label>
    <input name="file" value="README.md">
    <label>内容 / 命令文本</label>
    <textarea name="text" placeholder="例如：手机 webhook 测试 2026-09-22"></textarea>
    <button type="submit">发送执行</button>
  </form>
</body>
</html>"""

# 表单提交后的结果页（前后包住 JSON 结果）
RESULT_HTML_PREFIX = """<!doctype html><html lang="zh"><head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>执行结果</title>
<style>body{{font-family:system-ui,sans-serif;max-width:520px;margin:0 auto;padding:18px;background:#f5f6f8}}
pre{{background:#111;color:#0f0;padding:12px;border-radius:9px;font-size:12px;white-space:pre-wrap;word-break:break-all}}
a{{display:inline-block;margin-top:14px;color:#2b7de9}}</style></head><body>
<h1>执行结果</h1><pre>"""
RESULT_HTML_SUFFIX = """</pre><a href="/">&#8592; 返回控制面板</a> <a href="/status">查看执行状态</a></body></html>"""


def git(*args):
    try:
        r = subprocess.run(
            ["git", "-C", PROJECT_DIR, *args],
            capture_output=True, text=True, timeout=120,
        )
        return r.returncode == 0, (r.stdout + r.stderr).strip()
    except Exception as e:  # noqa: BLE001
        return False, str(e)


def do_pull():
    git("pull", "origin", "master")


def do_commit_push(msg):
    git("add", "-A")
    ok, _ = git("diff", "--cached", "--quiet")
    if not ok:  # 有改动才提交（diff --cached --quiet 非0=有差异）
        git("commit", "-m", msg)
    return git("push", "origin", "master")


def _safe_project_path(rel_file):
    """把相对路径解析为项目内绝对路径，防止越权写项目外文件。"""
    p = os.path.normpath(os.path.join(PROJECT_DIR, rel_file))
    if not p.startswith(os.path.normpath(PROJECT_DIR)):
        return None
    return p


def append_text(rel_file, text):
    p = _safe_project_path(rel_file)
    if not p:
        return False, "path outside project"
    with open(p, "a", encoding="utf-8") as f:
        f.write("\n" + text + "\n")
    return True, p


def run_script(name):
    p = os.path.normpath(os.path.join(SCRIPTS_DIR, name))
    if not p.startswith(os.path.normpath(SCRIPTS_DIR)):
        return False, "script not in allowed dir"
    if not os.path.exists(p):
        return False, "script not found"
    r = subprocess.run(
        ["powershell", "-ExecutionPolicy", "Bypass", "-File", p],
        capture_output=True, text=True, timeout=300,
    )
    return r.returncode == 0, (r.stdout + r.stderr).strip()


def write_command(text):
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    block = f"\n## CMD-WEBHOOK-{stamp} [PENDING]\n{text}\n"
    with open(COMMAND_FILE, "a", encoding="utf-8") as f:
        f.write(block)
    return COMMAND_FILE


# ---- 后台执行 + 状态/日志（避免手机端等待 git 慢操作而卡死）----
LAST = {"status": "idle", "time": None, "detail": None}
LAST_LOCK = threading.Lock()
REL_LOG = os.path.join(os.path.dirname(os.path.abspath(__file__)), "webhook_relay.log")


def log(msg):
    line = f"[{datetime.now().isoformat()}] {msg}"
    print(line, flush=True)
    try:
        with open(REL_LOG, "a", encoding="utf-8") as f:
            f.write(line + "\n")
    except Exception:  # noqa: BLE001
        pass


def worker(action, data):
    try:
        with _lock:  # 串行化 git，避免并发冲突
            log(f"worker start action={action}")
            do_pull()
            log("pull done")
            res = {"action": action, "time": datetime.now().isoformat()}
            if action == "append":
                ok, info = append_text(
                    data.get("file", "README.md"), data.get("text", "")
                )
                git_ok, git_out = (False, "") if not ok else do_commit_push(
                    f"webhook: append to {data.get('file', 'README.md')}"
                )
                res.update({"ok": ok and git_ok, "target": str(info), "git": git_out})
                log(f"append ok={ok} git_ok={git_ok}")
            elif action == "run":
                ok, info = run_script(data.get("script", ""))
                res.update({"script": data.get("script"), "ok": ok, "out": info})
                log(f"run ok={ok}")
            elif action == "sync":
                git_ok, git_out = do_commit_push("webhook: sync")
                res.update({"ok": git_ok, "git": git_out})
                log(f"sync git_ok={git_ok}")
            else:  # command
                info = write_command(data.get("cmd", data.get("text", "")))
                git_ok, git_out = do_commit_push("webhook: new command")
                res.update({"ok": git_ok, "note": "written to COMMAND.md", "git": git_out})
                log(f"command git_ok={git_ok}")
        with LAST_LOCK:
            LAST.clear()
            LAST.update({"status": "done", "time": res.get("time"), "detail": res})
            log("worker done")
    except Exception as e:  # noqa: BLE001
        log(f"worker error {e!r}")
        with LAST_LOCK:
            LAST.clear()
            LAST.update({"status": "error", "time": datetime.now().isoformat(),
                         "detail": {"error": repr(e)}})


class Handler(http.server.BaseHTTPRequestHandler):
    def _send(self, code, obj):
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "POST, GET, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()
        self.wfile.write(json.dumps(obj, ensure_ascii=False).encode("utf-8"))

    def _send_html(self, html):
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(html.encode("utf-8"))

    def do_OPTIONS(self):
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "POST, GET, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_GET(self):
        if self.path == "/":
            self._send_html(CONTROL_PANEL_HTML)
        elif self.path == "/ping":
            self._send(200, {"status": "ok", "time": datetime.now().isoformat()})
        elif self.path == "/status":
            with LAST_LOCK:
                self._send(200, dict(LAST))
        else:
            self._send(404, {"error": "not found"})

    def _respond(self, result, is_form):
        if is_form:
            self._send_html(RESULT_HTML_PREFIX
                            + json.dumps(result, ensure_ascii=False, indent=2)
                            + RESULT_HTML_SUFFIX)
        else:
            self._send(200, result)

    def do_POST(self):
        if self.path != "/run":
            self._send(404, {"error": "not found"})
            return
        try:
            length = int(self.headers.get("Content-Length", 0))
            raw = self.rfile.read(length)
            ctype = self.headers.get("Content-Type", "")
            if "application/x-www-form-urlencoded" in ctype:
                q = urllib.parse.parse_qs(raw.decode("utf-8"))
                data = {k: v[0] for k, v in q.items()}
                is_form = True
            else:
                data = json.loads(raw.decode("utf-8"))
                is_form = False
        except Exception as e:  # noqa: BLE001
            self._send(400, {"error": "bad request: " + str(e)})
            return

        if data.get("token") != TOKEN:
            self._respond({"ok": False, "error": "unauthorized: token 不对"}, is_form)
            return

        # 立即返回「已接收」，真正 git 工作在后台线程跑，避免手机端长时间等待/卡死
        action = data.get("action", "command")
        threading.Thread(target=worker, args=(action, data), daemon=True).start()
        self._respond({
            "ok": True, "accepted": True, "action": action,
            "time": datetime.now().isoformat(),
            "note": "已接收，后台执行中；结果见 /status",
        }, is_form)

    def log_message(self, *args):  # 静默日志
        pass


if __name__ == "__main__":
    srv = http.server.ThreadingHTTPServer(("0.0.0.0", PORT), Handler)
    print(f"[aitools-webhook-relay] listening on 0.0.0.0:{PORT}")
    print(f"[aitools-webhook-relay] project: {PROJECT_DIR}")
    print(f"[aitools-webhook-relay] token set: {'yes' if TOKEN != 'hutouhunao' else 'NO - CHANGE IT'}")
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        print("\n[aitools-webhook-relay] stopped")
