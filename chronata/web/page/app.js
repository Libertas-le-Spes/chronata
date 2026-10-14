const token = document.querySelector('meta[name="token"]').content;
const $ = (selector) => document.querySelector(selector);
const DAY = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"];
const MONTH = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];
const DAY_NAME = { mon: "Mon", tue: "Tue", wed: "Wed", thu: "Thu", fri: "Fri", sat: "Sat", sun: "Sun" };

let current = null;
let interrupted = null;
let lunch = { start: "12:00", minutes: 60 };
let clockSkew = 0;

function el(tag, attributes = {}, ...children) {
  const node = document.createElement(tag);
  for (const [key, value] of Object.entries(attributes)) {
    if (value === false || value == null) continue;
    if (key.startsWith("on")) node.addEventListener(key.slice(2), value);
    else node.setAttribute(key, value === true ? "" : value);
  }
  node.append(...children.flat().filter((child) => child != null && child !== false));
  return node;
}

function hours(minutes) {
  const sign = minutes < 0 ? "-" : "";
  const total = Math.abs(minutes);
  return `${sign}${Math.floor(total / 60)}:${String(total % 60).padStart(2, "0")}`;
}

function localDate(iso) {
  const [y, m, d] = iso.slice(0, 10).split("-").map(Number);
  return new Date(y, m - 1, d);
}

function dayLabel(iso) {
  const date = localDate(iso);
  return `${DAY[date.getDay()]} ${date.getDate()} ${MONTH[date.getMonth()]}`;
}

function longDate(iso) {
  const date = localDate(iso);
  return `${date.getDate()} ${MONTH[date.getMonth()]} ${date.getFullYear()}`;
}

function clockTime(iso) {
  return iso.slice(11, 19);
}

function weekStart(iso) {
  const date = localDate(iso);
  date.setDate(date.getDate() - ((date.getDay() + 6) % 7));
  return `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, "0")}-${String(date.getDate()).padStart(2, "0")}`;
}

function lateLabel(minutes) {
  return minutes >= 1440 ? `${Math.floor(minutes / 1440)}d ${Math.floor((minutes % 1440) / 60)}h` : hours(minutes);
}

async function api(path, body) {
  const response = await fetch(path, {
    method: body === undefined ? "GET" : "POST",
    headers: { "X-Token": token, "Content-Type": "application/json" },
    body: body === undefined ? undefined : JSON.stringify(body),
  });
  const payload = await response.json();
  if (!response.ok) throw new Error(payload.error || `request failed (${response.status})`);
  return payload;
}

let toastTimer;
function toast(text, tone = "") {
  const node = $("#toast");
  node.textContent = text;
  node.className = `toast ${tone}`;
  node.hidden = false;
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => (node.hidden = true), tone ? 9000 : 4000);
}

async function act(path, body, form) {
  const buttons = form ? form.querySelectorAll("button") : [];
  buttons.forEach((button) => (button.disabled = true));
  try {
    const outcome = await api(path, body);
    toast(outcome.warning ? `${outcome.message}. ${outcome.warning}` : outcome.message, outcome.warning ? "warn" : "");
    await refresh();
    return true;
  } catch (error) {
    toast(error.message, "bad");
    return false;
  } finally {
    buttons.forEach((button) => (button.disabled = false));
  }
}

function fields(form) {
  return Object.fromEntries(new FormData(form).entries());
}

function renderClock(state) {
  current = state.open;
  interrupted = state.interrupted;
  $(".clock").classList.toggle("live", Boolean(current) && !interrupted);
  $(".clock").classList.toggle("interrupted", Boolean(interrupted));
  if (interrupted) {
    const off = interrupted.pcWentOff;
    $("#clock-state").textContent = off
      ? `Still clocked in from ${dayLabel(interrupted.start)}, ${clockTime(interrupted.start)}. The PC's last activity before it turned off was ${dayLabel(off)}, ${clockTime(off)}.`
      : `Still clocked in from ${dayLabel(interrupted.start)}, ${clockTime(interrupted.start)}, before the PC last turned off.`;
    $("#clock-button").textContent = off ? `Clock out at ${dayLabel(off)}, ${clockTime(off).slice(0, 5)}` : "Clock out now";
  } else {
    $("#clock-state").textContent = current ? `Clocked in since ${dayLabel(current.start)}, ${clockTime(current.start)}` : "Not clocked in";
    $("#clock-button").textContent = current ? "Clock out" : "Clock in";
  }
  const week = state.weeks.find((w) => w.running);
  const parts = [week ? `This week: ${hours(week.worked)} worked, ${hours(week.overtime)} overtime` : "Nothing logged this week yet"];
  if (state.pcOnSince) parts.push(`PC on since ${dayLabel(state.pcOnSince)}, ${clockTime(state.pcOnSince).slice(0, 5)}`);
  $("#this-week").textContent = parts.join(" · ");
  tick();
}

