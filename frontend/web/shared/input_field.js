import { el } from "./dom.js";

export function inputField(input) {
  return el("label", { class: "wide" }, input.prompt,
    el("input", { name: input.name, type: input.type || "text", step: input.type ? "1" : null, min: input.type === "number" ? "1" : null,
      autocomplete: "off", list: input.suggestions || null, value: input.value || null,
      placeholder: input.example ? `e.g. ${input.example}` : null, required: Boolean(input.required) }));
}
