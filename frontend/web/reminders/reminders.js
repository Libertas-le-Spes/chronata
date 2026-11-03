import { act } from "../shared/actions.js";
import { $ } from "../shared/dom.js";
import { ask } from "../shared/question.js";

let every = null;

function currently() {
  if (every === null) return "Clock-out reminders are off.";
  return `Once your shift has ended you're reminded to clock out every ${every} minutes, and every hour on a day off.`;
}

function minutesShown() {
  if (every === null) return "30";
  return String(every);
}

async function changeReminders() {
  const answer = await ask({
    title: "Clock-out reminders",
    text: `${currently()} Choose how often, from 5 to 240 minutes, or turn them off.`,
    choices: [
      { caption: "Turn off", answers: { off: true } },
      { caption: "Save", style: "primary", inputs: [{ name: "every", prompt: "Minutes between reminders", type: "number", value: minutesShown(), required: true }] },
    ],
  });
  if (!answer) return;
  if (answer.answers.off) {
    act("/api/reminders", { off: true });
    return;
  }
  act("/api/reminders", { every: Number(answer.answers.every) });
}

export function render(state) {
  every = state.reminders.clockOutEvery;
}

export function wire() {
  $("#reminders-button").addEventListener("click", changeReminders);
}
