import { $, el } from "./dom.js";
import { clockTime, hours } from "./dates.js";
import { now } from "./server_time.js";

export function askChoice(title, text, choices) {
  return new Promise((resolve) => {
    const dialog = $("#choice-dialog");
    $("#choice-title").textContent = title;
    $("#choice-text").textContent = text;
    const choose = (answer) => () => { dialog.close(); resolve(answer); };
    $("#choice-buttons").replaceChildren(
      el("button", { type: "button", onclick: choose(null) }, "Cancel"),
      ...choices.map(([caption, change, style]) => el("button", { type: "button", class: style, onclick: choose(change) }, caption)),
    );
    dialog.showModal();
  });
}

export function askAboutNewLabel({ label, nearMisses }, field) {
  return askChoice("New label?", `“${label}” would start a new label, with its own folder. Did you mean ${nearMisses.map((m) => `“${m}”`).join(" or ")}?`, [
    [`Create “${label}”`, { newLabel: true }],
    ...nearMisses.map((miss) => [`Use “${miss}”`, { [field]: miss }, "primary"]),
  ]);
}

export function askAboutOffDefault({ label, defaultLabel }) {
  const chosen = label ? `Clock in on “${label}”` : "Clock in with no label";
  return askChoice("Not your default?", `Today is a workday, and “${defaultLabel}” is your default. ${chosen} instead?`, [
    [chosen, { offDefault: true }],
    [`Use “${defaultLabel}”`, { label: defaultLabel }, "primary"],
  ]);
}

export function askWhenStarted(pcOn) {
  if (!pcOn) return Promise.resolve({});
  const since = clockTime(pcOn).slice(0, 5);
  const ago = hours(Math.round((now().getTime() - Date.parse(pcOn)) / 60000));
  return askChoice("Since when?", `Have you been working since the PC came on at ${since} (${ago} ago), or are you starting now?`, [
    [`Since ${since}`, { at: pcOn, note: "started when the PC came on" }],
    ["From now", {}, "primary"],
  ]);
}
