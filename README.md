# 知页 · 笔记工作台

基于 Flask 的个人笔记应用。在原有 `mywebsite` 学习笔记项目上改进，保留已有 SQLite 数据。

## 功能

- 账号注册与登录，旧版明文密码会在首次成功登录时自动升级为哈希
- 笔记创建、编辑、删除、置顶、归档和标签
- 根据标题、内容、标签、日期搜索；桌面和手机均可使用
- 编辑时在当前浏览器暂存草稿，保存仍需点击“保存笔记”
- 导出 JSON、Markdown、TXT、Word 和 PDF；从 JSON 备份导入
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

生产环境应设置随机 `SECRET_KEY` 环境变量，并使用支持 Python/Flask 的主机运行 `gunicorn app:app`。如需外部数据库，可设置 `DATABASE_URL`。GitHub 仓库用于保存代码；GitHub Pages 不能运行 Flask 后端。个人数据库、密钥、虚拟环境和本地笔记文件已列入 `.gitignore`。

## 备份

进入“备份与导出”下载 JSON 文件。导入会新增笔记，不覆盖已有内容，重复导入会产生副本。不要将备份文件或 `instance/notes.db` 提交到公开仓库。

## 参考

设计功能时参考了 [HTMLNotes](https://github.com/HTMLToolkit/HTMLNotes) 的导入导出与侧栏组织方式、[Neoma](https://github.com/infinitumio/neoma) 的标签与可迁移数据理念、[Flask 官方教程](https://flask.palletsprojects.com/en/stable/tutorial/) 的基础 Web 应用结构。未复制上述项目代码。
