document.addEventListener('DOMContentLoaded', () => {
  if (document.body.dataset.clearDraftKey) {
    try { localStorage.removeItem(`zhiyenotes:draft:${document.body.dataset.clearDraftKey}`); } catch (_) { /* Storage may be unavailable. */ }
  }

  document.querySelectorAll('form[data-confirm]').forEach(form => {
    form.addEventListener('submit', event => {
      if (!window.confirm(form.dataset.confirm)) event.preventDefault();
    });
  });

  const editor = document.querySelector('form[data-draft-key]');
  if (!editor) return;

  const fields = ['title', 'tags', 'content'];
  const content = editor.elements.content;
  const preview = document.getElementById('markdown-preview');
  const status = document.getElementById('draft-status');
  const count = document.getElementById('word-count');
  const csrf = editor.elements.csrf_token.value;
  let noteId = editor.dataset.noteId ? Number(editor.dataset.noteId) : null;
  let key = `zhiyenotes:draft:${editor.dataset.draftKey}`;
  let localTimer;
  let saveTimer;
  let previewTimer;
  let previewVersion = 0;
  let editVersion = 0;
  let inFlight = null;
  let submitting = false;

  function updateCount() {
    const characters = content.value.trim().length;
    count.textContent = `${characters} 字 · 约 ${Math.max(1, Math.ceil(characters / 400))} 分钟阅读`;
  }

  async function updatePreview() {
    const version = ++previewVersion;
    if (!content.value.trim()) {
      preview.textContent = '预览会显示在这里。';
      return;
    }
    try {
      const response = await fetch(editor.dataset.previewUrl, {
        method: 'POST', credentials: 'same-origin',
        headers: { 'Content-Type': 'application/json', 'X-CSRF-Token': csrf },
        body: JSON.stringify({ content: content.value })
      });
      if (!response.ok) throw new Error('Preview unavailable');
      const data = await response.json();
      if (version === previewVersion) preview.innerHTML = data.html;
    } catch (_) {
      if (version === previewVersion) preview.textContent = '预览暂时不可用，正文仍可继续编辑。';
    }
  }

  async function saveNow() {
    if (submitting || inFlight) return inFlight;
    if (!editor.elements.title.value.trim() && !content.value.trim()) return null;
    const version = editVersion;
    status.textContent = '正在自动保存…';
    inFlight = (async () => {
      try {
        const response = await fetch(editor.dataset.autosaveUrl, {
          method: 'POST', credentials: 'same-origin',
          headers: { 'Content-Type': 'application/json', 'X-CSRF-Token': csrf },
          body: JSON.stringify({
            note_id: noteId,
            title: editor.elements.title.value,
            content: content.value,
            tags: editor.elements.tags.value,
            is_pinned: editor.elements.is_pinned.checked
          })
        });
        if (!response.ok) throw new Error('Autosave failed');
        const data = await response.json();
        if (data.saved) {
          if (!noteId) {
            const oldKey = key;
            noteId = data.id;
            editor.elements.note_id.value = String(noteId);
            editor.action = data.edit_url;
            history.replaceState(null, '', data.edit_url);
            key = `zhiyenotes:draft:note-${noteId}`;
            try { localStorage.removeItem(oldKey); } catch (_) { /* Ignore unavailable storage. */ }
          }
          if (version === editVersion) {
            status.textContent = `已自动保存 · ${data.saved_at}`;
            try { localStorage.removeItem(key); } catch (_) { /* Ignore unavailable storage. */ }
          }
        }
      } catch (_) {
        status.textContent = '网络异常，草稿暂存在此浏览器';
      } finally {
        inFlight = null;
        if (!submitting && version !== editVersion) {
          clearTimeout(saveTimer);
          saveTimer = setTimeout(saveNow, 600);
        }
      }
    })();
    return inFlight;
  }

  try {
    const draft = JSON.parse(localStorage.getItem(key) || 'null');
    if (draft && fields.some(name => draft[name] && draft[name] !== editor.elements[name].value) && window.confirm('发现此浏览器暂存的草稿，是否恢复？')) {
      fields.forEach(name => { if (draft[name] != null) editor.elements[name].value = draft[name]; });
      status.textContent = '草稿已恢复，正在同步';
      editVersion++;
      saveTimer = setTimeout(saveNow, 1200);
    }
  } catch (_) { /* Storage may be unavailable. */ }

  function onEdit() {
    editVersion++;
    updateCount();
    clearTimeout(localTimer);
    clearTimeout(saveTimer);
    clearTimeout(previewTimer);
    localTimer = setTimeout(() => {
      try {
        localStorage.setItem(key, JSON.stringify(Object.fromEntries(fields.map(name => [name, editor.elements[name].value]))));
      } catch (_) { /* Server save remains available. */ }
    }, 250);
    saveTimer = setTimeout(saveNow, 1200);
    previewTimer = setTimeout(updatePreview, 250);
    status.textContent = '尚未保存的更改';
  }

  fields.forEach(name => editor.elements[name].addEventListener('input', onEdit));
  editor.elements.is_pinned.addEventListener('change', onEdit);

  document.querySelectorAll('[data-md-before]').forEach(button => {
    button.addEventListener('click', () => {
      const start = content.selectionStart;
      const end = content.selectionEnd;
      const before = button.dataset.mdBefore || '';
      const after = button.dataset.mdAfter || '';
      const selection = content.value.slice(start, end);
      content.setRangeText(before + selection + after, start, end, 'select');
      content.focus();
      content.setSelectionRange(start + before.length, start + before.length + selection.length);
      onEdit();
    });
  });

  editor.addEventListener('submit', async event => {
    event.preventDefault();
    if (submitting) return;
    submitting = true;
    clearTimeout(saveTimer);
    clearTimeout(localTimer);
    if (inFlight) await inFlight;
    editor.submit();
  });

  updateCount();
  updatePreview();
});
