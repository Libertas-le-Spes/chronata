from tests.fakes import Fixture, hours


def clocked(f: Fixture, came_in: str, left: str) -> int:
    f.at(f"2026-10-14T{came_in}:00")
    f.app.clocking.clock_in(None, None)
    f.at(f"2026-10-14T{left}:00")
    f.app.clocking.clock_out(None, None)
    return f.app.log.shifts()[-1].id


def waived_spans(f: Fixture) -> list[tuple[str, str]]:
    spans = []
    for gap in f.app.log.shifts()[-1].breaks:
        if gap.waived:
            spans.append((f"{gap.start:%H:%M}", f"{gap.end:%H:%M}"))
    return spans


def set_up_hours() -> Fixture:
    f = Fixture("2026-10-14T07:00:00")
    f.app.setup.configure(hours("08:00", "17:00"), "Primary")
    return f
