import { $, el } from "./dom.js";

function field(input) {
  return el("label", { class: "wide" }, input.prompt,
    el("input", { name: input.name, type: input.type || "text", step: input.type ? "1" : null, autocomplete: "off", list: input.suggestions || null,
      placeholder: input.example ? `e.g. ${input.example}` : null, required: Boolean(input.required) }));
}

function inputsOf(choices) {
  const byName = new Map(choices.flatMap((choice) => choice.inputs || []).map((input) => [input.name, input]));
  return [...byName.values()];
}

function filledIn(form, choice) {
  const inputs = (choice.inputs || []).map((input) => form.elements[input.name]);
  const missing = inputs.find((input) => !input.checkValidity());
  if (missing) {
    missing.reportValidity();
    return null;
  }
  return Object.fromEntries(inputs.map((input) => [input.name, input.value]));
}

export function ask(question) {
  return new Promise((resolve) => {
    const dialog = $("#question");
    const form = dialog.querySelector("form");
    let answer = null;
    $("#question-title").textContent = question.title || "Just to check";
    $("#question-text").textContent = question.text;
    $("#question-inputs").replaceChildren(...inputsOf(question.choices).map(field));
    for (const input of inputsOf(question.choices)) form.elements[input.name].value = input.value ?? "";
    const choose = (choice) => () => {
      const typed = filledIn(form, choice);
      if (typed === null) return;
      answer = { label: choice.label ?? null, answers: { ...(choice.answers || {}), ...typed } };
      dialog.close();
    };
    $("#question-buttons").replaceChildren(
      el("button", { type: "button", onclick: () => dialog.close() }, question.cancel || "Cancel"),
      ...question.choices.map((choice) => el("button", { type: "button", class: choice.style || null, onclick: choose(choice) }, choice.caption)),
    );
    dialog.onclose = () => resolve(answer);
    dialog.showModal();
    form.querySelector("input")?.focus();
  });
}
