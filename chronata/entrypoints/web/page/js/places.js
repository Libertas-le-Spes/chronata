import { act } from "./actions.js";
import { api } from "./api.js";
import { clockTime, dayLabel, longDate } from "./dates.js";
import { $, el, fields } from "./dom.js";

const PLACE_HELP = {
  obsidian: ["Vault folder", "/home/you/Notes", true, "Goes into a Chronata folder inside the vault: an overview, the whole log in one note, a note per day, and the sealed log."],
  folder: ["Folder", "/home/you/Documents/Time", true, "Gets an overview, the whole log in one file, a file per day, and the sealed log. A Dropbox, OneDrive or Syncthing folder works too."],
  git: ["Repository address", "https://github.com/you/time-log.git", false, "Create an empty private repository first. Git hosts record when each save arrives."],
  "git-folder": ["Repository address", "https://github.com/you/notes.git", false, "Saves into one folder of a repository you already use, such as your notes. Only that folder is ever changed, and a folder Chronata did not create is left alone."],
  webdav: ["Server address", "https://cloud.example.com/remote.php/dav/files/you/", false, "Nextcloud, ownCloud and most file servers speak WebDAV. The password is kept only on this computer."],
};

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
  const [label, placeholder, local, hint] = PLACE_HELP[$("#place-kind").value];
  $("#target-label").textContent = label;
  $("#place-form").elements.target.placeholder = placeholder;
  $("#choose-folder").hidden = !local;
  $("#place-hint").textContent = hint;
  document.querySelectorAll(".dav-only").forEach((node) => (node.hidden = $("#place-kind").value !== "webdav"));
  document.querySelectorAll(".folder-only").forEach((node) => (node.hidden = $("#place-kind").value !== "git-folder"));
}

export function render(state) {
  const { places, kinds, stamped } = state.saving;
  renderBadge(places);
  const select = $("#place-kind");
  if (!select.options.length) {
    select.append(...Object.entries(kinds).map(([kind, label]) => el("option", { value: kind }, label)));
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
