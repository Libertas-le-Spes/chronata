import { act } from "./actions.js";
import { $ } from "./dom.js";
import { askForHours, rememberHours } from "./hours_dialog.js";

let defaultLabel = "";

export async function changeHours(label) {
  const answer = await askForHours(label, false);
  if (answer) act("/api/labels/hours", answer);
}

export function render(state) {
  rememberHours(state.labelHours);
  defaultLabel = state.defaultLabel || (state.labelHours[0] || {}).label || "";
  $("#hours-button").hidden = !state.labelHours.length;
}

export function wire() {
  $("#hours-button").addEventListener("click", () => changeHours(defaultLabel));
}
