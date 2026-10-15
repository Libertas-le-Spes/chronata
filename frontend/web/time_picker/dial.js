import { svg } from "../shared/dom.js";

const SIZE = 256;
const CENTRE = SIZE / 2;
const OUTER = 104;
const INNER = 68;
const BETWEEN_RINGS = (OUTER + INNER) / 2;
const KNOB = 18;

const pad = (number) => String(number).padStart(2, "0");

function point(step, steps, radius) {
  const angle = (step / steps) * 2 * Math.PI;
  return { x: CENTRE + radius * Math.sin(angle), y: CENTRE - radius * Math.cos(angle) };
}

function stepAt(dx, dy, steps) {
  const turn = (Math.atan2(dx, -dy) + 2 * Math.PI) % (2 * Math.PI);
  return Math.round((turn / (2 * Math.PI)) * steps) % steps;
}

export const HOURS = {
  label: "hour",
  max: 23,
  marks: [...Array(24).keys()].map((hour) => ({ value: hour, text: String(hour) })),
  place: (hour) => point(hour % 12, 12, hour < 12 ? OUTER : INNER),
  pick: (dx, dy) => stepAt(dx, dy, 12) + (Math.hypot(dx, dy) < BETWEEN_RINGS ? 12 : 0),
};

export const MINUTES = {
  label: "minute",
  max: 59,
  marks: [...Array(12).keys()].map((step) => ({ value: step * 5, text: pad(step * 5) })),
  place: (minute) => point(minute, 60, OUTER),
  pick: (dx, dy) => stepAt(dx, dy, 60),
};

function face(unit, value) {
  const knob = unit.place(value);
  const onMark = unit.marks.some((mark) => mark.value === value);
  return [
    svg("circle", { class: "face", cx: CENTRE, cy: CENTRE, r: SIZE / 2 - 4 }),
    svg("line", { class: "hand", x1: CENTRE, y1: CENTRE, x2: knob.x, y2: knob.y }),
    svg("circle", { class: "hand-dot", cx: CENTRE, cy: CENTRE, r: 4 }),
    svg("circle", { class: "knob", cx: knob.x, cy: knob.y, r: KNOB }),
    onMark ? null : svg("circle", { class: "knob-dot", cx: knob.x, cy: knob.y, r: 3 }),
    ...unit.marks.map((mark) => {
      const at = unit.place(mark.value);
      return svg("text", { class: mark.value === value ? "mark chosen" : "mark", x: at.x, y: at.y }, mark.text);
    }),
  ].filter(Boolean);
}

class Dial {
  constructor({ onChange, onSettle }) {
    this.onChange = onChange;
    this.onSettle = onSettle;
    this.unit = HOURS;
    this.value = 0;
    this.dragging = false;
    this.node = svg("svg", { class: "dial", viewBox: `0 0 ${SIZE} ${SIZE}`, tabindex: "0", role: "slider" });
    this.node.addEventListener("pointerdown", (event) => this.press(event));
    this.node.addEventListener("pointermove", (event) => this.dragging && this.follow(event));
    this.node.addEventListener("pointerup", () => this.release());
    this.node.addEventListener("keydown", (event) => this.step(event));
  }

  show(unit, value) {
    this.unit = unit;
    this.value = value;
    this.draw();
  }

  draw() {
    this.node.replaceChildren(...face(this.unit, this.value));
    this.node.setAttribute("aria-label", `Choose the ${this.unit.label}`);
    this.node.setAttribute("aria-valuenow", this.value);
    this.node.setAttribute("aria-valuemax", this.unit.max);
  }

  choose(value) {
    this.value = value;
    this.draw();
    this.onChange(this.unit, value);
  }

  press(event) {
    this.dragging = true;
    this.node.setPointerCapture(event.pointerId);
    this.follow(event);
  }

  follow(event) {
    const box = this.node.getBoundingClientRect();
    const scale = SIZE / box.width;
    this.choose(this.unit.pick((event.clientX - box.left) * scale - CENTRE, (event.clientY - box.top) * scale - CENTRE));
  }

  release() {
    this.dragging = false;
    this.onSettle(this.unit);
  }

  step(event) {
    const step = { ArrowUp: 1, ArrowRight: 1, ArrowDown: -1, ArrowLeft: -1 }[event.key];
    if (!step) return;
    event.preventDefault();
    const count = this.unit.max + 1;
    this.choose((this.value + step + count) % count);
  }
}

export function dial(handlers) {
  return new Dial(handlers);
}
