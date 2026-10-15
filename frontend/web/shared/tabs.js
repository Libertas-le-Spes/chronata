export function showTab(name) {
  document.querySelectorAll(".tabs button").forEach((tab) => tab.setAttribute("aria-selected", String(tab.dataset.tab === name)));
  document.querySelectorAll(".tab").forEach((panel) => (panel.hidden = panel.id !== `tab-${name}`));
  try { localStorage.setItem("chronata-tab", name); } catch {}
}

export function showRememberedTab() {
  try { showTab(localStorage.getItem("chronata-tab") || "shifts"); } catch { showTab("shifts"); }
}

export function hasTab(name) {
  return Boolean(document.getElementById(`tab-${name}`));
}

export function wire() {
  document.querySelectorAll(".tabs button").forEach((tab) => tab.addEventListener("click", () => showTab(tab.dataset.tab)));
}
