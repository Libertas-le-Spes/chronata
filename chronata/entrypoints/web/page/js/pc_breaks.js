import { act } from "./actions.js";
import { clockTime, dayLabel } from "./dates.js";
import { $, el, fields } from "./dom.js";

function breakCard(gap) {
  const form = el("form", { class: "grid-form" },
    el("label", { class: "wide" }, `Why was the PC off from ${clockTime(gap.start).slice(0, 5)} to ${clockTime(gap.end).slice(0, 5)} on ${dayLabel(gap.start)}?`,
      el("input", { name: "reason", type: "text", required: true, autocomplete: "off", placeholder: "e.g. power cut, restart for updates, went home" })),
    el("button", { class: "primary wide", type: "submit" }, "Add to the record"),
  );
  form.addEventListener("submit", (event) => {
    event.preventDefault();
    act("/api/explain", { id: gap.shift, start: gap.start, reason: fields(form).reason }, form);
  });
  return el("section", { class: "card pc-break" },
    el("h2", {}, "Your PC was off during a shift"),
    el("p", { class: "muted" }, "That time isn't counted as work. Saying why keeps the record self-explaining."),
    form,
  );
}

export function render(state) {
  $("#pc-breaks").replaceChildren(...state.unexplainedBreaks.map(breakCard));
}

export function focusFirst() {
  $("#pc-breaks input")?.focus();
}
