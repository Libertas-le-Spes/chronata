from chronata.presenters.page.facts import PageFacts
from chronata.timekeeping.shifts.shifts import open_shift


def page_facts(app) -> PageFacts:
    log = app.log
    all_shifts = log.shifts()
    newest, by = app.saving.stamped()
    return PageFacts(
        now=log.clock(), hours=log.hours, shifts=all_shifts, weeks=log.weeks(), sessions=log.pc_sessions(),
        current=open_shift(all_shifts), interrupted=app.pc.interrupted(), this_boot=app.pc.this_boot(),
        unclocked_since=app.clocking.unclocked_since(), suggested_label=app.labels.suggested(), stamps=app.timestamper.stamps(),
        entry_count=log.entry_count(), problems=log.problems(), compensation=log.compensation(log.weeks_per_label()),
        places=app.saving.statuses(), place_kinds=app.saving.places.kinds(), newest_stamped=newest, stamped_by=by,
    )
