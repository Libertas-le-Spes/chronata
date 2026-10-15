import { act } from "./actions.js";
import { api } from "./api.js";
import { clockedIn, shiftOpen } from "./clock.js";
import { hours } from "./dates.js";
import { $, el } from "./dom.js";

let hintTimer;
let hints = [];

function watchLabel(input) {
  const hint = input.closest("form").querySelector(".label-hint");
  const describe = async () => {
    const typed = input.value;
    if (!typed.trim()) {
      hint.textContent = hint.dataset.whenEmpty || "No label: goes into the “No label” folder";
      return;
    }
    const { label, exists, folder, nearMisses } = await api(`/api/label-check?text=${encodeURIComponent(typed)}`);
    if (input.value !== typed) return;
    if (exists) hint.replaceChildren(`Adds to the “${folder}” folder` + (label !== typed.trim() ? ` (as ${label})` : ""));
    else if (nearMisses.length) hint.replaceChildren(`New folder “${folder}”. Did you mean `,
      ...nearMisses.map((miss) => el("button", { type: "button", class: "link", onclick: () => { input.value = miss; describe(); } }, miss)), "?");
    else hint.textContent = `Creates a new folder: “${folder}”`;
  };
  input.addEventListener("input", () => { clearTimeout(hintTimer); hintTimer = setTimeout(describe, 200); });
  return describe;
}

function renameLabel(old, known) {
  const to = prompt(`New name for “${old}”. Every shift labelled ${old} moves with it.`, old);
  if (to === null || !to.trim() || to.trim() === old) return;
  const existing = known.find((name) => name.toLowerCase() === to.trim().toLowerCase() && name !== old);
  if (existing && !confirm(`“${existing}” already exists. Merge ${old} into ${existing}? Both folders become one.`)) return;
  act("/api/labels/rename", { from: old, to: to.trim() });
}

function labelRow(row, state) {
  const isDefault = row.label === state.defaultLabel;
  return el("tr", {},
    el("td", {}, row.label, isDefault ? el("span", { class: "chip label" }, "default") : null,
      row.openNow ? el("span", { class: "chip live" }, " open") : null),
    el("td", { class: "muted" }, `${row.folder}/`),
    el("td", { class: "number" }, hours(row.week)), el("td", { class: "number" }, hours(row.all)),
    el("td", { class: "row-actions" },
      el("button", { type: "button", class: "link", onclick: () => renameLabel(row.label, state.labels) }, "Rename"),
      el("button", { type: "button", class: "link", onclick: () => act("/api/default-label", { label: isDefault ? "" : row.label }) },
        isDefault ? "No default" : "Make default")),
  );
}

export function render(state) {
  $("#known-labels").replaceChildren(...state.labels.map((label) => el("option", { value: label })));
  const labelInput = $("#clock-form").elements.label;
  labelInput.hidden = clockedIn();
  $("#clock-form .label-hint").hidden = labelInput.hidden;
  if (!shiftOpen() && document.activeElement !== labelInput && !labelInput.value) labelInput.value = state.suggestedLabel;
  hints.forEach((describe) => describe().catch(() => {}));
  const rows = state.labelSummary.filter((row) => row.label);
  $("#by-label").replaceChildren(...(rows.length ? [el("div", { class: "card" },
    el("h3", {}, "Labels"),
    el("table", { class: "label-table" },
      el("tr", {}, el("th", {}, "Label"), el("th", {}, "Folder"), el("th", { class: "number" }, "This week"), el("th", { class: "number" }, "All time"), el("th", {}, "")),
      ...rows.map((row) => labelRow(row, state)),
    ),
  )] : []));
}

export function wire() {
  hints = [...document.querySelectorAll('input[name="label"]')].map(watchLabel);
}
