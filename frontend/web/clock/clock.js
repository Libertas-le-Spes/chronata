import { act } from "../shared/actions.js";
import { clockTime, dayLabel, hours } from "../shared/dates.js";
import { $, fields } from "../shared/dom.js";
import { ask } from "../shared/question.js";
import { now, secondsSinceSync } from "../shared/server_time.js";

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
  earlyOut = clockedIn() && state.beforeEndOfWorkday ? state.shiftEnd : null;
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

export async function askBeforeClockingOut(note = "") {
  if (!earlyOut) return;
  const time = now();
  const answer = await ask({
    title: "Clock out now?",
    text: `It's ${String(time.getHours()).padStart(2, "0")}:${String(time.getMinutes()).padStart(2, "0")}, before your ${earlyOut} finish. Clocking out now ends today's work unless you clock back in, and any time away isn't counted.`,
    cancel: "No, keep working",
    choices: [{ caption: "Yes, clock out", style: "primary",
      inputs: [{ name: "note", prompt: "Why, if you'd like it on record", example: "doctor's appointment, back at 15:00", value: note }] }],
  });
  if (answer && await act("/api/out", { note: answer.answers.note }, null)) $("#clock-form").reset();
}

async function askWhenStarted() {
  if (!unclockedSince) return {};
  const since = clockTime(unclockedSince).slice(0, 5);
  const ago = hours(Math.round((now().getTime() - Date.parse(unclockedSince)) / 60000));
  const answer = await ask({
    title: "Since when?",
    text: `Have you been working since the PC came on at ${since} (${ago} ago), or are you starting now?`,
    choices: [
      { caption: `Since ${since}`, answers: { at: unclockedSince, note: "started when the PC came on" } },
      { caption: "From now", style: "primary", answers: {} },
    ],
  });
  return answer && answer.answers;
}

async function clockIn(form, { note, at, label }) {
  const start = at ? {} : await askWhenStarted();
  if (!start) return false;
  const noted = [note, start.note].filter(Boolean).join("; ");
  return act("/api/in", { note: noted, at: at || start.at || null, label }, form);
}

function clockOut(form, { note, at }) {
  if (earlyOut && !at) return askBeforeClockingOut(note);
  return act("/api/out", { note, at: at || (interrupted && interrupted.pcWentOff) || null }, form);
}

export function focusLabel() {
  const labelInput = $("#clock-form").elements.label;
  if (!labelInput.hidden) { labelInput.focus(); labelInput.select(); }
}

export function wire() {
  $("#clock-form").addEventListener("submit", async (event) => {
    event.preventDefault();
    const form = event.target;
    const done = await (current ? clockOut : clockIn)(form, fields(form));
    if (done) {
      form.reset();
      form.querySelector("details").open = false;
    }
  });
  setInterval(tick, 1000);
}
