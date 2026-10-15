import { api } from "./api.js";
import { askAboutNewLabel, askAboutOffDefault } from "./choices.js";
import { toast } from "./toast.js";

let afterChange = async () => {};

export function whenChanged(refresh) {
  afterChange = refresh;
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
    if (error.status === 409 && (error.payload.nearMisses || error.payload.offDefault)) {
      buttons.forEach((button) => (button.disabled = false));
      const field = "label" in body ? "label" : "to";
      const change = error.payload.offDefault ? await askAboutOffDefault(error.payload) : await askAboutNewLabel(error.payload, field);
      if (!change) return false;
      return act(path, { ...body, ...change }, form);
    }
    toast(error.message, "bad");
    return false;
  } finally {
    buttons.forEach((button) => (button.disabled = false));
  }
}
