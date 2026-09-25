# 知页 · 笔记工作台

基于 Flask 的个人笔记应用。在原有 `mywebsite` 学习笔记项目上改进，保留已有 SQLite 数据。

## 功能

- 账号注册与登录，旧版明文密码会在首次成功登录时自动升级为哈希
- 笔记创建、编辑、置顶、归档、标签，以及可恢复的回收站
- Markdown 工具栏、实时预览和安全的正文渲染
- 服务端自动保存；新笔记输入后会生成草稿，网络异常时暂存于当前浏览器
- 历史版本预览与恢复：手动保存记录版本，自动保存定期记录快照（每篇最多保留 100 个）
- 图片和 PDF 附件；仅笔记所有者和管理员可访问，单个文件限 5 MB
- 根据标题、内容、标签、日期搜索；桌面和手机均可使用
- 导出完整 ZIP、轻量 JSON、Markdown、TXT、Word 和 PDF；支持 ZIP/JSON 导入
- 管理员查看和管理全站笔记

## 本地运行

需要 Python 3.10 或更新版本。

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python app.py
```

打开 http://127.0.0.1:5000 。首次运行会在 `instance/notes.db` 创建数据库。旧项目已有的 `instance/notes.db` 会原地添加新字段，不删除旧笔记。

生产环境应设置随机 `SECRET_KEY` 环境变量，并使用支持 Python/Flask 的主机运行 `gunicorn app:app`。如需外部数据库，可设置 `DATABASE_URL`。附件默认存储在 `instance/uploads/`，部署时该目录与数据库都需要持久化。GitHub 仓库用于保存代码；GitHub Pages 不能运行 Flask 后端。个人数据库、密钥、附件、虚拟环境和本地笔记文件已列入 `.gitignore`。

## 备份

进入“备份与导出”下载 ZIP 文件，可保存所选笔记、历史版本和附件。回收站里的笔记需要先恢复再导出。JSON 只包含当前笔记文字与标签，不包含历史版本和附件。导入会新增笔记，不覆盖已有内容，重复导入会产生副本。导入文件限 30 MB。不要将备份文件或 `instance/notes.db` 提交到公开仓库。

运行测试：`python -m unittest discover -s tests -v`。

## GitHub 中文界面扩展

`github-zh-extension/` 是可安装到 Chrome / Edge 的本地扩展，只翻译 GitHub 常用界面，并可自定义保留英文的菜单项。安装步骤见该目录的 `README.md`。它不会读取本项目的笔记数据，也不会更改 GitHub 账号设置。

第一次使用 GitHub，可从 [中文新手指南](docs/GitHub-新手指南.md) 开始。指南对照了 Marketplace 截图中常见英文、仓库页面的主要按钮，以及 branch、commit、push、PR 的用法。

## 参考

设计功能时参考了 [HTMLNotes](https://github.com/HTMLToolkit/HTMLNotes) 的导入导出与侧栏组织方式、[Neoma](https://github.com/infinitumio/neoma) 的标签与可迁移数据理念、[Flask 官方教程](https://flask.palletsprojects.com/en/stable/tutorial/) 的基础 Web 应用结构。未复制上述项目代码。
