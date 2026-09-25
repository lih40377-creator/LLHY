document.addEventListener('DOMContentLoaded', () => {
  if (document.body.dataset.clearDraftKey) {
    try { localStorage.removeItem(`zhiyenotes:draft:${document.body.dataset.clearDraftKey}`); } catch (_) { /* Ignore unavailable storage. */ }
  }
  document.querySelectorAll('form[data-confirm]').forEach(form => {
    form.addEventListener('submit', event => {
      if (!window.confirm(form.dataset.confirm)) event.preventDefault();
    });
  });

  const editor = document.querySelector('form[data-draft-key]');
  if (!editor) return;
  const key = `zhiyenotes:draft:${editor.dataset.draftKey}`;
  const fields = ['title', 'tags', 'content'];
  const status = document.getElementById('draft-status');
  try {
    const draft = JSON.parse(localStorage.getItem(key) || 'null');
    if (draft && Object.values(draft).some(Boolean) && window.confirm('发现此浏览器暂存的草稿，是否恢复？')) {
      fields.forEach(name => { if (draft[name] != null) editor.elements[name].value = draft[name]; });
      status.textContent = '草稿已恢复';
    }
  } catch (_) { /* Storage may be unavailable in private browsing. */ }
  let timer;
  editor.addEventListener('input', () => {
    window.clearTimeout(timer);
    timer = window.setTimeout(() => {
      try {
        const draft = Object.fromEntries(fields.map(name => [name, editor.elements[name].value]));
        localStorage.setItem(key, JSON.stringify(draft));
        status.textContent = '草稿已暂存于此浏览器';
      } catch (_) { status.textContent = '浏览器未允许暂存草稿'; }
    }, 400);
  });
});
