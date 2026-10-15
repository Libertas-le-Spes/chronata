import { DAY, dayLabel, hours, localDate, longDate } from "../shared/dates.js";
import { $, el, svg } from "../shared/dom.js";

let chartWeek = null;
let lastState = null;

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

function drawWeek(week, targetMinutes) {
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
  if (targetMinutes) {
    layers.push(svg("line", { class: "target", x1: left, x2: width - right, y1: y(targetMinutes), y2: y(targetMinutes) }));
    layers.push(svg("text", { x: width - right, y: y(targetMinutes) - 5, "text-anchor": "end" }, `full day ${hours(targetMinutes)}`));
  }

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
  return svg("svg", { viewBox: `0 0 ${width} ${height}`, role: "img", "aria-label": `Hours worked per day, ${$("#chart-title").textContent.toLowerCase()}` }, ...layers);
}

function weekTable(week) {
  return [
    el("tr", {}, ["Day", "Normal", "Overtime", "Total", ""].map((h) => el("th", {}, h))),
    ...week.days.map((day) => el("tr", {},
      el("td", {}, dayLabel(day.date)),
      el("td", {}, hours(day.normal)),
      el("td", {}, hours(day.overtime)),
      el("td", {}, hours(day.normal + day.overtime) + (day.soFar ? " so far" : "")),
      el("td", {}, dayStatus(day)?.detail || ""),
    )),
  ];
}

export function render(state) {
  lastState = state;
  const { weeks, targetMinutes } = state.chart;
  if (chartWeek === null || chartWeek >= weeks.length) chartWeek = weeks.length - 1;
  const week = weeks[chartWeek];
  $("#week-back").disabled = chartWeek === 0;
  $("#week-next").disabled = chartWeek === weeks.length - 1;
  $("#chart-title").textContent = chartWeek === weeks.length - 1 ? "This week" : `Week of ${longDate(week.start)}`;
  $("#chart").replaceChildren(drawWeek(week, targetMinutes));
  $("#chart-table").replaceChildren(...weekTable(week));
}

export function wire() {
  $("#week-back").addEventListener("click", () => { chartWeek -= 1; render(lastState); });
  $("#week-next").addEventListener("click", () => { chartWeek += 1; render(lastState); });
  let resizing;
  window.addEventListener("resize", () => {
    clearTimeout(resizing);
    resizing = setTimeout(() => lastState && render(lastState), 150);
  });
}
