# 远程命令通道协议（aitools 项目）

## 目的
让手机/任意设备通过 GitHub 远程驱动电脑端 AI 执行项目任务：手机发令 -> 电脑执行 -> 结果回传。

## 原理
1. 手机在 GitHub 编辑 00-in/00-brief/COMMAND.md，新增一条 [PENDING] 命令。
2. 电脑端 WorkBuddy 自动化每小时间隔触发：git pull -> 读 COMMAND.md -> 找 [PENDING] -> 执行 -> 写结果 -> 改 [DONE] -> git push。
3. 手机刷新 GitHub 查看结果与产物（02-out/02-docs/RESULT-<id>.md）。

## 命令格式
## CMD-<日期>-<序号> [PENDING]
<一句明确指令>

状态：[PENDING] 待执行 / [RUNNING] 执行中 / [DONE] 已完成 / [SKIP] 跳过(附原因)

## 约束
- 电脑需开机且 WorkBuddy 运行，自动化才触发（最小粒度每小时一次）。
- 只执行与本项目相关的明确指令；含糊或高风险会被 [SKIP]。
- 结果写入 02-out/02-docs/RESULT-<id>.md。
