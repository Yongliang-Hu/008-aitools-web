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
from datetime import datetime

# ============ 配置（使用前请改 TOKEN）============
PORT = 8765
TOKEN = "hutouhunao"   # ← 改成你自己的强 token！不要用默认值
PROJECT_DIR = r"D:\AI program\workbuddy dic\008-aitools-web"
SCRIPTS_DIR = os.path.join(PROJECT_DIR, "01-work", "01-scripts")
COMMAND_FILE = os.path.join(PROJECT_DIR, "00-in", "00-brief", "COMMAND.md")
# =================================================

_lock = threading.Lock()


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


class Handler(http.server.BaseHTTPRequestHandler):
    def _send(self, code, obj):
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.end_headers()
        self.wfile.write(json.dumps(obj, ensure_ascii=False).encode("utf-8"))

    def do_GET(self):
        if self.path == "/":
            self._send(200, {
                "status": "ok",
                "service": "aitools-webhook-relay",
                "project": "008-aitools-web",
                "time": datetime.now().isoformat(),
            })
        else:
            self._send(404, {"error": "not found"})

    def do_POST(self):
        if self.path != "/run":
            self._send(404, {"error": "not found"})
            return
        try:
            length = int(self.headers.get("Content-Length", 0))
            raw = self.rfile.read(length)
            data = json.loads(raw.decode("utf-8"))
        except Exception as e:  # noqa: BLE001
            self._send(400, {"error": "bad json: " + str(e)})
            return

        if data.get("token") != TOKEN:
            self._send(401, {"error": "unauthorized"})
            return

        action = data.get("action", "command")
        with _lock:
            do_pull()
            result = {"action": action, "time": datetime.now().isoformat()}
            if action == "append":
                ok, info = append_text(
                    data.get("file", "README.md"), data.get("text", "")
                )
                git_ok, git_out = (False, "") if not ok else do_commit_push(
                    f"webhook: append to {data.get('file', 'README.md')}"
                )
                result.update({"ok": ok and git_ok, "target": str(info), "git": git_out})
            elif action == "run":
                ok, info = run_script(data.get("script", ""))
                result.update({"script": data.get("script"), "ok": ok, "out": info})
            elif action == "sync":
                git_ok, git_out = do_commit_push("webhook: sync")
                result.update({"ok": git_ok, "git": git_out})
            else:  # command：异步，写 COMMAND.md 留给自动化/手动
                info = write_command(data.get("cmd", data.get("text", "")))
                ok = bool(info)
                git_ok, git_out = do_commit_push("webhook: new command")
                result.update({
                    "ok": git_ok,
                    "note": "written to COMMAND.md, async exec by automation/manual",
                    "git": git_out,
                })
        self._send(200, result)

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
