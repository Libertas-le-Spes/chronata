const token = document.querySelector('meta[name="token"]').content;
const $ = (selector) => document.querySelector(selector);
const DAY = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"];
const MONTH = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];
const DAY_NAME = { mon: "Mon", tue: "Tue", wed: "Wed", thu: "Thu", fri: "Fri", sat: "Sat", sun: "Sun" };

let current = null;
let interrupted = null;
let earlyOut = null;
let stateTime = 0;
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
  earlyOut = current && !state.interrupted && state.beforeEndOfWorkday ? state.shiftEnd : null;
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
  const sinceState = (Date.now() + clockSkew - stateTime) / 1000;
  const seconds = Math.max(0, Math.floor(current.workedSeconds + sinceState));
  const h = Math.floor(seconds / 3600);
  const m = Math.floor((seconds % 3600) / 60);
  const s = seconds % 60;
  $("#timer").textContent = `${h}:${String(m).padStart(2, "0")}:${String(s).padStart(2, "0")}`;
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
  obsidian: ["Vault folder", "/home/you/Notes", true, "Goes into a Chronata folder inside the vault: an overview, the whole log in one note, a note per day, and the sealed log."],
  folder: ["Folder", "/home/you/Documents/Time", true, "Gets an overview, the whole log in one file, a file per day, and the sealed log. A Dropbox, OneDrive or Syncthing folder works too."],
  git: ["Repository address", "https://github.com/you/time-log.git", false, "Create an empty private repository first. Git hosts record when each save arrives."],
  "git-folder": ["Repository address", "https://github.com/you/notes.git", false, "Saves into one folder of a repository you already use, such as your notes. Only that folder is ever changed, and a folder Chronata did not create is left alone."],
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
  document.querySelectorAll(".folder-only").forEach((node) => (node.hidden = $("#place-kind").value !== "git-folder"));
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
    !day.late ? `${hours(day.short)} short of a full day`
      : day.madeUp ? `Late ${hours(day.late)} · made up, left ${clockTime(day.lastOut).slice(0, 5)}`
      : `Late ${hours(day.late)} · ${hours(day.short)} short`));
  if (!shift.end) chips.push(el("span", { class: "chip live" }, "Open"));
  if (shift.voided) chips.push(el("span", { class: "chip" }, "Struck out"));
  if (shift.lateBy != null) chips.push(el("span", { class: "chip warn" }, `Entered ${lateLabel(shift.lateBy)} after the fact`));
  chips.push(pcChip(shift));
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

const SVG = "http://www.w3.org/2000/svg";
let chartWeek = null;
let lastState = null;

function svg(tag, attributes = {}, ...children) {
  const node = document.createElementNS(SVG, tag);
  for (const [key, value] of Object.entries(attributes)) {
    if (key.startsWith("on")) node.addEventListener(key.slice(2), value);
    else node.setAttribute(key, value);
  }
  node.append(...children);
  return node;
}

function roundedTop(x, y, width, height, radius) {
  const r = Math.min(radius, height, width / 2);
  return `M${x},${y + height}V${y + r}Q${x},${y} ${x + r},${y}H${x + width - r}Q${x + width},${y} ${x + width},${y + r}V${y + height}Z`;
}

function dayStatus(day) {
  if (day.soFar || day.future) return null;
  if (day.late && day.madeUp) return { tone: "good", text: "✓ made up", detail: `Late ${hours(day.late)}, made up` };
  if (day.late) return { tone: "warn", text: `! ${hours(day.short)} short`, detail: `Late ${hours(day.late)}, ${hours(day.short)} short` };
  if (day.short) return { tone: "warn", text: `! ${hours(day.short)} short`, detail: `${hours(day.short)} short of a full day` };
  return null;
}

