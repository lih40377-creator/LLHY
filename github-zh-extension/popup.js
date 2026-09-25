const defaults = ["Issues", "Pull requests", "Actions", "Copilot", "README"];
const enabled = document.getElementById("enabled");
const preserved = document.getElementById("preserved");
const status = document.getElementById("status");

chrome.storage.local.get({ enabled: true, preserved: defaults }, (settings) => {
  enabled.checked = settings.enabled;
  preserved.value = settings.preserved.join("\n");
});

function save() {
  const words = [...new Set(preserved.value.split(/\r?\n/).map(value => value.trim()).filter(Boolean))].slice(0, 100);
  chrome.storage.local.set({ enabled: enabled.checked, preserved: words }, () => {
    status.textContent = "已保存，GitHub 页面会立即更新。";
  });
}

enabled.addEventListener("change", save);
preserved.addEventListener("change", save);
