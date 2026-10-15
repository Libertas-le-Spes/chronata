import { pickTime } from "./time_picker.js";

const OPENS = new Set(["Enter", " ", "ArrowDown"]);

function labelOf(input) {
  const label = input.closest("label");
  return label ? label.firstChild.textContent.trim() : "";
}

async function choose(input) {
  const picked = await pickTime(input.value, { label: labelOf(input), clearable: !input.required });
  if (picked === null) return;
  input.value = picked;
  input.dispatchEvent(new Event("input", { bubbles: true }));
  input.dispatchEvent(new Event("change", { bubbles: true }));
}

export function timeField(input) {
  input.type = "text";
  input.removeAttribute("step");
  input.setAttribute("inputmode", "none");
  input.setAttribute("autocomplete", "off");
  input.placeholder = "--:--";
  input.classList.add("time-field");
  input.addEventListener("click", () => choose(input));
  input.addEventListener("beforeinput", (event) => event.preventDefault());
  input.addEventListener("keydown", (event) => {
    if (!OPENS.has(event.key)) return;
    event.preventDefault();
    choose(input);
  });
  return input;
}

export function timeFields(root) {
  root.querySelectorAll('input[type="time"]').forEach(timeField);
}