function renderChart(state) {
  lastState = state;
  const { weeks, targetMinutes } = state.chart;
  if (chartWeek === null || chartWeek >= weeks.length) chartWeek = weeks.length - 1;
  const week = weeks[chartWeek];
  $("#week-back").disabled = chartWeek === 0;
  $("#week-next").disabled = chartWeek === weeks.length - 1;
  $("#chart-title").textContent = chartWeek === weeks.length - 1 ? "This week" : `Week of ${longDate(week.start)}`;

  const width = Math.max(300, Math.round($("#chart").clientWidth || 700)), height = 230, left = 34, right = 8, top = 22, bottom = 46;
  const plotHeight = height - top - bottom, band = (width - left - right) / 7, barWidth = Math.min(24, Math.round(band * 0.5));
  const most = Math.max(targetMinutes, ...week.days.map((d) => d.normal + d.overtime));
  const ceiling = Math.max(2, Math.ceil(most / 120) * 2) * 60;
  const y = (m) => top + plotHeight - (m / ceiling) * plotHeight;

  const layers = [];
  for (let tick = 0; tick <= ceiling; tick += 120) {
    layers.push(svg("line", { class: "grid", x1: left, x2: width - right, y1: y(tick), y2: y(tick) }));
    layers.push(svg("text", { x: left - 8, y: y(tick) + 4, "text-anchor": "end" }, `${tick / 60}h`));
  }
  layers.push(svg("line", { class: "target", x1: left, x2: width - right, y1: y(targetMinutes), y2: y(targetMinutes) }));
  layers.push(svg("text", { x: width - right, y: y(targetMinutes) - 5, "text-anchor": "end" }, `full day ${hours(targetMinutes)}`));

  week.days.forEach((day, index) => {
    const centre = left + band * index + band / 2;
    const x = centre - barWidth / 2;
    const total = day.normal + day.overtime;
    const fade = day.soFar ? " so-far" : "";
    if (day.normal > 0) {
      const h = y(0) - y(day.normal);
      layers.push(day.overtime > 0
        ? svg("rect", { class: `normal${fade}`, x, y: y(day.normal), width: barWidth, height: h })
        : svg("path", { class: `normal${fade}`, d: roundedTop(x, y(day.normal), barWidth, h, 4) }));
    }
    if (day.overtime > 0) {
      const gap = day.normal > 0 ? 2 : 0;
      const h = Math.max(1, y(day.normal) - y(total) - gap);
      layers.push(svg("path", { class: `overtime${fade}`, d: roundedTop(x, y(total), barWidth, h, 4) }));
    }
    if (total > 0) layers.push(svg("text", { class: "value", x: centre, y: y(total) - 6, "text-anchor": "middle" }, hours(total)));
    const date = localDate(day.date);
    layers.push(svg("text", { x: centre, y: height - bottom + 18, "text-anchor": "middle" }, band < 60 ? DAY[date.getDay()].slice(0, 2) : `${DAY[date.getDay()]} ${date.getDate()}`));
    const status = dayStatus(day);
    if (status) layers.push(svg("text", { class: `status-${status.tone}`, x: centre, y: height - bottom + 34, "text-anchor": "middle" }, status.text));
    else if (day.soFar) layers.push(svg("text", { x: centre, y: height - bottom + 34, "text-anchor": "middle" }, "so far"));
    layers.push(svg("rect", {
      class: "hit", x: centre - band / 2, y: top, width: band, height: plotHeight + bottom, rx: 6,
      onmouseenter: (event) => showTip(event, day), onmousemove: (event) => showTip(event, day), onmouseleave: hideTip,
    }));
  });

  $("#chart").replaceChildren(svg("svg", { viewBox: `0 0 ${width} ${height}`, role: "img", "aria-label": `Hours worked per day, ${$("#chart-title").textContent.toLowerCase()}` }, ...layers));
  $("#chart-table").replaceChildren(
    el("tr", {}, ["Day", "Normal", "Overtime", "Total", ""].map((h) => el("th", {}, h))),
    ...week.days.map((day) => el("tr", {},
      el("td", {}, dayLabel(day.date)),
      el("td", {}, hours(day.normal)),
      el("td", {}, hours(day.overtime)),
      el("td", {}, hours(day.normal + day.overtime) + (day.soFar ? " so far" : "")),
      el("td", {}, dayStatus(day)?.detail || ""),
    )),
  );
}

