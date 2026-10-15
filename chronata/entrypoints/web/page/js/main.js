import { whenChanged } from "./actions.js";
import { api } from "./api.js";
import * as chart from "./chart.js";
import * as clock from "./clock.js";
import * as compensation from "./compensation.js";
import * as hours from "./hours.js";
import * as integrity from "./integrity.js";
import * as labels from "./labels.js";
import * as pcBreaks from "./pc_breaks.js";
import * as places from "./places.js";
import { syncWith } from "./server_time.js";
import * as setup from "./setup.js";
import * as shifts from "./shifts.js";
import * as tabs from "./tabs.js";
import { toast } from "./toast.js";

const sections = [clock, integrity, compensation, shifts, chart, pcBreaks, hours, labels, places, setup];

async function refresh() {
  try {
    const state = await api("/api/state");
    syncWith(state);
    sections.forEach((section) => section.render(state));
  } catch (error) {
    toast(`Could not load the log: ${error.message}`, "bad");
  }
}

const LINKS = {
  "explain-break": () => pcBreaks.focusFirst(),
  "clock-in": () => clock.focusLabel(),
  "confirm-out": () => clock.askBeforeClockingOut(),
};

function followLink() {
  const linked = location.hash.slice(1);
  if (LINKS[linked]) {
    history.replaceState(null, "", location.pathname);
    LINKS[linked]();
    return tabs.showTab("shifts");
  }
  if (tabs.hasTab(linked)) return tabs.showTab(linked);
  tabs.showRememberedTab();
}

whenChanged(refresh);
[...sections.filter((section) => section.wire), tabs].forEach((section) => section.wire());
document.addEventListener("visibilitychange", () => document.visibilityState === "visible" && refresh());
setInterval(refresh, 60000);
refresh().then(followLink);
