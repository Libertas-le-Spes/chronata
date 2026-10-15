import { act } from "./actions.js";
import { clockTime, dayLabel, hours, lateLabel, longDate, weekStart } from "./dates.js";
import { $, el, fields } from "./dom.js";
import { today } from "./server_time.js";

function proofLine(shift) {
  const { fromPcOn, entry, stamps } = shift.proof;
  const source = fromPcOn ? `PC came on at ${clockTime(shift.start)}` : `Start logged in entry ${entry}`;
  const by = stamps.map((s) => `${s.authority} ${s.time.slice(0, 10) === shift.start.slice(0, 10) ? clockTime(s.time) : `${dayLabel(s.time)} ${clockTime(s.time)}`}`);
  return el("p", { class: `proof ${fromPcOn ? "pc-on" : ""}` },
    stamps.length ? `${source} · independently timestamped by ${by.join(", ")}` : `${source} · not yet independently timestamped`);
}

function pcChip(shift) {
  const { share, sessions, beforeRecords } = shift.pc;
  if (!sessions.length) return beforeRecords ? el("span", { class: "chip" }, "No PC record") : el("span", { class: "chip warn" }, "PC was off");
  if (share >= 0.98) return el("span", { class: "chip live" }, shift.end ? "PC on throughout" : "PC on");
  return el("span", { class: "chip warn" }, `PC on for ${Math.round(share * 100)}%`);
}

function chips(shift, day) {
  const found = [];
  if (shift.label) found.push(el("span", { class: "chip label" }, shift.label));
  if (day) found.push(el("span", { class: `chip ${day.madeUp ? "live" : "warn"}` },
    !day.late ? `${hours(day.short)} short of a full day`
      : day.madeUp ? `Late ${hours(day.late)} · made up, left ${clockTime(day.lastOut).slice(0, 5)}`
      : `Late ${hours(day.late)} · ${hours(day.short)} short`));
  if (!shift.end) found.push(el("span", { class: "chip live" }, "Open"));
  if (shift.voided) found.push(el("span", { class: "chip" }, "Struck out"));
  if (shift.lateBy != null) found.push(shift.proof.fromPcOn
    ? el("span", { class: "chip" }, "Written down later, from the PC-on time")
    : el("span", { class: "chip warn" }, `Entered ${lateLabel(shift.lateBy)} after the fact`));
  found.push(pcChip(shift));
  const corrections = shift.changes.filter((change) => change.includes(" changed ")).length;
  if (corrections) found.push(el("span", { class: "chip" }, corrections === 1 ? "Corrected" : `Corrected ${corrections}×`));
  return found;
}

function tools(shift) {
  if (shift.voided) return el("span", { class: "tools" });
  const labelButton = el("button", { type: "button", class: "link", onclick: () => {
    const label = prompt("Client or project for this shift (leave empty to remove)", shift.label);
    if (label !== null) act("/api/label", { id: shift.id, label });
  } }, "Label");
  return el("span", { class: "tools" },
    labelButton,
    shift.end ? el("button", { type: "button", class: "link", onclick: () => openCorrect(shift) }, "Correct") : null,
    shift.end ? el("button", { type: "button", class: "link", onclick: () => openStrike(shift) }, "Strike out") : null,
  );
}

function trail(shift) {
  const pcLines = shift.pc.sessions.map((s) => el("li", {}, `PC on ${dayLabel(s.on)} ${clockTime(s.on).slice(0, 5)} – ${s.off ? `${dayLabel(s.off)} ${clockTime(s.off).slice(0, 5)}` : "still on"}${s.off ? (s.exact ? ", at shutdown" : ", last activity") : ""}`));
  return [...shift.notes.map((note) => el("li", { class: "note" }, note)), ...pcLines, ...shift.changes.map((change) => el("li", {}, change))];
}

function shiftCard(shift, day) {
  const tags = chips(shift, day);
  const history = trail(shift);
  return el("div", { class: `shift ${shift.voided ? "voided" : ""}` },
    el("div", { class: "shift-row" },
      el("span", { class: "when" }, dayLabel(shift.start)),
      el("span", { class: "span" }, `${clockTime(shift.start)} – ${shift.end ? clockTime(shift.end) : "now"}`),
      el("span", { class: "worked" }, shift.worked == null ? "" : hours(shift.worked)),
      tools(shift),
    ),
    proofLine(shift),
    tags.length ? el("div", { class: "chips" }, tags) : null,
    history.length ? el("ul", { class: "trail" }, history) : null,
  );
}

function openCorrect(shift) {
  const form = $("#correct-form");
  form.elements.id.value = shift.id;
  form.elements.start.value = shift.start.slice(0, 19);
  form.elements.end.value = shift.end.slice(0, 19);
  form.elements.reason.value = "";
  $("#correct-dialog").showModal();
}

function openStrike(shift) {
  const form = $("#strike-form");
  form.elements.id.value = shift.id;
  form.elements.reason.value = "";
  $("#strike-dialog").showModal();
}

function firstShiftOfEachDay(state) {
  const firstOfDay = new Map();
  for (const [date, day] of Object.entries(state.days)) {
    const earliest = state.shifts.filter((s) => s.start.slice(0, 10) === date && !s.voided).sort((a, b) => a.start.localeCompare(b.start))[0];
    if (earliest) firstOfDay.set(earliest.id, day);
  }
  return firstOfDay;
}

function byWeek(shifts) {
  const groups = new Map();
  for (const shift of shifts) {
    const key = weekStart(shift.start);
    if (!groups.has(key)) groups.set(key, []);
    groups.get(key).push(shift);
  }
  return groups;
}

export function render(state) {
  const date = $("#add-form").elements.date;
  if (!date.value) date.value = today();
  const container = $("#shifts");
  if (!state.shifts.length) {
    container.replaceChildren(el("div", { class: "card empty" }, "No shifts yet. Clock in above, or add one you missed."));
    return;
  }
  const weeks = new Map(state.weeks.map((week) => [week.start, week]));
  const firstOfDay = firstShiftOfEachDay(state);
  container.replaceChildren(...[...byWeek(state.shifts)].map(([start, shifts]) => {
    const week = weeks.get(start);
    return el("section", { class: "week" },
      el("div", { class: "week-head" },
        el("h3", {}, `Week of ${longDate(start)}`),
        week ? el("span", { class: "sum" }, el("strong", {}, hours(week.worked)), " worked · ", el("strong", {}, hours(week.overtime)), week.running ? " overtime so far" : " overtime") : null,
      ),
      el("div", { class: "shift-list" }, shifts.map((shift) => shiftCard(shift, firstOfDay.get(shift.id)))),
    );
  }));
}

export function wire() {
  $("#add-form").addEventListener("submit", async (event) => {
    event.preventDefault();
    if (await act("/api/add", fields(event.target), event.target)) {
      event.target.reset();
      event.target.elements.date.value = today();
    }
  });
  for (const [formId, dialogId, path] of [["#correct-form", "#correct-dialog", "/api/correct"], ["#strike-form", "#strike-dialog", "/api/strike"]]) {
    $(formId).addEventListener("submit", async (event) => {
      event.preventDefault();
      if (await act(path, fields(event.target), event.target)) $(dialogId).close();
    });
  }
}
