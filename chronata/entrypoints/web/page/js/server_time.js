import { isoDay } from "./dates.js";

let skew = 0;
let syncedAt = 0;

export function syncWith(state) {
  skew = Date.parse(state.now) - Date.now();
  syncedAt = Date.parse(state.now);
}

export function now() {
  return new Date(Date.now() + skew);
}

export function secondsSinceSync() {
  return (Date.now() + skew - syncedAt) / 1000;
}

export function today() {
  return isoDay(now());
}
