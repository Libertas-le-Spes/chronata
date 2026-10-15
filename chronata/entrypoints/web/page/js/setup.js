import { act } from "./actions.js";
import { $, fields } from "./dom.js";

export function render(state) {
  const { setup } = state;
  const form = $("#setup-form");
  $("#lunch-question").textContent = setup.lunchQuestion;
  $("#shift-question").textContent = setup.shiftQuestion;
  $("#default-label-question").textContent = setup.defaultLabelQuestion;
  if ($("#setup").hidden) {
    form.elements.lunch.value = setup.lunch;
    form.elements.shift.value = setup.shift;
    form.elements.label.value = setup.defaultLabel;
  }
  $("#setup-cancel").hidden = setup.needed;
  if (setup.needed) $("#setup").hidden = false;
}

export function wire() {
  $("#setup-form").addEventListener("submit", async (event) => {
    event.preventDefault();
    if (await act("/api/setup", fields(event.target), event.target)) $("#setup").hidden = true;
  });
  $("#setup-cancel").addEventListener("click", () => ($("#setup").hidden = true));
}
