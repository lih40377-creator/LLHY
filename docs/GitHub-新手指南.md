# 从 LLHY 开始学 GitHub

这份指南写给第一次使用 GitHub、看英文界面有压力的人。先记住一句话：**Git 负责记录文件的变化，GitHub 负责在网上保存和协作。** 你的项目仓库是 [LLHY](https://github.com/lih40377-creator/LLHY)。

## 你截图里的页面是什么

截图是 **GitHub Marketplace（应用市场）**，展示能连接 GitHub 的第三方 App 和能用于自动化的 Action。它不是安装浏览器汉化插件的地方。我们的“GitHub 界面中文助手”安装在 Chrome 的 `chrome://extensions` 页面，而不是 Marketplace。[GitHub 官方对 Marketplace 的说明](https://docs.github.com/zh/apps/using-github-apps)。

| 截图里的英文 | 意思 | 现在要做什么 |
| --- | --- | --- |
| Featured | 精选 | 只是推荐列表，可以先跳过 |
| Apps / All apps | 应用 / 全部应用 | 第三方服务，暂时不用安装 |
| Actions | 自动化步骤 | 以后需要自动测试或部署时再学 |
| Recommended | 推荐 | 平台推荐的项目 |
| Recently added | 最近添加 | 新上架的项目 |
| Learning | 学习类 | 想找教程时可以看 |
| Localization | 本地化类 | 与语言翻译相关的工具分类 |
| Deployment | 部署类 | 以后公开运行网站时再研究 |
| Code review | 代码审查 | 供团队检查改动 |

**卡片上的 Render、CodeRabbit 等是产品名称，不必逐词翻译，也不用为了看懂 GitHub 而安装。** 安装 Marketplace App 时，GitHub 会显示它要求访问账号或仓库的哪些权限；先读懂权限再决定是否安装。[GitHub 官方权限说明](https://docs.github.com/en/apps/using-github-apps/about-using-github-apps)。

## 先认识你的仓库

打开 [LLHY](https://github.com/lih40377-creator/LLHY)，先看这些位置：

| 界面文字 | 中文理解 | 在 LLHY 里有什么用 |
| --- | --- | --- |
| Code | 文件 | 查看 `app.py`、`templates/`、`static/` 等代码 |
| README | 项目说明 | 先读功能和运行方法 |
| main | 主分支 | 目前正式保存的代码版本 |
| Commits / History | 修改记录 | 看每次保存了哪些变化 |
| Issues | 任务与问题 | 记录想做的功能或发现的错误 |
| Pull requests / PR | 合并申请 | 先检查修改，再合入 main |
| Actions | 自动化 | 查看自动测试、构建或部署流程 |
| Settings | 设置 | 管理仓库可见性和其他配置 |

GitHub 上的仓库保存代码和提交历史。你在笔记网站里写下的个人数据仍保存在自己电脑的 `instance/notes.db`，不在公开仓库里。**公开仓库意味着任何人可以查看代码**，以后也别把密码、密钥或个人备份文件上传进去。[仓库概念与可见性](https://docs.github.com/en/repositories/creating-and-managing-repositories/about-repositories)。

## 只需先记住 6 个词

1. **repository（仓库）**：项目文件夹加上修改历史。LLHY 就是你的仓库。
2. **commit（提交）**：给当前改动留一个可回看的记录。它先发生在本地或 GitHub 网页上。
3. **push（推送）**：把本地已有的 commit 传到 GitHub。
4. **pull（拉取）**：把 GitHub 上的新 commit 同步回电脑。
5. **branch（分支）**：一条独立的修改路线，便于尝试而不立刻改变 main。
6. **PR（Pull request，合并申请）**：请人检查分支里的改动，再决定是否合并到 main。

最常用的顺序是：**修改文件 → commit → push**。需要稳妥地修改正式版本时：**新建 branch → 修改 → PR → 检查 → merge**。[GitHub Flow 官方中文教程](https://docs.github.com/zh/get-started/using-github/github-flow)。

## 三个不需要会英文的练习

### 练习一：只看，不修改

1. 打开 [LLHY](https://github.com/lih40377-creator/LLHY)。
2. 在 **Code（文件）** 页向下找到 README，读懂项目介绍。
3. 点页面上的 **History / Commits（修改记录）**，选一条 commit，看看“新增”和“删除”的文件行。

### 练习二：记一个待办事项

1. 在仓库点 **Issues（任务与问题）**，再点 **New issue（新建）**。
2. 标题写“想给笔记增加的功能”，正文写一两句话。
3. 提交后，这条事项会留在仓库中，方便以后继续做。它是公开仓库的一部分，别写私人信息。

### 练习三：用分支修改一个练习文件

1. 在 **Code** 页选 **Add file → Create new file（添加文件 → 新建文件）**。
2. 文件名填 `docs/practice.md`，内容写 `# 我的 GitHub 练习`。
3. 点 **Commit changes（提交更改）**，选择创建新 branch 并发起 PR 的选项。
4. 在 PR 页面确认新增的只有这个练习文件，再点 **Create pull request**。
5. 看懂改动后，点 **Merge pull request（合并）**。完成后，main 就有了这个文件。

网页上修改了仓库后，电脑里的项目不会自动跟着变；下次在电脑上继续开发前，先 **pull**。你也可以先只做前两个练习。[GitHub 官方中文入门](https://docs.github.com/zh/get-started/using-github)。

## 汉化插件没有生效时

1. 在安装插件的**同一个 Chrome 账号资料**中打开 `chrome://extensions`，找到“GitHub 界面中文助手”，确认版本是 **1.2.0** 且处于启用状态。
2. 若安装位置是以前解压的 ZIP 文件夹，先移除旧版，再加载新版解压出的 `github-zh-extension` 文件夹。修改 GitHub 仓库里的源码不会自动更新本机安装的插件。若你直接修改的就是已安装文件夹，点 **重新加载** 即可。最后刷新 `https://github.com/marketplace`。
3. 点插件图标，确认“开启界面翻译”已勾选。默认 `Issues`、`Pull requests`、`Actions` 等会以中英对照显示。
4. 插件只覆盖内置词库。Marketplace 随时新增的商品说明可能仍是英文；Chrome 页面右键菜单里的“翻译成中文”可用来读这些长说明。

GitHub 官方文档有[中文版](https://docs.github.com/zh)。看不懂某个英文按钮时，先找这个页面的中文文档，再决定是否点击。
