import { el, svg } from "../shared/dom.js";
import { now } from "../shared/server_time.js";
import { HOURS, MINUTES, dial } from "./dial.js";

const pad = (number) => String(number).padStart(2, "0");
const PARTS = { hour: 23, minute: 59, second: 59 };

function parsed(value) {
  const [hour, minute, second = 0] = (value || "").split(":").map(Number);
  if (Number.isInteger(hour) && Number.isInteger(minute)) return { hour, minute, second };
  const current = now();
  return { hour: current.getHours(), minute: current.getMinutes(), second: 0 };
}

function withinRange(text, max) {
  const number = Number(text);
  if (!Number.isInteger(number)) return null;
  return number >= 0 && number <= max ? number : null;
}

function keyboardIcon() {
  const keys = [0, 1, 2, 3].flatMap((column) => [0, 1].map((row) => svg("rect", { x: 5 + column * 4, y: 8 + row * 4, width: 2, height: 2 })));
  return svg("svg", { viewBox: "0 0 24 24", width: 22, height: 22, "aria-hidden": "true" },
    svg("rect", { x: 2, y: 5, width: 20, height: 14, rx: 2, fill: "none", stroke: "currentColor", "stroke-width": 1.6 }),
    ...keys, svg("rect", { x: 7, y: 16, width: 10, height: 1.6 }));
}

class TimePicker {
  constructor() {
    this.time = { hour: 0, minute: 0, second: 0 };
    this.face = dial({ onChange: (unit, value) => this.dialled(unit, value), onSettle: (unit) => unit === HOURS && this.showUnit(MINUTES) });
    this.title = el("p", { class: "picker-title" });
    this.hour = el("button", { type: "button", class: "part", onclick: () => this.showDial(HOURS) });
    this.minute = el("button", { type: "button", class: "part", onclick: () => this.showDial(MINUTES) });
    this.seconds = el("span", { class: "seconds" });
    this.typed = Object.fromEntries(Object.keys(PARTS).map((name) => [name, this.typedInput(name)]));
    this.typedArea = el("div", { class: "typed" }, ...Object.entries(this.typed).map(([name, input]) => el("label", {}, name[0].toUpperCase() + name.slice(1), input)));
    this.toggle = el("button", { type: "button", class: "icon-button", onclick: () => this.showTyping(!this.typing) }, keyboardIcon());
    this.clear = el("button", { type: "button", class: "link", onclick: () => this.answer("") }, "Clear");
    this.dialog = this.layout();
    document.body.append(this.dialog);
  }

  layout() {
    return el("dialog", { class: "time-picker" },
      el("form", { method: "dialog" },
        this.title,
        el("div", { class: "readout" }, this.hour, el("span", { class: "colon" }, ":"), this.minute, this.seconds),
        this.face.node, this.typedArea,
        el("div", { class: "picker-actions" }, this.toggle, el("span", { class: "spacer" }), this.clear,
          el("button", { type: "button", class: "link", onclick: () => this.dialog.close() }, "Cancel"),
          el("button", { type: "button", class: "primary", onclick: () => this.answer(this.written()) }, "OK"))));
  }

  typedInput(name) {
    const input = el("input", { type: "number", min: 0, max: PARTS[name], inputmode: "numeric", name });
    input.addEventListener("input", () => {
      const number = withinRange(input.value, PARTS[name]);
      if (number !== null) this.set(name, number);
    });
    input.addEventListener("keydown", (event) => {
      if (event.key !== "Enter") return;
      event.preventDefault();
      this.answer(this.written());
    });
    return input;
  }

  written() {
    return `${pad(this.time.hour)}:${pad(this.time.minute)}:${pad(this.time.second)}`;
  }

  set(name, value) {
    this.time[name] = value;
    this.hour.textContent = pad(this.time.hour);
    this.minute.textContent = pad(this.time.minute);
    this.seconds.textContent = this.time.second ? `:${pad(this.time.second)}` : "";
    for (const [part, input] of Object.entries(this.typed)) if (document.activeElement !== input) input.value = pad(this.time[part]);
  }

  dialled(unit, value) {
    this.set(unit.label, value);
    this.set("second", 0);
  }

  showUnit(unit) {
    this.hour.classList.toggle("chosen", unit === HOURS);
    this.minute.classList.toggle("chosen", unit === MINUTES);
    this.face.show(unit, this.time[unit.label]);
  }

  showDial(unit) {
    this.showTyping(false);
    this.showUnit(unit);
  }

  showTyping(on) {
    this.typing = on;
    this.face.node.toggleAttribute("hidden", on);
    this.typedArea.hidden = !on;
    const label = on ? "Use the dial" : "Type the time";
    this.toggle.setAttribute("aria-label", label);
    this.toggle.title = label;
    (on ? this.typed.hour : this.face.node).focus();
  }

  answer(value) {
    this.answered = value;
    this.dialog.close();
  }

  open(value, { label, clearable }) {
    return new Promise((resolve) => {
      this.answered = null;
      this.title.textContent = label || "Select time";
      this.clear.hidden = !clearable;
      Object.entries(parsed(value)).forEach(([name, part]) => this.set(name, part));
      this.dialog.onclose = () => resolve(this.answered);
      this.dialog.showModal();
      this.showDial(HOURS);
    });
  }
}

let picker = null;

export function pickTime(value, options = {}) {
  picker = picker || new TimePicker();
  return picker.open(value, options);
}
