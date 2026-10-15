import { api } from "./api.js";
import { ask } from "./question.js";
import { toast } from "./toast.js";

let afterChange = async () => {};

export function whenChanged(refresh) {
  afterChange = refresh;
}

function answered(body, answer) {
  const field = "to" in body ? "to" : "label";
  const relabelled = answer.label === null ? {} : { [field]: answer.label };
  return { ...body, ...relabelled, answers: { ...(body.answers || {}), ...answer.answers } };
}

async function answerAndRetry(path, body, form, question) {
  const answer = await ask(question);
  return answer ? act(path, answered(body, answer), form) : false;
}

export async function act(path, body, form) {
  const buttons = form ? form.querySelectorAll("button") : [];
  buttons.forEach((button) => (button.disabled = true));
  try {
    const outcome = await api(path, body);
    toast(outcome.warning ? `${outcome.message}. ${outcome.warning}` : outcome.message, outcome.warning ? "warn" : "");
    await afterChange();
    return true;
  } catch (error) {
    buttons.forEach((button) => (button.disabled = false));
    if (error.payload?.question) return answerAndRetry(path, body, form, error.payload.question);
    toast(error.message, "bad");
    return false;
  } finally {
    buttons.forEach((button) => (button.disabled = false));
  }
}
