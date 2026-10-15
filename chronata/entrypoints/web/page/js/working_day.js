import { act } from "./actions.js";
import { DAY_NAME } from "./dates.js";
import { $, fields } from "./dom.js";

function renderSetup(setup) {
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

export function render(state) {
  const { dailyHours, weeklyHours, daysOff } = state.workingDay;
  const off = daysOff.length ? `, and every hour on ${daysOff.map((d) => DAY_NAME[d]).join(", ")}` : "";
  $("#working-day-summary").textContent = `Shift ${state.setup.shift}, lunch ${state.setup.lunch}. Overtime counts past ${dailyHours} h a day and ${weeklyHours} h a week${off}.`;
  renderSetup(state.setup);
}

export function wire() {
  $("#setup-form").addEventListener("submit", async (event) => {
    event.preventDefault();
    if (await act("/api/setup", fields(event.target), event.target)) $("#setup").hidden = true;
  });
  $("#setup-cancel").addEventListener("click", () => ($("#setup").hidden = true));
  $("#change-hours").addEventListener("click", () => {
    $("#setup").hidden = false;
    $("#setup").scrollIntoView({ behavior: "smooth" });
  });
}
