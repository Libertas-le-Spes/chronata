import argparse
import sys

from chronata.entrypoints.cli import clocking, compensation, corrections, desktop, labels, places, proof, reports, setup
from chronata.timekeeping.record import TamperedRecord
from chronata.use_cases.outcome import LabelNeedsHours, OffDefaultLabel, Outcome, UnconfirmedLabel, UserError
from chronata.wiring import open_app

COMMAND_GROUPS = [clocking, corrections, labels, compensation, reports, proof, places, setup, desktop]


def parser() -> argparse.ArgumentParser:
    built = argparse.ArgumentParser(prog="chronata", description="A sealed, timestamped record of the time you work.")
    commands = built.add_subparsers(required=True, metavar="command")
    for group in COMMAND_GROUPS:
        group.register(commands)
    return built


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    try:
        outcome = args.run(args, open_app())
    except UnconfirmedLabel as error:
        print(f"chronata: {error} Add --new-label to confirm.", file=sys.stderr)
        return 1
    except LabelNeedsHours as error:
        print(f"chronata: {error}: chronata label-add '{error.label}' --shift '08:00 to 17:00' (or --no-set-hours)", file=sys.stderr)
        return 1
    except OffDefaultLabel as error:
        print(f"chronata: {error} Add --off-default to confirm.", file=sys.stderr)
        return 1
    except (UserError, TamperedRecord, FileNotFoundError) as error:
        print(f"chronata: {error}", file=sys.stderr)
        return 1
    if isinstance(outcome, Outcome):
        print(outcome.message)
        if outcome.warning:
            print(outcome.warning, file=sys.stderr)
    return 0
