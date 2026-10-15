import { act } from "./actions.js";
import { clockTime, dayLabel, hours, lateLabel, longDate, weekStart } from "./dates.js";
import { $, el, fields } from "./dom.js";
import { today } from "./server_time.js";

function proofLine(piece) {
  const { fromPcOn, entry, stamps } = piece.proof;
  const source = fromPcOn ? `Started when the PC came on at ${clockTime(piece.start)}` : `Start logged in entry ${entry}`;
  const by = stamps.map((s) => `${s.authority} ${s.time.slice(0, 10) === piece.start.slice(0, 10) ? clockTime(s.time) : `${dayLabel(s.time)} ${clockTime(s.time)}`}`);
  return el("li", { class: "proof" },
    stamps.length ? `${source} · independently timestamped by ${by.join(", ")}` : `${source} · not yet independently timestamped`);
}

function pcChip(entry) {
  if (entry.pcShare == null) {
    const beforeRecords = entry.pieces.every((piece) => piece.pc.beforeRecords);
    return beforeRecords ? el("span", { class: "chip" }, "No PC record") : el("span", { class: "chip warn" }, "PC was off");
  }
  if (entry.pcShare >= 0.98) return el("span", { class: "chip live" }, entry.end ? "PC on throughout" : "PC on");
  return el("span", { class: "chip warn" }, `PC on for ${Math.round(entry.pcShare * 100)}%`);
}

function chips(entry, day) {
  const found = [];
  if (entry.label) found.push(el("span", { class: "chip label" }, entry.label));
  if (day) found.push(el("span", { class: `chip ${day.madeUp ? "live" : "warn"}` },
    !day.late ? `${hours(day.short)} short of a full day`
      : day.madeUp ? `Late ${hours(day.late)} · made up, left ${clockTime(day.lastOut).slice(0, 5)}`
      : `Late ${hours(day.late)} · ${hours(day.short)} short`));
  if (!entry.end) found.push(el("span", { class: "chip live" }, "Open"));
  if (entry.voided) found.push(el("span", { class: "chip" }, "Struck out"));
  const enteredLate = entry.pieces.filter((piece) => piece.lateBy != null && !piece.proof.fromPcOn);
  if (enteredLate.length) found.push(el("span", { class: "chip warn" }, `Entered ${lateLabel(Math.max(...enteredLate.map((p) => p.lateBy)))} after the fact`));
  found.push(pcChip(entry));
  const corrections = entry.pieces.flatMap((piece) => piece.changes).filter((change) => change.includes(" changed ")).length;
  if (corrections) found.push(el("span", { class: "chip" }, corrections === 1 ? "Corrected" : `Corrected ${corrections}×`));
  return found;
}

function tools(piece) {
  if (piece.voided) return null;
  const labelButton = el("button", { type: "button", class: "link", onclick: () => {
    const label = prompt("Client or project for this part of the day (leave empty to remove)", piece.label);
    if (label !== null) act("/api/label", { id: piece.id, label });
  } }, "Label");
  return el("span", { class: "tools" },
    labelButton,
    piece.end ? el("button", { type: "button", class: "link", onclick: () => openCorrect(piece) }, "Correct") : null,
    piece.end ? el("button", { type: "button", class: "link", onclick: () => openStrike(piece) }, "Strike out") : null,
  );
}

function pieceBlock(piece) {
  const span = `${clockTime(piece.start)} – ${piece.end ? `${clockTime(piece.end)} (${hours(piece.worked)})` : "now"}`;
  const lateNote = piece.lateBy == null ? null
    : el("li", {}, piece.proof.fromPcOn ? "Written down later, from the PC-on time" : `Entered ${lateLabel(piece.lateBy)} after the fact`);
  const pcLines = piece.pc.sessions.map((s) => el("li", {}, `PC on ${dayLabel(s.on)} ${clockTime(s.on).slice(0, 5)} – ${s.off ? `${dayLabel(s.off)} ${clockTime(s.off).slice(0, 5)}` : "still on"}${s.off ? (s.exact ? ", at shutdown" : ", last activity") : ""}`));
  return el("div", { class: `piece ${piece.voided ? "voided" : ""}` },
    el("div", { class: "piece-head" }, el("span", {}, `Shift ${piece.id} · ${span}`), tools(piece)),
    el("ul", { class: "trail" },
      proofLine(piece),
      lateNote,
      ...piece.notes.map((note) => el("li", { class: "note" }, note)),
      ...pcLines,
      ...piece.changes.map((change) => el("li", {}, change)),
    ),
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
      ...entry.pieces.map(pieceBlock),
    ),
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
  for (const [formId, dialogId, path] of [["#correct-form", "#correct-dialog", "/api/correct"], ["#strike-form", "#strike-dialog", "/api/strike"]]) {
    $(formId).addEventListener("submit", async (event) => {
      event.preventDefault();
      if (await act(path, fields(event.target), event.target)) $(dialogId).close();
    });
  }
}
