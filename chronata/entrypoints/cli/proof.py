import sys
from pathlib import Path

from chronata.use_cases.outcome import UserError
from chronata.use_cases.verification import verify
from chronata.wiring import App, open_saved_copy


def check(args, app: App) -> None:
    if args.folder:
        record, timestamper = open_saved_copy(Path(args.folder).expanduser())
        findings = verify(record, timestamper)
    else:
        findings = verify(app.log.record, app.timestamper, app.history)
    if findings.problems:
        print("\n".join(findings.problems), file=sys.stderr)
        raise UserError("the log has been altered; see above")
    kept = not args.folder and app.history.keeps_history()
    counted = f"{findings.entries} {'entry' if findings.entries == 1 else 'entries'}"
    print(f"intact: {counted}, each sealed to the one before" + (", none rewritten in history" if kept else ""))
    newest = findings.latest_stamped
    if newest is None:
        print("no independent timestamps yet")
        return
    by = ", ".join(f"{s.authority_name} {s.time:%Y-%m-%d %H:%M:%S} UTC" for s in findings.stamps if s.seq == newest)
    print(f"independently timestamped: everything up to entry {newest} existed by {by}")
    if findings.entries > newest:
        print(f"not yet timestamped: entries {newest + 1} to {findings.entries}")


def register(commands) -> None:
    command = commands.add_parser("verify", help="prove the log has not been edited, and check its timestamps")
    command.add_argument("--folder", help="check a saved copy instead, e.g. an Obsidian vault or a folder")
    command.set_defaults(run=check)
