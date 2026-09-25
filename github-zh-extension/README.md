# GitHub 界面中文助手

这是一个独立的 Chrome / Edge 扩展，作用范围仅为 `https://github.com/*`。它把常用菜单、按钮、表单提示翻译成简体中文，并默认保留 `Issues`、`Pull requests`、`Actions`、`Copilot` 和 `README` 等界面项。译文中也保留 Git、PR、issue、commit、branch、merge、fork 等专业词。点击扩展图标可开关翻译、增减需要保持英文的完整界面项。

## 安装

1. 在 Chrome 地址栏打开 `chrome://extensions`；Edge 打开 `edge://extensions`。
2. 开启“开发者模式”。
3. 点击“加载已解压的扩展程序”，选择本目录 `github-zh-extension`。
4. 刷新已打开的 GitHub 页面。

安装后扩展会在浏览器中保持启用；修改本目录的代码后，需要在扩展管理页面点“重新加载”。

## 范围与隐私

- 只翻译内置词库匹配的界面文字，不自动翻译 README、代码、issue 正文或评论。因此 GitHub 更新界面后，少数新文字可能仍为英文。
- 只申请浏览器的 `storage` 权限，用于在本机保存开关和保留英文的列表；没有远程接口、账号权限或网络请求。
- 扩展属于浏览器设置，不会修改 GitHub 账号语言，也不会影响其他电脑上的 GitHub。