function tick() {
  if (!current || interrupted) {
    $("#timer").textContent = interrupted ? "–:––:––" : "0:00:00";
    return;
  }
  const now = Date.now() + clockSkew;
  const started = Date.parse(current.start);
  const seconds = Math.max(0, Math.floor((now - started - lunchOverlap(started, now)) / 1000));
  const h = Math.floor(seconds / 3600);
  const m = Math.floor((seconds % 3600) / 60);
  const s = seconds % 60;
  $("#timer").textContent = `${h}:${String(m).padStart(2, "0")}:${String(s).padStart(2, "0")}`;
}

function lunchOverlap(start, end) {
  const [h, m] = lunch.start.split(":").map(Number);
  const begins = new Date(start);
  begins.setHours(h, m, 0, 0);
  const ends = begins.getTime() + lunch.minutes * 60000;
  return Math.max(0, Math.min(end, ends) - Math.max(start, begins.getTime()));
}

function renderBadges(state) {
  const integrity = $("#integrity");
  const broken = state.integrity.problems.length > 0;
  integrity.className = `badge ${broken ? "bad" : "ok"}`;
  integrity.textContent = broken ? "Log has been altered" : `Log intact · ${state.integrity.entries} entries`;
  integrity.title = broken ? state.integrity.problems.join("\n") : "Click to also check the full git history";

  const saving = $("#saving");
  const { places } = state.saving;
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

const PLACE_HELP = {
  obsidian: ["Vault folder", "/home/you/Notes", true, "Notes go into a Chronata folder inside the vault: one note per day and an overview, plus the sealed log."],
  folder: ["Folder", "/home/you/Documents/Time", true, "Writes “Chronata time log.txt” and the sealed log into this folder. A Dropbox, OneDrive or Syncthing folder works too."],
  git: ["Repository address", "https://github.com/you/time-log.git", false, "Create an empty private repository first. Git hosts record when each save arrives."],
  webdav: ["Server address", "https://cloud.example.com/remote.php/dav/files/you/", false, "Nextcloud, ownCloud and most file servers speak WebDAV. The password is kept only on this computer."],
};

function renderPlaces(state) {
  const { places, kinds, stamped } = state.saving;
  const select = $("#place-kind");
  if (!select.options.length) {
    select.append(...Object.entries(kinds).map(([kind, label]) => el("option", { value: kind }, label)));
    describeKind();
  }
  $("#stamp-text").textContent = stamped.upTo
    ? `Everything up to entry ${stamped.upTo} was timestamped by ${stamped.by.map((s) => `${s.authority} at ${s.time.slice(11, 19)} UTC on ${longDate(s.time)}`).join(" and ")}. These are signed receipts from outside organisations, so the times don't depend on this computer's clock.`
    : "Nothing timestamped yet. The next save asks DigiCert and FreeTSA for signed receipts of the log.";
  $("#places").replaceChildren(...places.map((place) => el("div", { class: "card place" },
    el("div", {},
      el("h3", {}, `${place.name} · ${place.kindLabel}`),
      el("div", { class: "where" }, place.target),
      el("div", { class: `state ${place.error ? "bad" : "good"}` },
        place.error ? `Last save failed: ${place.error}` : place.saved ? `Saved ${dayLabel(place.saved)}, ${clockTime(place.saved)}` : "Not saved yet"),
    ),
    el("button", { type: "button", class: "link", onclick: () => {
      if (confirm(`Stop saving to ${place.name}? Copies already there are left alone.`)) act("/api/places/remove", { id: place.id });
    } }, "Remove"),
  )));
}

function describeKind() {
  const [label, placeholder, local, hint] = PLACE_HELP[$("#place-kind").value];
  $("#target-label").textContent = label;
  $("#place-form").elements.target.placeholder = placeholder;
  $("#choose-folder").hidden = !local;
  $("#place-hint").textContent = hint;
  document.querySelectorAll(".dav-only").forEach((node) => (node.hidden = $("#place-kind").value !== "webdav"));
}

function renderTotals(state) {
  $("#t-owed").textContent = hours(state.totals.owed);
  $("#t-compensated").textContent = hours(state.totals.compensated);
  $("#t-shortfall").textContent = hours(state.totals.shortfall);
  $("#t-unmatched").textContent = hours(state.totals.unmatched);
  $("#t-shortfall").parentElement.classList.toggle("has-value", state.totals.shortfall > 0);
}

function shiftCard(shift, day) {
  const chips = [];
  if (shift.label) chips.push(el("span", { class: "chip label" }, shift.label));
  if (day) chips.push(el("span", { class: `chip ${day.madeUp ? "live" : "warn"}` },
    day.madeUp ? `Late ${hours(day.late)} · made up, left ${clockTime(day.lastOut).slice(0, 5)}` : `Late ${hours(day.late)} · ${hours(day.short)} short`));
  if (!shift.end) chips.push(el("span", { class: "chip live" }, "Open"));
  if (shift.voided) chips.push(el("span", { class: "chip" }, "Struck out"));
  if (shift.lateBy != null) chips.push(el("span", { class: "chip warn" }, `Entered ${lateLabel(shift.lateBy)} after the fact`));
  chips.push(pcChip(shift));
  if (shift.lunch) chips.push(el("span", { class: "chip" }, `Lunch −${hours(shift.lunch)}`));
  const corrections = shift.changes.filter((change) => change.includes(" changed ")).length;
  if (corrections) chips.push(el("span", { class: "chip" }, corrections === 1 ? "Corrected" : `Corrected ${corrections}×`));

  const labelButton = el("button", { type: "button", class: "link", onclick: () => {
    const label = prompt("Client or project for this shift (leave empty to remove)", shift.label);
    if (label !== null) act("/api/label", { id: shift.id, label });
  } }, "Label");
  const tools = shift.voided ? null : el("span", { class: "tools" },
    labelButton,
    shift.end ? el("button", { type: "button", class: "link", onclick: () => openCorrect(shift) }, "Correct") : null,
    shift.end ? el("button", { type: "button", class: "link", onclick: () => openStrike(shift) }, "Strike out") : null,
  );

  const pcLines = shift.pc.sessions.map((s) => el("li", {}, `PC on ${dayLabel(s.on)} ${clockTime(s.on).slice(0, 5)} – ${s.off ? `${dayLabel(s.off)} ${clockTime(s.off).slice(0, 5)}` : "still on"}${s.off ? (s.exact ? ", at shutdown" : ", last activity") : ""}`));
  const trail = [...shift.notes.map((note) => el("li", { class: "note" }, note)), ...pcLines, ...shift.changes.map((change) => el("li", {}, change))];

  return el("div", { class: `shift ${shift.voided ? "voided" : ""}` },
    el("div", { class: "shift-row" },
      el("span", { class: "when" }, dayLabel(shift.start)),
      el("span", { class: "span" }, `${clockTime(shift.start)} – ${shift.end ? clockTime(shift.end) : "now"}`),
      el("span", { class: "worked" }, shift.worked == null ? "" : hours(shift.worked)),
      tools || el("span", { class: "tools" }),
    ),
    chips.length ? el("div", { class: "chips" }, chips) : null,
    trail.length ? el("ul", { class: "trail" }, trail) : null,
  );
}

function pcChip(shift) {
  const { share, sessions, beforeRecords } = shift.pc;
  if (!sessions.length) return beforeRecords ? el("span", { class: "chip" }, "No PC record") : el("span", { class: "chip warn" }, "PC was off");
  if (share >= 0.98) return el("span", { class: "chip live" }, shift.end ? "PC on throughout" : "PC on");
  return el("span", { class: "chip warn" }, `PC on for ${Math.round(share * 100)}%`);
}

function renderShifts(state) {
  const container = $("#shifts");
  if (!state.shifts.length) {
    container.replaceChildren(el("div", { class: "card empty" }, "No shifts yet. Clock in above, or add one you missed."));
    return;
  }
  const weeks = new Map(state.weeks.map((week) => [week.start, week]));
  const firstOfDay = new Map();
  for (const [date, day] of Object.entries(state.days)) {
    const earliest = state.shifts.filter((s) => s.start.slice(0, 10) === date && !s.voided).sort((a, b) => a.start.localeCompare(b.start))[0];
    if (earliest) firstOfDay.set(earliest.id, day);
  }
  const groups = new Map();
  for (const shift of state.shifts) {
    const key = weekStart(shift.start);
    if (!groups.has(key)) groups.set(key, []);
    groups.get(key).push(shift);
  }
  container.replaceChildren(...[...groups].map(([start, shifts]) => {
    const week = weeks.get(start);
    return el("section", { class: "week" },
      el("div", { class: "week-head" },
        el("h3", {}, `Week of ${longDate(start)}`),
        week ? el("span", { class: "sum" }, el("strong", {}, hours(week.worked)), " worked · ", el("strong", {}, hours(week.overtime)), week.running ? " overtime so far" : " overtime") : null,
      ),
      el("div", { class: "shift-list" }, shifts.map((shift) => shiftCard(shift, firstOfDay.get(shift.id)))),
    );
  }));
}

function renderLabels(state) {
  $("#known-labels").replaceChildren(...state.labels.map((label) => el("option", { value: label })));
  const labelInput = $("#clock-form").elements.label;
  labelInput.hidden = Boolean(current) && !interrupted;
  if (!current && document.activeElement !== labelInput && !labelInput.value && state.labels.length) labelInput.value = state.labels[0];
  const week = state.byLabel.week.filter((row) => row.label);
  $("#by-label").replaceChildren(...(week.length ? [el("div", { class: "card" },
    el("h3", {}, "This week by label"),
    el("div", { class: "by-label" }, state.byLabel.week.map((row) => el("span", {}, `${row.label || "No label"} `, el("strong", {}, hours(row.worked))))),
  )] : []));
}

function renderPay(state) {
  const unmatched = $("#unmatched");
  unmatched.replaceChildren();
  if (state.unmatched.length) {
    unmatched.append(el("div", { class: "card" },
      el("h2", {}, "Overtime no payslip covers yet"),
      el("p", { class: "muted small" }, "When the payslip for these days arrives, record it above."),
      el("ul", { class: "days" }, state.unmatched.map((day) => el("li", {}, `${dayLabel(day.date)} · ${hours(day.overtime)}`))),
    ));
  }
  $("#periods").replaceChildren(...state.periods.map((period) => {
    const settled = period.shortfall === 0;
    return el("div", { class: "card period" },
      el("div", { class: "period-head" },
        el("h3", {}, `${longDate(period.start)} – ${longDate(period.end)}`),
        el("span", { class: "muted small" }, period.references.join("; ")),
      ),
      el("div", { class: "figures" },
        el("div", {}, el("span", {}, "Overtime worked"), el("span", {}, hours(period.owed))),
        el("div", {}, el("span", {}, "Paid"), el("span", {}, hours(period.paid))),
        el("div", {}, el("span", {}, "Time off"), el("span", {}, hours(period.timeOff))),
        el("div", { class: settled ? "good" : "bad" }, el("span", {}, "Uncompensated"), el("span", {}, settled ? "None" : hours(period.shortfall))),
      ),
    );
  }));
}

function renderRules(state) {
  const { dailyHours, weeklyHours, daysOff, lunchStart, lunchMinutes } = state.rules;
  lunch = { start: lunchStart, minutes: lunchMinutes };
  const off = daysOff.length ? `, and every hour on ${daysOff.map((d) => DAY_NAME[d]).join(", ")}` : "";
  $("#rules").textContent = `Shift ${state.setup.shift}, lunch ${state.setup.lunch}. Overtime counts past ${dailyHours} h a day and ${weeklyHours} h a week${off}.`;
  renderSetup(state.setup, state.setup.needed);
}

function renderSetup(setup, open) {
  const form = $("#setup-form");
  $("#lunch-question").textContent = setup.lunchQuestion;
  $("#shift-question").textContent = setup.shiftQuestion;
  if ($("#setup").hidden) {
    form.elements.lunch.value = setup.lunch;
    form.elements.shift.value = setup.shift;
  }
  $("#setup-cancel").hidden = setup.needed;
  if (open) $("#setup").hidden = false;
}

async function refresh() {
  try {
    const state = await api("/api/state");
    clockSkew = Date.parse(state.now) - Date.now();
    renderClock(state);
    renderBadges(state);
    renderTotals(state);
    renderShifts(state);
    renderPay(state);
    renderLabels(state);
    renderPlaces(state);
    renderRules(state);
  } catch (error) {
    toast(`Could not load the log: ${error.message}`, "bad");
  }
}

function openCorrect(shift) {
  const form = $("#correct-form");
  form.elements.id.value = shift.id;
  form.elements.start.value = shift.start.slice(0, 19);
  form.elements.end.value = shift.end.slice(0, 19);
  form.elements.reason.value = "";
  $("#correct-dialog").showModal();
}

function openStrike(shift) {
  const form = $("#strike-form");
  form.elements.id.value = shift.id;
  form.elements.reason.value = "";
  $("#strike-dialog").showModal();
}

function today() {
  const now = new Date(Date.now() + clockSkew);
  return `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, "0")}-${String(now.getDate()).padStart(2, "0")}`;
}

function wire() {
  $("#clock-form").addEventListener("submit", async (event) => {
    event.preventDefault();
    const form = event.target;
    const { note, at, label } = fields(form);
    const when = at || (interrupted && interrupted.pcWentOff) || null;
    if (await act(current ? "/api/out" : "/api/in", { note, at: when, label }, form)) {
      form.reset();
      form.querySelector("details").open = false;
    }
  });

  $("#add-form").addEventListener("submit", async (event) => {
    event.preventDefault();
    if (await act("/api/add", fields(event.target), event.target)) {
      event.target.reset();
      event.target.elements.date.value = today();
    }
  });

  $("#setup-form").addEventListener("submit", async (event) => {
    event.preventDefault();
    if (await act("/api/setup", fields(event.target), event.target)) $("#setup").hidden = true;
  });
  $("#setup-cancel").addEventListener("click", () => ($("#setup").hidden = true));
  $("#change-hours").addEventListener("click", () => {
    $("#setup").hidden = false;
    $("#setup").scrollIntoView({ behavior: "smooth" });
  });

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

  $("#paid-form").addEventListener("submit", async (event) => {
    event.preventDefault();
    const body = fields(event.target);
    if (await act("/api/paid", { ...body, timeOff: body.timeOff === "1" }, event.target)) event.target.reset();
  });

  for (const [formId, dialogId, path] of [["#correct-form", "#correct-dialog", "/api/correct"], ["#strike-form", "#strike-dialog", "/api/strike"]]) {
    $(formId).addEventListener("submit", async (event) => {
      event.preventDefault();
      if (await act(path, fields(event.target), event.target)) $(dialogId).close();
    });
  }
  document.querySelectorAll("[data-close]").forEach((button) => button.addEventListener("click", () => button.closest("dialog").close()));

  document.querySelectorAll(".tabs button").forEach((tab) => tab.addEventListener("click", () => showTab(tab.dataset.tab)));

  $("#integrity").addEventListener("click", async () => {
    toast("Checking the full history…");
    try {
      const { problems } = await api("/api/verify");
      toast(problems.length ? `Altered: ${problems.join("; ")}` : "Intact: every entry is sealed to the one before, and no commit rewrote an earlier one.", problems.length ? "bad" : "");
    } catch (error) {
      toast(error.message, "bad");
    }
  });

  document.addEventListener("visibilitychange", () => document.visibilityState === "visible" && refresh());
  setInterval(tick, 1000);
  setInterval(refresh, 60000);
}

function showTab(name) {
  document.querySelectorAll(".tabs button").forEach((tab) => tab.setAttribute("aria-selected", String(tab.dataset.tab === name)));
  document.querySelectorAll(".tab").forEach((panel) => (panel.hidden = panel.id !== `tab-${name}`));
  try { localStorage.setItem("chronata-tab", name); } catch {}
}

wire();
refresh().then(() => {
  $("#add-form").elements.date.value = today();
  const linked = location.hash.slice(1);
  if (document.getElementById(`tab-${linked}`)) return showTab(linked);
  try { showTab(localStorage.getItem("chronata-tab") || "shifts"); } catch { showTab("shifts"); }
});
