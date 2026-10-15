import { act } from "./actions.js";
import { api } from "./api.js";
import { clockTime, dayLabel, longDate } from "./dates.js";
import { $, el, fields } from "./dom.js";

let kinds = {};

function renderBadge(places) {
  const saving = $("#saving");
  const failed = places.filter((place) => place.error);
  if (!places.length) {
    saving.className = "badge bad";
    saving.textContent = "Only on this computer";
  } else if (failed.length) {
    saving.className = "badge warn";
    saving.textContent = `Not saved to ${failed.map((place) => place.name).join(", ")}`;
    saving.title = failed.map((place) => `${place.name}: ${place.error}`).join("\n");
  } else {
    saving.className = "badge ok";
    saving.textContent = places.length === 1 ? `Saved to ${places[0].name}` : `Saved to ${places.length} places`;
    saving.title = "";
  }
}

function placeCard(place) {
  return el("div", { class: "card place" },
    el("div", {},
      el("h3", {}, `${place.name} · ${place.kindLabel}`),
      el("div", { class: "where" }, place.target),
      el("div", { class: `state ${place.error ? "bad" : "good"}` },
        place.error ? `Last save failed: ${place.error}` : place.saved ? `Saved ${dayLabel(place.saved)}, ${clockTime(place.saved)}` : "Not saved yet"),
    ),
    el("button", { type: "button", class: "link", onclick: () => {
      if (confirm(`Stop saving to ${place.name}? Copies already there are left alone.`)) act("/api/places/remove", { id: place.id });
    } }, "Remove"),
  );
}

function describeKind() {
  const kind = kinds[$("#place-kind").value];
  if (!kind) return;
  $("#target-label").textContent = kind.asksFor;
  $("#place-form").elements.target.placeholder = kind.example;
  $("#choose-folder").hidden = !kind.onThisComputer;
  $("#place-hint").textContent = kind.explanation;
  document.querySelectorAll(".needs-login").forEach((node) => (node.hidden = !kind.needsLogin));
  document.querySelectorAll(".needs-folder").forEach((node) => (node.hidden = !kind.needsFolder));
}

export function render(state) {
  const { places, stamped } = state.saving;
  kinds = state.saving.kinds;
  renderBadge(places);
  const select = $("#place-kind");
  if (!select.options.length) {
    select.append(...Object.entries(kinds).map(([kind, described]) => el("option", { value: kind }, described.label)));
    describeKind();
  }
  $("#stamp-text").textContent = stamped.upTo
    ? `Everything up to entry ${stamped.upTo} was timestamped by ${stamped.by.map((s) => `${s.authority} at ${s.time.slice(11, 19)} UTC on ${longDate(s.time)}`).join(" and ")}. These are signed receipts from outside organisations, so the times don't depend on this computer's clock.`
    : "Nothing timestamped yet. The next save asks DigiCert and FreeTSA for signed receipts of the log.";
  $("#places").replaceChildren(...places.map(placeCard));
}

export function wire() {
  $("#save-button").addEventListener("click", (event) => act("/api/save", {}, event.target.parentElement));
  $("#place-kind").addEventListener("change", describeKind);
  $("#choose-folder").addEventListener("click", async () => {
    const { path } = await api("/api/choose-folder", {});
    if (path) $("#place-form").elements.target.value = path;
  });
  $("#place-form").addEventListener("submit", async (event) => {
    event.preventDefault();
    if (await act("/api/places/add", fields(event.target), event.target)) {
      event.target.reset();
      describeKind();
    }
  });
}
