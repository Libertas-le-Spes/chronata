import { act } from "../shared/actions.js";
import { $, fields } from "../shared/dom.js";
import { inputField } from "../shared/input_field.js";
import { timeFields } from "../time_picker/time_field.js";

export function render(state) {
  const { setup } = state;
  const form = $("#setup-form");
  $("#default-label-question").textContent = setup.defaultLabelQuestion;
  if ($("#setup").hidden) {
    form.elements.label.value = setup.defaultLabel;
    $("#setup-hours").replaceChildren(...setup.hoursInputs.map(inputField));
    timeFields($("#setup-hours"));
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
