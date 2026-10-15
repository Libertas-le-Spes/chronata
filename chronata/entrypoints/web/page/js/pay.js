import { act } from "./actions.js";
import { dayLabel, hours, longDate } from "./dates.js";
import { $, el, fields } from "./dom.js";

function renderTotals(totals) {
  $("#t-owed").textContent = hours(totals.owed);
  $("#t-compensated").textContent = hours(totals.compensated);
  $("#t-shortfall").textContent = hours(totals.shortfall);
  $("#t-unmatched").textContent = hours(totals.unmatched);
  $("#t-shortfall").parentElement.classList.toggle("has-value", totals.shortfall > 0);
}

function periodCard(period) {
  const settled = period.shortfall === 0;
  return el("div", { class: "card period" },
    el("div", { class: "period-head" },
      el("h3", {}, `${longDate(period.start)} – ${longDate(period.end)}`),
      el("span", { class: "muted small" }, period.references.join("; ")),
    ),
    el("div", { class: "figures" },
      el("div", {}, el("span", {}, "Overtime worked"), el("span", {}, hours(period.owed))),
      el("div", {}, el("span", {}, "Paid"), el("span", {}, hours(period.paid))),
      el("div", {}, el("span", {}, "Time off"), el("span", {}, hours(period.timeOff))),
      el("div", { class: settled ? "good" : "bad" }, el("span", {}, "Uncompensated"), el("span", {}, settled ? "None" : hours(period.shortfall))),
    ),
  );
}

export function render(state) {
  renderTotals(state.totals);
  const unmatched = $("#unmatched");
  unmatched.replaceChildren();
  if (state.unmatched.length) {
    unmatched.append(el("div", { class: "card" },
      el("h2", {}, "Overtime no payslip covers yet"),
      el("p", { class: "muted small" }, "When the payslip for these days arrives, record it above."),
      el("ul", { class: "days" }, state.unmatched.map((day) => el("li", {}, `${dayLabel(day.date)} · ${hours(day.overtime)}`))),
    ));
  }
  $("#periods").replaceChildren(...state.periods.map(periodCard));
}

export function wire() {
  $("#paid-form").addEventListener("submit", async (event) => {
    event.preventDefault();
    const body = fields(event.target);
    if (await act("/api/paid", { ...body, timeOff: body.timeOff === "1" }, event.target)) event.target.reset();
  });
}
