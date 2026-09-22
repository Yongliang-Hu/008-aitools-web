# aitools Webhook 中继指南（局域网 · 秒级远程执行）

> 目的：把「手机发令 → 电脑执行」从每小时轮询压到**秒级事件触发**。
> 适用：008-aitools-web 项目。服务跑在**桌面电脑**（沙箱不能常驻），用桌面 git 网络（稳定）。
> 前置决策：局域网（同 WiFi） + 简单命令 MVP（零 LLM 依赖）。

## 一、架构

```
手机（curl / 快捷指令 / 语音转文字）
   │  POST http://<电脑局域网IP>:8765/run  {token, action, ...}
   ▼
桌面 webhook_relay.py（Python 零依赖，监听 0.0.0.0:8765）
   ├─ 校验 token
   ├─ git pull
   ├─ 执行 action（append / run / sync / command）
   └─ git commit + push
   ▼
GitHub 008-aitools-web  ← 手机刷新即看结果
```

## 二、桌面部署（一次性）

1. 改 token：编辑 `01-work/01-scripts/webhook_relay.py`，把 `TOKEN = "aitools-webhook-2026"` 改成你自己的强随机串。
2. 启动（保持此窗口/进程常驻，电脑不关机）：
   ```
   cd "D:\AI program\workbuddy dic\008-aitools-web\01-work\01-scripts"
   python webhook_relay.py
   ```
   看到 `listening on 0.0.0.0:8765` 即成功。
3. 查看电脑局域网 IP（手机同 WiFi 时填这个）：
   ```
   ipconfig
   ```
   找「IPv4 地址」，形如 `192.168.1.xx`。
4. 本机自检（桌面另开终端）：
   ```
   curl http://127.0.0.1:8765/
   ```
   应返回 `{"status":"ok",...}`。

## 三、手机触发（三种 action）

所有请求都是 POST JSON 到 `http://<电脑IP>:8765/run`，必须带正确 `token`。

### A. append —— 秒级给某文件末尾加一行（最常用）
```bash
curl -X POST http://192.168.1.xx:8765/run \
  -H "Content-Type: application/json" \
  -d '{"token":"你的token","action":"append","file":"README.md","text":"手机 webhook 测试 2026-09-22"}'
```
返回 `{"ok":true,...}` 即已提交并推送。GitHub 上 README 立刻多出那行。

### B. run —— 运行项目脚本（白名单限 01-work/01-scripts/）
```bash
curl -X POST http://192.168.1.xx:8765/run \
  -H "Content-Type: application/json" \
  -d '{"token":"你的token","action":"run","script":"aitools-sync.ps1"}'
```

### C. sync —— 仅同步（pull + 有改动则 push）
```bash
curl -X POST http://192.168.1.xx:8765/run \
  -H "Content-Type: application/json" \
  -d '{"token":"你的token","action":"sync"}'
```

### D. command —— 自然语言兜底（异步）
把命令写进 `00-in/00-brief/COMMAND.md` 标 `[PENDING]` 并推送，等桌面 WorkBuddy 自动化（每小时）或你手动执行：
```bash
curl -X POST http://192.168.1.xx:8765/run \
  -H "Content-Type: application/json" \
  -d '{"token":"你的token","action":"command","cmd":"在首页加一个价格对比卡片区"}'
```

## 四、iOS / Android 快捷指令（语音入口）

用手机「快捷指令」App 做一个「按住说话 → 转文字 → POST」：
1. 新建快捷指令：添加「听写文本」→ 变量 `文本`。
2. 添加「获取 URL 内容」：
   - URL：`http://192.168.1.xx:8765/run`
   - 方法：POST
   - 请求体（JSON）：`{"token":"你的token","action":"command","cmd":"<听写文本>"}`
3. 保存。以后说一句话，电脑就收到命令。

（MVP 阶段 command 走异步；若想让语音命令也秒级执行，后续接入 LLM 解析后改走 append/run。）

## 五、安全须知

- **必须改 TOKEN**：默认值任何人都能猜到，局域网内可让电脑跑命令。
- **仅局域网**：服务监听 `0.0.0.0`，但请勿把 8765 端口映射到公网。需公网访问时套 Cloudflare Tunnel / ngrok 并保留 token。
- **append 越权防护**：脚本已限制只能写项目目录内文件。
- **run 白名单**：只允许运行 `01-work/01-scripts/` 下的脚本，不执行任意 shell。

## 六、与现有通道的关系

| 通道 | 延迟 | 执行者 | 适合 |
|------|------|--------|------|
| GitHub COMMAND.md | ≤1h（轮询） | 桌面 WorkBuddy 自动化 | 复杂、可文字描述 |
| Agent Mail | 即时/≤1h | 桌面会话 或 自动化 | 语音、随手一句 |
| **Webhook 中继** | **秒级** | **桌面常驻脚本** | **确定动作（加文本/跑脚本/同步）** |

三者并存，按场景选。Webhook 解决「我不在 WorkBuddy 会话旁、又要秒级让电脑改项目」这一段。
