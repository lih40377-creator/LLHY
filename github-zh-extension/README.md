# GitHub 界面中文助手

这是一个独立的 Chrome / Edge 扩展，作用范围仅为 `https://github.com/*`。它把常用菜单、按钮、表单提示翻译成简体中文。`Issues`、`Pull requests`、`Actions` 等默认显示中英对照；Git、PR、issue、commit、branch、merge、fork 等专业词保留英文。点击扩展图标可开关翻译、调整需要中英对照的完整界面项。Marketplace 的分类、常见标签和部分推荐卡片说明也支持中文。

## 安装

1. 在 Chrome 地址栏打开 `chrome://extensions`；Edge 打开 `edge://extensions`。
2. 开启“开发者模式”。
3. 点击“加载已解压的扩展程序”，选择本目录 `github-zh-extension`。
4. 刷新已打开的 GitHub 页面。

安装后扩展会在浏览器中保持启用。**如果旧版是从 ZIP 解压到别的文件夹安装的，更新仓库源码不会自动更新那个文件夹。** 请解压新版 ZIP，先从扩展管理页面移除旧版，再用“加载已解压的扩展程序”选择新版 `github-zh-extension` 文件夹，最后刷新 GitHub 页面。可在扩展详情中检查版本应为 `1.2.0`。以后若直接修改了已安装文件夹里的代码，才可用“重新加载”更新。

## 范围与隐私

- 只翻译内置词库匹配的界面文字，不自动翻译 README、代码、issue 正文或评论。Marketplace 的动态商品说明可能仍为英文；浏览器自带的“翻译成中文”可作为补充。
- 只申请浏览器的 `storage` 权限，用于在本机保存开关和保留英文的列表；没有远程接口、账号权限或网络请求。
- 扩展属于浏览器设置，不会修改 GitHub 账号语言，也不会影响其他电脑上的 GitHub。
