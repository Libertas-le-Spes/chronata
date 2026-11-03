from chronata.use_cases.log.outcome import Outcome
from chronata.wiring import App


def reminders(args, app: App) -> Outcome:
    if args.off:
        return app.reminder_setting.turn_off()
    return app.reminder_setting.remind_every(args.every)


def register(commands) -> None:
    command = commands.add_parser("reminders", help="how often to be reminded to clock out once your shift has ended")
    choice = command.add_mutually_exclusive_group(required=True)
    choice.add_argument("--every", type=int, help="minutes between reminders, 5 to 240; on a day off they come every hour")
    choice.add_argument("--off", action="store_true", help="no clock-out reminders")
    command.set_defaults(run=reminders)
