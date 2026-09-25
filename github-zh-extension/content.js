(() => {
  "use strict";

  // Exact interface labels only. Do not translate repository content or user text.
  const dictionary = Object.freeze({
    "Dashboard": "工作台", "Home": "首页", "Explore": "探索", "Marketplace": "应用市场",
    "Search": "搜索", "Search or jump to...": "搜索或跳转…", "Type / to search": "按 / 搜索",
    "Your dashboard": "你的工作台", "Your repositories": "你的仓库", "Repositories": "仓库",
    "Repository": "仓库", "New repository": "新建仓库", "Create a new repository": "新建仓库",
    "Create repository": "创建仓库", "New": "新建", "Create": "创建", "Cancel": "取消",
    "Save": "保存", "Save changes": "保存更改", "Edit": "编辑", "Delete": "删除",
    "Remove": "移除", "Close": "关闭", "Confirm": "确认", "Submit": "提交",
    "Update": "更新", "Done": "完成", "Back": "返回", "Next": "下一步",
    "Settings": "设置", "General": "常规", "Appearance": "外观", "Accessibility": "辅助功能",
    "Profile": "个人资料", "Account": "账号", "Notifications": "通知", "Sign out": "退出登录",
    "Sign in": "登录", "Sign up": "注册", "Username or email address": "用户名或邮箱",
    "Password": "密码", "Forgot password?": "忘记密码？", "New to GitHub?": "还没有 GitHub 账号？",
    "Overview": "概览", "Activity": "动态", "Stars": "星标", "Star": "加星标",
    "Unstar": "取消星标", "Watch": "关注", "Unwatch": "取消关注",
    "Fork": "fork", "Forks": "fork", "Code": "代码", "Clone": "clone",
    "Download ZIP": "下载 ZIP", "Open with GitHub Desktop": "在 GitHub Desktop 中打开",
    "Add file": "添加文件", "Upload files": "上传文件", "Create new file": "新建文件",
    "Go to file": "跳转到文件", "Find file": "查找文件", "View all files": "查看全部文件",
    "History": "历史记录", "Commits": "commits", "Commit changes": "提交 commit",
    "Latest commit": "最近的 commit", "Branches": "branches", "Branch": "branch",
    "Tags": "标签", "Releases": "发布版本", "Release": "发布版本",
    "Contributors": "贡献者", "Languages": "语言", "About": "关于",
    "Public": "公开", "Private": "私有", "Visibility": "可见性",
    "Public repository": "公开仓库", "Private repository": "私有仓库",
    "Owner": "所有者", "Repository name": "仓库名称", "Description": "简介",
    "Add a README file": "添加 README 文件", "Choose a license": "选择许可证",
    "Add .gitignore": "添加 .gitignore", "Initialize this repository": "初始化此仓库",
    "Issues": "议题", "New issue": "新建 issue", "Issue": "issue",
    "Pull requests": "PR", "New pull request": "新建 PR", "Compare & pull request": "比较并创建 PR",
    "Open": "未关闭", "Closed": "已关闭", "Merged": "已 merge",
    "Review changes": "审查更改", "Files changed": "变更的文件", "Conversation": "讨论",
    "Checks": "检查", "Projects": "项目", "Discussions": "讨论区", "Wiki": "Wiki",
    "Actions": "Actions", "Security": "安全", "Insights": "洞察",
    "People": "成员", "Teams": "团队", "Organizations": "组织",
    "Pinned": "已置顶", "Recently updated": "最近更新", "Sort": "排序", "Filter": "筛选",
    "All": "全部", "Clear": "清除", "Apply": "应用", "View more": "查看更多",
    "View all": "查看全部", "Show more": "展开更多", "Show less": "收起",
    "No results": "没有结果", "Loading...": "正在加载…", "Learn more": "了解更多",
    "Read more": "阅读更多", "Copy": "复制", "Copied!": "已复制！",
    "Copy link": "复制链接", "Share": "分享", "Preview": "预览",
    "Write": "编辑", "Comment": "评论", "Add a comment": "添加评论",
    "Edit profile": "编辑个人资料", "Edit repository details": "编辑仓库信息",
    "Pin": "置顶", "Unpin": "取消置顶", "Archive": "归档", "Unarchive": "取消归档",
    "You don't have any repositories yet.": "你还没有仓库。"
  });

  const defaults = ["Issues", "Pull requests", "Actions", "Copilot", "README"];
  const excluded = "pre, code, kbd, samp, [contenteditable], .markdown-body, .comment-body, .js-comment-body, .blob-code, .react-code-text, [data-testid='issue-body'], [data-testid='issue-comment']";
  const uiAreas = "header, nav, [role='navigation'], [role='menu'], [role='menuitem'], [role='tablist'], [role='tab'], [role='dialog'], button, [role='button'], label, summary, h1, h2, h3";
  const attributes = ["aria-label", "title", "placeholder"];
  const changedText = new Map();
  const changedAttributes = new Map();
  const pending = new Set();
  let enabled = true;
  let preserved = new Set(defaults);
  let scheduled = false;

  function translate(value) {
    const match = /^(\s*)(.*?)(\s*)$/s.exec(value);
    const label = match[2];
    if (!Object.hasOwn(dictionary, label) || preserved.has(label)) return value;
    return match[1] + dictionary[label] + match[3];
  }

  function eligible(element) {
    return element && !element.closest(excluded) && Boolean(element.closest(uiAreas));
  }

  function translateText(node) {
    const element = node.parentElement;
    if (!eligible(element)) return;
    const previous = changedText.get(node);
    if (previous && node.nodeValue === previous.translated) return;
    const original = node.nodeValue;
    const translated = translate(original);
    if (translated !== original) {
      changedText.set(node, { original, translated });
      node.nodeValue = translated;
    } else {
      changedText.delete(node);
    }
  }

  function translateAttributes(element) {
    if (!eligible(element)) return;
    for (const attribute of attributes) {
      if (!element.hasAttribute(attribute)) continue;
      const key = `${attribute}`;
      const original = element.getAttribute(attribute);
      const translated = translate(original);
      if (translated !== original) {
        let entries = changedAttributes.get(element);
        if (!entries) {
          entries = new Map();
          changedAttributes.set(element, entries);
        }
        entries.set(key, { original, translated });
        element.setAttribute(attribute, translated);
      }
    }
  }

  function scan(root) {
    if (!enabled || !root || !root.isConnected) return;
    if (root.nodeType === Node.TEXT_NODE) {
      translateText(root);
      return;
    }
    if (root.nodeType !== Node.ELEMENT_NODE || root.closest(excluded)) return;
    translateAttributes(root);
    const walker = document.createTreeWalker(root, NodeFilter.SHOW_ELEMENT | NodeFilter.SHOW_TEXT);
    while (walker.nextNode()) {
      const node = walker.currentNode;
      if (node.nodeType === Node.TEXT_NODE) translateText(node);
      else translateAttributes(node);
    }
  }

  function restore() {
    for (const [node, entry] of changedText) {
      if (node.isConnected && node.nodeValue === entry.translated) node.nodeValue = entry.original;
    }
    changedText.clear();
    for (const [element, entries] of changedAttributes) {
      if (!element.isConnected) continue;
      for (const [name, entry] of entries) {
        if (element.getAttribute(name) === entry.translated) element.setAttribute(name, entry.original);
      }
    }
    changedAttributes.clear();
  }

  function flush() {
    scheduled = false;
    if (!enabled) return;
    for (const node of pending) scan(node);
    pending.clear();
    for (const node of changedText.keys()) if (!node.isConnected) changedText.delete(node);
    for (const element of changedAttributes.keys()) if (!element.isConnected) changedAttributes.delete(element);
  }

  const observer = new MutationObserver((mutations) => {
    if (!enabled) return;
    for (const mutation of mutations) {
      if (mutation.type === "characterData") pending.add(mutation.target);
      else for (const node of mutation.addedNodes) pending.add(node);
    }
    if (!scheduled && pending.size) {
      scheduled = true;
      queueMicrotask(flush);
    }
  });

  chrome.storage.local.get({ enabled: true, preserved: defaults }, (settings) => {
    enabled = settings.enabled;
    preserved = new Set(settings.preserved);
    observer.observe(document.documentElement, { childList: true, characterData: true, subtree: true });
    scan(document.body);
  });

  chrome.storage.onChanged.addListener((changes, area) => {
    if (area !== "local" || (!changes.enabled && !changes.preserved)) return;
    restore();
    if (changes.enabled) enabled = changes.enabled.newValue;
    if (changes.preserved) preserved = new Set(changes.preserved.newValue);
    pending.clear();
    scan(document.body);
  });
})();
