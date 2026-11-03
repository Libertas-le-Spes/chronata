import { act } from "../shared/actions.js";
import { clockTime, dayLabel, hours, lateLabel, longDate, weekStart } from "../shared/dates.js";
import { $, el, fields } from "../shared/dom.js";
import { ask } from "../shared/question.js";
import { today } from "../shared/server_time.js";

function pcChip(entry) {
  if (entry.pcShare == null) {
    const beforeRecords = entry.pieces.every((piece) => piece.beforeRecords);
    return beforeRecords ? el("span", { class: "chip" }, "No PC record") : el("span", { class: "chip warn" }, "PC was off");
  }
  if (entry.pcShare >= 0.98) return el("span", { class: "chip live" }, entry.end ? "PC on throughout" : "PC on");
  return el("span", { class: "chip warn" }, `PC on for ${Math.round(entry.pcShare * 100)}%`);
}

function punctualityText(day) {
  if (day.afterShift) {
    return "Started after the shift ended · not counted as late, check the times are right";
  }
  const gap = day.running ? `${hours(day.short)} behind so far` : `${hours(day.short)} short`;
  if (!day.late) return day.running ? gap : `${hours(day.short)} short of a full day`;
  if (day.madeUp) return day.running ? `Late ${hours(day.late)} · made up so far` : `Late ${hours(day.late)} · made up, left ${clockTime(day.lastOut).slice(0, 5)}`;
  return `Late ${hours(day.late)} · ${gap}`;
}

function typedInLate(piece) {
  if (piece.voided || piece.fromPcOn) return false;
  return piece.lateBy != null;
}

function chips(entry, day) {
  const found = [];
  if (entry.label) found.push(el("span", { class: "chip label" }, entry.label));
  if (day) found.push(el("span", { class: `chip ${day.madeUp ? "live" : "warn"}` }, punctualityText(day)));
  if (!entry.end) found.push(el("span", { class: "chip live" }, "Open"));
  if (entry.voided) found.push(el("span", { class: "chip" }, "Marked as a mistake"));
  const enteredLate = entry.pieces.filter(typedInLate);
  if (enteredLate.length) found.push(el("span", { class: "chip warn" }, `Entered ${lateLabel(Math.max(...enteredLate.map((p) => p.lateBy)))} after the fact`));
  if (!entry.voided) found.push(pcChip(entry));
  const corrections = entry.pieces.reduce((sum, piece) => sum + piece.corrections, 0);
  if (corrections) found.push(el("span", { class: "chip" }, corrections === 1 ? "Corrected" : `Corrected ${corrections}×`));
  const waived = waivedMinutes(entry);
  if (waived) found.push(el("span", { class: "chip" }, `Waived ${hours(waived)}`));
  return found;
}

function waivedMinutes(entry) {
  let total = 0;
  for (const waiver of entry.waivers) total += waiver.minutes;
  return total;
}

function waiverItem(waiver) {
  return el("li", { class: "line" },
    el("span", { class: "what" }, "Waived"),
    el("span", { class: "at" }, `${clockTime(waiver.start)} – ${clockTime(waiver.end)}`),
    el("span", { class: "detail" }, waiver.reason),
    el("button", { type: "button", class: "link", onclick: () => countAgain(waiver) }, "Count again"),
  );
}

function waiverList(entry) {
  if (!entry.waivers.length) return null;
  return el("ul", { class: "trail day waivers" }, entry.waivers.map(waiverItem));
}

function lineItem(line) {
  return el("li", { class: "line" },
    el("span", { class: "what" }, line.what),
    el("span", { class: "at" }, line.time),
    el("span", { class: "detail" }, line.detail),
    line.mistake ? el("button", { type: "button", class: "link", onclick: () => markMistake([line.mistake], "This time stops counting") }, "Mark as mistake") : null,
  );
}

function dayTools(entry) {
  if (!entry.ids.length) return null;
  return el("div", { class: "tools day-tools" },
    el("button", { type: "button", class: "link", onclick: () => relabel(entry) }, "Label"),
    entry.end ? el("button", { type: "button", class: "link", onclick: () => correct(entry) }, "Correct") : null,
    el("button", { type: "button", class: "link", onclick: () => waive(entry) }, "Waive time"),
    el("button", { type: "button", class: "link", onclick: () => markMistake(entry.ids, "The whole day stops counting") }, "Mark as mistake"),
  );
}

