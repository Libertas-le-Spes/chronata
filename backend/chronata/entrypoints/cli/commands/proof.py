import sys
from pathlib import Path

from chronata.use_cases.log.outcome import UserError
from chronata.use_cases.log.verification import Findings, verify
from chronata.wiring import App, open_saved_copy


def check(args, app: App) -> None:
    findings = _findings(args, app)
    if findings.problems:
        print("\n".join(findings.problems), file=sys.stderr)
        raise UserError("the log has been altered; see above")
    kept = not args.folder and app.history.keeps_history()
    counted = f"{findings.entries} {'entry' if findings.entries == 1 else 'entries'}"
    print(f"intact: {counted}, each sealed to the one before" + (", none rewritten in history" if kept else ""))
    print("\n".join(_stamp_lines(findings)))


def _findings(args, app: App) -> Findings:
    if not args.folder:
        return verify(app.log.record, app.timestamper, app.history)
    record, timestamper = open_saved_copy(Path(args.folder).expanduser())
    return verify(record, timestamper)


def _stamp_lines(findings: Findings) -> list[str]:
    newest = findings.latest_stamped
    if newest is None:
        return ["no independent timestamps yet"]
    by = ", ".join(f"{s.authority_name} {s.time:%Y-%m-%d %H:%M:%S} UTC" for s in findings.stamps if s.seq == newest)
    lines = [f"independently timestamped: everything up to entry {newest} existed by {by}"]
    return lines + [f"not yet timestamped: entries {newest + 1} to {findings.entries}"] * (findings.entries > newest)


def register(commands) -> None:
    command = commands.add_parser("verify", help="prove the log has not been edited, and check its timestamps")
    command.add_argument("--folder", help="check a saved copy instead, e.g. an Obsidian vault or a folder")
    command.set_defaults(run=check)