function showTip(event, day) {
  const tip = $("#chart-tip");
  const card = tip.parentElement.getBoundingClientRect();
  const status = dayStatus(day);
  const lines = [
    `${dayLabel(day.date)}${day.soFar ? " (so far)" : ""}`,
    day.normal + day.overtime ? `Worked ${hours(day.normal + day.overtime)}` : "Nothing logged",
    day.overtime ? `Normal ${hours(day.normal)} · overtime ${hours(day.overtime)}` : null,
    status ? status.detail : null,
  ].filter(Boolean);
  tip.replaceChildren(...lines.map((line, i) => el("div", i === 0 ? { class: "tip-title" } : {}, line)));
  tip.style.left = `${event.clientX - card.left}px`;
  tip.style.top = `${event.clientY - card.top}px`;
  tip.hidden = false;
}

function hideTip() {
  $("#chart-tip").hidden = true;
}

function renderPcBreaks(state) {
  $("#pc-breaks").replaceChildren(...state.unexplainedBreaks.map((gap) => {
    const form = el("form", { class: "grid-form" },
      el("label", { class: "wide" }, `Why was the PC off from ${clockTime(gap.start).slice(0, 5)} to ${clockTime(gap.end).slice(0, 5)} on ${dayLabel(gap.start)}?`,
        el("input", { name: "reason", type: "text", required: true, autocomplete: "off", placeholder: "e.g. power cut, restart for updates, went home" })),
      el("button", { class: "primary wide", type: "submit" }, "Add to the record"),
    );
    form.addEventListener("submit", (event) => {
      event.preventDefault();
      act("/api/explain", { id: gap.shift, start: gap.start, reason: fields(form).reason }, form);
    });
    return el("section", { class: "card pc-break" },
      el("h2", {}, "Your PC was off during a shift"),
      el("p", { class: "muted" }, "That time isn't counted as work. Saying why keeps the record self-explaining."),
      form,
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

function renderWorkingDay(state) {
  const { dailyHours, weeklyHours, daysOff } = state.workingDay;
  const off = daysOff.length ? `, and every hour on ${daysOff.map((d) => DAY_NAME[d]).join(", ")}` : "";
  $("#working-day-summary").textContent = `Shift ${state.setup.shift}, lunch ${state.setup.lunch}. Overtime counts past ${dailyHours} h a day and ${weeklyHours} h a week${off}.`;
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
    stateTime = Date.parse(state.now);
    renderClock(state);
    renderBadges(state);
    renderTotals(state);
    renderShifts(state);
    renderPay(state);
    renderChart(state);
    renderPcBreaks(state);
    renderLabels(state);
    renderPlaces(state);
    renderWorkingDay(state);
  } catch (error) {
    toast(`Could not load the log: ${error.message}`, "bad");
  }
}

function askBeforeClockingOut(note = "") {
  const now = new Date(Date.now() + clockSkew);
  $("#out-question").textContent = `It's ${String(now.getHours()).padStart(2, "0")}:${String(now.getMinutes()).padStart(2, "0")}, before your ${earlyOut} finish. Clocking out now ends today's work unless you clock back in, and any time away isn't counted.`;
  $("#out-form").elements.note.value = note;
  $("#out-dialog").showModal();
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
    if (current && earlyOut && !at) return askBeforeClockingOut(note);
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

  $("#week-back").addEventListener("click", () => { chartWeek -= 1; renderChart(lastState); });
  $("#week-next").addEventListener("click", () => { chartWeek += 1; renderChart(lastState); });

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
  $("#out-form").addEventListener("submit", async (event) => {
    event.preventDefault();
    if (await act("/api/out", { note: fields(event.target).note }, event.target)) {
      $("#out-dialog").close();
      $("#clock-form").reset();
    }
  });

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

  let resizing;
  window.addEventListener("resize", () => {
    clearTimeout(resizing);
    resizing = setTimeout(() => lastState && renderChart(lastState), 150);
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
  if (linked === "explain-break") {
    history.replaceState(null, "", location.pathname);
    $("#pc-breaks input")?.focus();
    return showTab("shifts");
  }
  if (linked === "confirm-out") {
    history.replaceState(null, "", location.pathname);
    if (earlyOut) askBeforeClockingOut();
    return showTab("shifts");
  }
  if (document.getElementById(`tab-${linked}`)) return showTab(linked);
  try { showTab(localStorage.getItem("chronata-tab") || "shifts"); } catch { showTab("shifts"); }
});
