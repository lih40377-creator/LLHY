# 把知页部署为公开网站（PythonAnywhere）

此方案使用 PythonAnywhere 的免费 Beginner 账号。网站有公开的 HTTPS 地址；访客可注册账号，登录后保存自己的笔记。线上数据库和上传文件保存在 PythonAnywhere 的磁盘中，与电脑上的 `instance/` 分开。**不要把本机的数据库、密钥或附件提交到 GitHub。**

免费账号目前提供 1 个网站和 512 MiB 磁盘空间。网站每月需要在 PythonAnywhere 的 **Web** 页面手动续期，否则网址会暂时停止服务。请定期下载自己的笔记备份。

## 1. 注册账号

打开 [Beginner 免费账号注册页](https://www.pythonanywhere.com/registration/register/beginner/)，填写用户名、邮箱和密码，完成邮箱验证。请保管密码，不要把它发给协助部署的人。

下面把你的 PythonAnywhere 用户名写作 `YOURNAME`。实际输入命令时将它换成自己的用户名。

## 2. 从 GitHub 下载项目

登录 PythonAnywhere，打开顶部 **Consoles（控制台）**，点击 **Bash**。在命令行依次运行：

```bash
git clone https://github.com/lih40377-creator/LLHY.git
cd LLHY
python3.11 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
```

如果平台不提供 `python3.11`，在 **Web** 中选择可用的 Python 3.10 或更新版本，并在命令中使用相同版本。安装完成后可运行 `python -c 'from wsgi import application; print(application.name)'`，看到 `app` 即表示入口可以加载。

## 3. 创建网站

打开顶部 **Web（网站）**，点击 **Add a new web app（新增网站）**。域名选择 `YOURNAME.pythonanywhere.com`，框架选择 **Manual configuration（手动配置）**，再选与虚拟环境相同的 Python 版本。

在网站配置页填写：

- **Source code（源代码目录）**：`/home/YOURNAME/LLHY`
- **Working directory（工作目录）**：`/home/YOURNAME/LLHY`
- **Virtualenv（虚拟环境）**：`/home/YOURNAME/LLHY/.venv`

点击页面中的 **WSGI configuration file（WSGI 配置文件）**，清空原有示例代码，填入下列内容，替换用户名后保存：

```python
import os
import sys

os.environ["PUBLIC_HTTPS"] = "1"
project = "/home/YOURNAME/LLHY"
if project not in sys.path:
    sys.path.insert(0, project)

from wsgi import application
```

项目会在首次启动时自动生成 `instance/notes.db` 和 `instance/secret_key`，附件保存在 `instance/uploads/`。这些文件不会上传到 GitHub。请不要删除线上 `instance/` 目录。

可在 **Static files（静态文件）** 添加 URL `/static/`，对应目录 `/home/YOURNAME/LLHY/static/`。这能让网页样式和脚本由平台直接提供。

点击 **Reload（重新加载）**。打开 `https://YOURNAME.pythonanywhere.com/healthz`，看到 `{"status":"ok"}` 即表示网站和数据库已启动。再打开网站首页，注册一个新账号并登录。

## 4. 日常维护

- **更新代码**：在 Bash 控制台运行 `cd ~/LLHY && git pull`，然后到 **Web** 点击 **Reload**。
- **网站续期**：留意 PythonAnywhere 的通知，每月到 **Web** 页面续期免费网站。续期不会更改数据库。
- **备份**：登录网站，在“备份与导出”下载 ZIP，妥善保存。每个普通用户只能导出自己的笔记。
- **错误排查**：在 **Web** 页面查看 **Error log（错误日志）**；先确认虚拟环境路径、WSGI 文件与 Python 版本一致。

免费账号的容量和续期规则可能变化。以 [PythonAnywhere 的免费账号说明](https://help.pythonanywhere.com/pages/FreeAccountsFeatures) 为准。