function entryCard(entry, day) {
  return el("div", { class: `shift ${entry.voided ? "voided" : ""}` },
    el("div", { class: "shift-row" },
      el("span", { class: "when" }, dayLabel(entry.start)),
      el("span", { class: "span" }, `${clockTime(entry.start)} – ${entry.end ? clockTime(entry.end) : "now"}`),
      el("span", { class: "worked" }, hours(entry.worked)),
    ),
    el("div", { class: "chips" }, chips(entry, day)),
    el("details", { class: "explanation" },
      el("summary", {}, "Full explanation"),
      el("ul", { class: "trail day" }, entry.lines.map(lineItem)),
      waiverList(entry),
      dayTools(entry),
    ),
  );
}

async function relabel(entry) {
  const answer = await ask({
    title: "Label",
    text: "Which client or project was this day for? Leave it empty to remove the label.",
    choices: [{ caption: "Save", style: "primary", inputs: [{ name: "label", prompt: "Label", value: entry.label, suggestions: "known-labels" }] }],
  });
  if (answer) act("/api/label", { ids: entry.ids, label: answer.answers.label });
}

async function correct(entry) {
  const answer = await ask({
    title: "Correct the day",
    text: "The corrected time shows on top. The PC and manual clock-in times stay on record underneath.",
    choices: [{ caption: "Save correction", style: "primary", inputs: [
      { name: "start", prompt: "Started", type: "time", value: entry.start.slice(11, 19), required: true },
      { name: "end", prompt: "Finished", type: "time", value: entry.end.slice(11, 19), required: true },
      { name: "reason", prompt: "Reason", required: true },
    ] }],
  });
  if (answer) act("/api/correct", { ids: entry.ids, ...answer.answers });
}

async function waive(entry) {
  const answer = await ask({
    title: "Waive time",
    text: "Stop counting a stretch you were not working, such as after forgetting to clock out. The clocked times stay on record, with the waived stretch and your reason shown beside them.",
    choices: [{ caption: "Waive", style: "primary", inputs: [
      { name: "start", prompt: "Not working from", type: "time", required: true },
      { name: "end", prompt: "Until", type: "time", value: waiveUntil(entry), required: true },
      { name: "reason", prompt: "Reason", required: true },
    ] }],
  });
  if (answer) act("/api/waive", { ids: entry.ids, ...answer.answers });
}

function waiveUntil(entry) {
  if (!entry.end) return "";
  return entry.end.slice(11, 19);
}

async function countAgain(waiver) {
  const answer = await ask({
    title: "Count again",
    text: `${clockTime(waiver.start)} – ${clockTime(waiver.end)} counts as work again. The waiver and this change both stay on record.`,
    choices: [{ caption: "Count again", style: "primary", inputs: [{ name: "reason", prompt: "Reason", required: true }] }],
  });
  if (answer) act("/api/withdraw-waiver", { id: waiver.shift, start: waiver.start, reason: answer.answers.reason });
}

async function markMistake(ids, consequence) {
  const answer = await ask({
    title: "Mark as a mistake",
    text: `${consequence} toward your hours. It stays on the record, with your reason, because nothing in the log is ever deleted.`,
    choices: [{ caption: "Mark as mistake", style: "danger-button", inputs: [{ name: "reason", prompt: "Reason", required: true }] }],
  });
  if (answer) act("/api/mistake", { ids, reason: answer.answers.reason });
}

function byWeek(entries) {
  const groups = new Map();
  for (const entry of entries) {
    const key = weekStart(entry.day);
    if (!groups.has(key)) groups.set(key, []);
    groups.get(key).push(entry);
  }
  return groups;
}

export function render(state) {
  const date = $("#add-form").elements.date;
  if (!date.value) date.value = today();
  const container = $("#shifts");
  if (!state.entries.length) {
    container.replaceChildren(el("div", { class: "card empty" }, "No shifts yet. Clock in above, or add one you missed."));
    return;
  }
  const weeks = new Map(state.weeks.map((week) => [week.start, week]));
  container.replaceChildren(...[...byWeek(state.entries)].map(([start, entries]) => {
    const week = weeks.get(start);
    return el("section", { class: "week" },
      el("div", { class: "week-head" },
        el("h3", {}, `Week of ${longDate(start)}`),
        week ? el("span", { class: "sum" }, el("strong", {}, hours(week.worked)), " worked · ", el("strong", {}, hours(week.overtime)), week.running ? " overtime so far" : " overtime") : null,
      ),
      el("div", { class: "shift-list" }, entries.map((entry) => entryCard(entry, entry.punctuality))),
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
}
