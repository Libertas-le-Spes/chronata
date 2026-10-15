export const DAY = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"];
const MONTH = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];
export const DAY_NAME = { mon: "Mon", tue: "Tue", wed: "Wed", thu: "Thu", fri: "Fri", sat: "Sat", sun: "Sun" };

export function hours(minutes) {
  const sign = minutes < 0 ? "-" : "";
  const total = Math.abs(minutes);
  return `${sign}${Math.floor(total / 60)}:${String(total % 60).padStart(2, "0")}`;
}

export function localDate(iso) {
  const [y, m, d] = iso.slice(0, 10).split("-").map(Number);
  return new Date(y, m - 1, d);
}

export function dayLabel(iso) {
  const date = localDate(iso);
  return `${DAY[date.getDay()]} ${date.getDate()} ${MONTH[date.getMonth()]}`;
}

export function longDate(iso) {
  const date = localDate(iso);
  return `${date.getDate()} ${MONTH[date.getMonth()]} ${date.getFullYear()}`;
}

export function clockTime(iso) {
  return iso.slice(11, 19);
}

export function weekStart(iso) {
  const date = localDate(iso);
  date.setDate(date.getDate() - ((date.getDay() + 6) % 7));
  return isoDay(date);
}

export function isoDay(date) {
  return `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, "0")}-${String(date.getDate()).padStart(2, "0")}`;
}

export function lateLabel(minutes) {
  return minutes >= 1440 ? `${Math.floor(minutes / 1440)}d ${Math.floor((minutes % 1440) / 60)}h` : hours(minutes);
}
