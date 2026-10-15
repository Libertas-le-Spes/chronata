import { $ } from "./dom.js";

let toastTimer;

export function toast(text, tone = "") {
  const node = $("#toast");
  node.textContent = text;
  node.className = `toast ${tone}`;
  node.hidden = false;
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => (node.hidden = true), tone ? 9000 : 4000);
}
