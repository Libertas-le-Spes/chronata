import { DAY_NAME } from "./dates.js";
import { $, el, fields } from "./dom.js";

let labelHours = [];

export function rememberHours(hours) {
  labelHours = hours;
}

function describe(hours) {
  if (!hours) return "";
  if (!hours.setHours) return "No set hours: only the time worked is counted.";
  const off = hours.daysOff.length ? `, and every hour on ${hours.daysOff.map((d) => DAY_NAME[d]).join(", ")}` : "";
  return `Overtime counts past ${hours.dailyHours} h a day and ${hours.weeklyHours} h a week${off}.`;
}

function fill(form, label) {
  const hours = labelHours.find((h) => h.label === label);
  form.elements.shift.value = hours ? hours.shift : "";
  form.elements.lunch.value = hours ? hours.lunch : "";
  form.elements.noSetHours.checked = Boolean(hours && !hours.setHours);
  showChoice(form);
  $("#hours-summary").textContent = describe(hours);
}

function showChoice(form) {
  const none = form.elements.noSetHours.checked;
  form.elements.shift.disabled = none;
  form.elements.lunch.disabled = none;
}

export function askForHours(label, isNew) {
  return new Promise((resolve) => {
    const dialog = $("#hours-dialog");
    const form = $("#hours-form");
    const select = form.elements.label;
    const choices = isNew ? [label] : labelHours.map((hours) => hours.label);
    select.replaceChildren(...choices.map((name) => el("option", { value: name }, name)));
    select.value = label;
    select.disabled = isNew;
    $("#hours-title").textContent = isNew ? `Hours for “${label}”` : "Hours";
    $("#hours-intro").textContent = isNew
      ? `“${label}” is a new label, with its own folder. Its hours are remembered, so next time clocking in on it just starts.`
      : "Each label keeps its own shift and lunch. Overtime, late arrivals and short days are measured against them.";
    fill(form, label);
    select.onchange = () => fill(form, select.value);
    form.elements.noSetHours.onchange = () => showChoice(form);
    let answer = null;
    form.onsubmit = (event) => {
      event.preventDefault();
      const typed = fields(form);
      answer = { label: select.value, shift: typed.shift || "", lunch: typed.lunch || "", noSetHours: form.elements.noSetHours.checked };
      dialog.close();
    };
    dialog.onclose = () => resolve(answer);
    dialog.showModal();
  });
}
