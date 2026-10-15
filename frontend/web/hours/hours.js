import { act } from "../shared/actions.js";
import { DAY_NAME } from "../shared/dates.js";
import { $ } from "../shared/dom.js";
import { ask } from "../shared/question.js";

let labelHours = [];
let defaultLabel = "";

function measuredBy(hours) {
  if (!hours || !hours.setHours) return "It has no set hours: only the time worked is counted.";
  const off = hours.daysOff.length ? `, and every hour on ${hours.daysOff.map((d) => DAY_NAME[d]).join(", ")}` : "";
  return `Overtime counts past ${hours.dailyHours} h a day and ${hours.weeklyHours} h a week${off}.`;
}

export async function changeHours(label) {
  const hours = labelHours.find((h) => h.label === label);
  const answer = await ask({
    title: `Hours for “${label}”`,
    text: `Overtime, late arrivals and short days for ${label} are measured against these. ${measuredBy(hours)}`,
    choices: [
      { caption: "No set hours", answers: { no_set_hours: true } },
      { caption: "Save hours", style: "primary", inputs: hours.hoursInputs },
    ],
  });
  if (answer) act("/api/labels/hours", { label, ...answer.answers });
}

export function render(state) {
  labelHours = state.labelHours;
  defaultLabel = state.defaultLabel || (labelHours[0] || {}).label || "";
  $("#hours-button").hidden = !labelHours.length;
}

export function wire() {
  $("#hours-button").addEventListener("click", () => changeHours(defaultLabel));
}
