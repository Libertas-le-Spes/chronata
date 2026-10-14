import re
import subprocess
import xml.etree.ElementTree as ElementTree
from datetime import datetime, timedelta, timezone

from chronata.timekeeping.pc_sessions import Boot

STARTED, STOPPED_CLEANLY = "6005", "6006"
STARTS_AND_STOPS = "*[System[Provider[@Name='EventLog'] and (EventID=6005 or EventID=6006)]]"
STARTS = "*[System[Provider[@Name='EventLog'] and EventID=6005]]"
NAMESPACE = {"e": "http://schemas.microsoft.com/win/2004/08/events/event"}
MATCHING_WINDOW = timedelta(minutes=15)


class WindowsEvents:
    def __init__(self):
        self._started: datetime | None = None

    def current_boot_id(self) -> str:
        return _boot_id(self._current_start())

    def boots(self) -> list[Boot]:
        events = events_from_xml(_query(STARTS_AND_STOPS))
        return boots_from_events(events, self._current_start(), datetime.now().astimezone().replace(microsecond=0))

    def shutting_down(self) -> bool:
        return False

    def _current_start(self) -> datetime:
        if self._started is None:
            import ctypes
            by_uptime = datetime.now().astimezone() - timedelta(milliseconds=ctypes.windll.kernel32.GetTickCount64())
            latest = [moment for event_id, moment in events_from_xml(_query(STARTS, newest_only=True)) if event_id == STARTED]
            matching = latest and abs(latest[-1] - by_uptime) <= MATCHING_WINDOW
            self._started = latest[-1] if matching else by_uptime.replace(second=0, microsecond=0)
        return self._started


def _query(query: str, newest_only: bool = False) -> str:
    newest = ["/rd:true", "/c:1"] if newest_only else []
    listed = subprocess.run(["wevtutil", "qe", "System", f"/q:{query}", "/f:xml", *newest], capture_output=True, text=True, check=False)
    return listed.stdout if listed.returncode == 0 else ""


def events_from_xml(text: str) -> list[tuple[str, datetime]]:
    root = ElementTree.fromstring(f"<Events>{text}</Events>")
    found = []
    for event in root.iter("{http://schemas.microsoft.com/win/2004/08/events/event}Event"):
        event_id = event.findtext("e:System/e:EventID", namespaces=NAMESPACE)
        created = event.find("e:System/e:TimeCreated", NAMESPACE)
        if event_id and created is not None:
            moment = re.sub(r"\.\d+", "", created.get("SystemTime", "")).replace("Z", "+00:00")
            found.append((event_id, datetime.fromisoformat(moment).astimezone()))
    return sorted(found, key=lambda pair: pair[1])


def boots_from_events(events: list[tuple[str, datetime]], current_start: datetime, now: datetime) -> list[Boot]:
    boots: list[Boot] = []
    started: datetime | None = None
    for event_id, moment in events:
        if event_id == STARTED:
            if started:
                boots.append(Boot(_boot_id(started), started, started, False))
            started = moment
        elif event_id == STOPPED_CLEANLY and started:
            boots.append(Boot(_boot_id(started), started, moment, False, off_is_exact=True))
            started = None
    if started and abs(started - current_start) <= MATCHING_WINDOW:
        boots.append(Boot(_boot_id(started), started, now, True))
    elif started:
        boots.append(Boot(_boot_id(started), started, started, False))
    if not boots or not boots[-1].current:
        boots.append(Boot(_boot_id(current_start), current_start, now, True))
    return boots


def _boot_id(on: datetime) -> str:
    return f"windows-{on.astimezone(timezone.utc):%Y%m%dT%H%M%S}"
