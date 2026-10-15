import { act } from "./actions.js";
import { askWhenStarted } from "./choices.js";
import { clockTime, dayLabel, hours } from "./dates.js";
import { $, fields } from "./dom.js";
import { now, secondsSinceSync } from "./server_time.js";

let current = null;
let interrupted = null;
let earlyOut = null;
let unclockedSince = null;

export function clockedIn() {
  return Boolean(current) && !interrupted;
}

export function shiftOpen() {
  return Boolean(current);
}

export function render(state) {
  current = state.open;
  interrupted = state.interrupted;
  earlyOut = current && !interrupted && state.beforeEndOfWorkday ? state.shiftEnd : null;
  unclockedSince = state.unclockedSince;
  $(".clock").classList.toggle("live", clockedIn());
  $(".clock").classList.toggle("interrupted", Boolean(interrupted));
  if (interrupted) {
    const off = interrupted.pcWentOff;
    $("#clock-state").textContent = off
      ? `Still clocked in from ${dayLabel(interrupted.start)}, ${clockTime(interrupted.start)}. The PC's last activity before it turned off was ${dayLabel(off)}, ${clockTime(off)}.`
      : `Still clocked in from ${dayLabel(interrupted.start)}, ${clockTime(interrupted.start)}, before the PC last turned off.`;
    $("#clock-button").textContent = off ? `Clock out at ${dayLabel(off)}, ${clockTime(off).slice(0, 5)}` : "Clock out now";
  } else {
    const onLabel = current && current.label ? ` on ${current.label}` : "";
    $("#clock-state").textContent = current ? `Clocked in${onLabel} · working since ${dayLabel(current.dayStart)}, ${clockTime(current.dayStart)}` : "Not clocked in";
    $("#clock-button").textContent = current ? "Clock out" : "Clock in";
  }
  const week = state.weeks.find((w) => w.running);
  const parts = [week ? `This week: ${hours(week.worked)} worked, ${hours(week.overtime)} overtime` : "Nothing logged this week yet"];
  if (state.pcOnSince) parts.push(`PC on since ${dayLabel(state.pcOnSince)}, ${clockTime(state.pcOnSince).slice(0, 5)}`);
  $("#this-week").textContent = parts.join(" · ");
  tick();
}

export function tick() {
  if (!current || interrupted) {
    $("#timer").textContent = interrupted ? "–:––:––" : "0:00:00";
    return;
  }
  const seconds = Math.max(0, Math.floor(current.workedSeconds + secondsSinceSync()));
  const h = Math.floor(seconds / 3600);
  const m = Math.floor((seconds % 3600) / 60);
  const s = seconds % 60;
  $("#timer").textContent = `${h}:${String(m).padStart(2, "0")}:${String(s).padStart(2, "0")}`;
}

export function askBeforeClockingOut(note = "") {
  if (!earlyOut) return;
  const time = now();
  $("#out-question").textContent = `It's ${String(time.getHours()).padStart(2, "0")}:${String(time.getMinutes()).padStart(2, "0")}, before your ${earlyOut} finish. Clocking out now ends today's work unless you clock back in, and any time away isn't counted.`;
  $("#out-form").elements.note.value = note;
  $("#out-dialog").showModal();
}

export function focusLabel() {
  const labelInput = $("#clock-form").elements.label;
  if (!labelInput.hidden) { labelInput.focus(); labelInput.select(); }
}

export function wire() {
  $("#clock-form").addEventListener("submit", async (event) => {
    event.preventDefault();
    const form = event.target;
    const { note, at, label } = fields(form);
    if (current && earlyOut && !at) return askBeforeClockingOut(note);
    const start = current || at ? {} : await askWhenStarted(unclockedSince);
    if (!start) return;
    const when = at || start.at || (interrupted && interrupted.pcWentOff) || null;
    const noted = [note, start.note].filter(Boolean).join("; ");
    if (await act(current ? "/api/out" : "/api/in", { note: noted, at: when, label }, form)) {
      form.reset();
      form.querySelector("details").open = false;
    }
  });
  $("#out-form").addEventListener("submit", async (event) => {
    event.preventDefault();
    if (await act("/api/out", { note: fields(event.target).note }, event.target)) {
      $("#out-dialog").close();
      $("#clock-form").reset();
    }
  });
  setInterval(tick, 1000);
}
