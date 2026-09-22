# aitools 三端同步 Playbook（008-aitools-web）

> 目的：电脑(D盘) 云端(GitHub) 手机 一体同步的 AI 开发项目模式。
> 仓库：https://github.com/Yongliang-Hu/008-aitools-web （Private）
> 维护：由 AI 搭档根据 2026-09-22 实操整理。

## 一、前提
- 项目根：D:\AI program\workbuddy dic\008-aitools-web
- GitHub 账号：Yongliang-Hu（仓库必须建在该账号下）
- 分支：master（已与 origin/master 跟踪）
- 本地 git 身份：
  git config user.name "Yongliang-Hu"
  git config user.email "hu_yong_liang@hotmail.com"

## 二、Step 0-2（脚手架+本地仓库，已落地）
由 AI 在沙箱终端建到 D 盘：
- IO 五区：00-in / 01-work / 02-out / 03-archive / 99-tmp（99-tmp 进 .gitignore）
- 空目录放 .gitkeep（Git 不跟踪空目录）
- 补齐 README.md / .gitignore / 01-work/00-src/index.html
- git init -> master -> 首次提交

## 三、Step 3（GitHub 推送，已成功）
1. 浏览器建空仓：New repository -> 008-aitools-web -> Private -> 不要勾 README。
2. 关联远端（已存在用 set-url，不要用 add）：
   git remote set-url origin https://github.com/Yongliang-Hu/008-aitools-web.git
3. 推送：git push -u origin master（首次弹浏览器登录，登后缓存）

## 四、踩过的坑
1. Vim 卡住：git commit 不带 -m 进 Vim，退出=Esc 后输入 :wq 回车。
2. remote add 报 already exists：改用 git remote set-url。
3. 仓库名拼错：web 曾拼成 wet，URL 必须精确。
4. Connection was reset：网络掐断 github.com。浏览器能开但 git 推不动->配代理：
   git config --global http.proxy http://127.0.0.1:7890
   git config --global https.proxy http://127.0.0.1:7890
5. Repository not found：远端仓库不存在/建错账号或名字，先去仓库列表确认。
6. 用户名占位：URL 里的 Yongliang-Hu 必须是真实账号。

## 五、日常同步（自动化）
- 脚本：01-work/01-scripts/aitools-sync.ps1
  检测改动->自动 commit（带时间戳）-> push；无改动只 push。
- AI 搭档下次完成改动后可直接运行该脚本推送，无需手敲。
- 手机验证：GitHub App 登录 Yongliang-Hu -> 看 008-aitools-web -> 改文件 push -> 电脑 git pull。

## 六、常用命令
git status / git add -A / git commit -m "信息" / git push / git pull / git remote -v
