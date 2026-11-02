import { act } from "../shared/actions.js";
import { dayLabel, hours, longDate } from "../shared/dates.js";
import { $, el, fields } from "../shared/dom.js";

let defaultLabel = "";

function takenOff(minutes) {
  return `-${hours(minutes)}`;
}

function renderTotals(totals) {
  $("#t-owed").textContent = hours(totals.owed);
  $("#t-compensated").textContent = hours(totals.compensated);
  $("#t-unpaid").textContent = hours(totals.unpaid);
  $("#t-unpaid").parentElement.classList.toggle("has-value", totals.unpaid > 0);
}

function latenessItem(late) {
  return el("li", {}, `${dayLabel(late.date)} · ${takenOff(late.late)}`);
}

function latenessCard(lateness) {
  if (lateness.length === 0) {
    return null;
  }
  return el("div", { class: "card" },
    el("h2", {}, "Lateness not covered that day"),
    el("p", { class: "muted small" }, "Taken off what is unpaid."),
    el("ul", { class: "days" }, lateness.map(latenessItem)),
  );
}

function periodCard(period) {
  const settled = period.unpaid === 0;
  return el("div", { class: "card period" },
    el("div", { class: "period-head" },
      el("h3", {}, `${longDate(period.start)} – ${longDate(period.end)}`),
      el("span", { class: "muted small" }, period.references.join("; ")),
    ),
    el("div", { class: "figures" },
      el("div", {}, el("span", {}, "Overtime worked"), el("span", {}, hours(period.owed))),
      el("div", {}, el("span", {}, "Paid"), el("span", {}, hours(period.paid))),
      el("div", {}, el("span", {}, "Time off"), el("span", {}, hours(period.timeOff))),
      el("div", { class: settled ? "good" : "bad" }, el("span", {}, "Unpaid"), el("span", {}, settled ? "None" : hours(period.unpaid))),
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
      el("h2", {}, "Unpaid overtime"),
      el("p", { class: "muted small" }, `When ${name} compensates these days, record it above.`),
      el("ul", { class: "days" }, section.unmatched.map((day) => el("li", {}, `${dayLabel(day.date)} · ${hours(day.overtime)}`))),
    ) : null,
    latenessCard(section.lateness),
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
    if (await act("/api/compensation", body, event.target)) {
      event.target.reset();
      event.target.elements.label.value = defaultLabel;
    }
  });
}
