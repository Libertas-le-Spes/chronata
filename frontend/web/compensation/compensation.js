import { act } from "../shared/actions.js";
import { dayLabel, hours, longDate } from "../shared/dates.js";
import { $, el, fields } from "../shared/dom.js";

let defaultLabel = "";

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

function labelSection(section) {
  const name = section.label || "No label";
  return el("section", { class: "compensation-label" },
    el("div", { class: "week-head" },
      el("h3", {}, name),
      el("span", { class: "sum" }, el("strong", {}, hours(section.totals.owed)), " overtime · ",
        el("strong", {}, hours(section.totals.compensated)), " compensated"),
    ),
    section.unmatched.length ? el("div", { class: "card" },
      el("h2", {}, "Overtime no compensation covers yet"),
      el("p", { class: "muted small" }, `When ${name} compensates these days, record it above.`),
      el("ul", { class: "days" }, section.unmatched.map((day) => el("li", {}, `${dayLabel(day.date)} · ${hours(day.overtime)}`))),
    ) : null,
    ...section.periods.map(periodCard),
  );
}

export function render(state) {
  renderTotals(state.totals);
  defaultLabel = state.defaultLabel;
  const label = $("#compensation-form").elements.label;
  if (document.activeElement !== label && !label.value) label.value = defaultLabel;
  $("#compensation-labels").replaceChildren(...state.compensation.map(labelSection));
}

export function wire() {
  $("#compensation-form").addEventListener("submit", async (event) => {
    event.preventDefault();
    const body = fields(event.target);
    if (await act("/api/compensation", { ...body, timeOff: body.timeOff === "1" }, event.target)) {
      event.target.reset();
      event.target.elements.label.value = defaultLabel;
    }
  });
}
