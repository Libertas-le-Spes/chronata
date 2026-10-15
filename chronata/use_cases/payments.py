from chronata.use_cases import typed_input
from chronata.use_cases.log import Log, one_writer_at_a_time
from chronata.use_cases.outcome import Outcome, UserError


class Payments:
    def __init__(self, log: Log):
        self.log = log

    @one_writer_at_a_time
    def record(self, start: str, end: str, paid_hours: float, time_off: bool, reference: str | None) -> Outcome:
        begins, ends = typed_input.day(start), typed_input.day(end)
        if ends < begins:
            raise UserError("the pay period ends before it starts")
        if paid_hours < 0:
            raise UserError("hours paid cannot be negative")
        data = {"from": begins.isoformat(), "to": ends.isoformat(), "hours": paid_hours,
                "kind": "time_off" if time_off else "paid", "reference": reference or ""}
        message = f"recorded {paid_hours:g}h of overtime {'given as time off' if time_off else 'paid'} for {begins} to {ends}"
        return self.log.write("compensation", data, message, self.log.clock())
