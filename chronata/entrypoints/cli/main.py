import argparse
import sys

from chronata.entrypoints.cli import clocking, compensation, corrections, desktop, labels, places, proof, reports, setup
from chronata.entrypoints.cli.answers import how_to_answer
from chronata.timekeeping.record import TamperedRecord
from chronata.use_cases.outcome import UserError
from chronata.use_cases.questions import Question
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
    except Question as question:
        print(f"chronata: {how_to_answer(question)}", file=sys.stderr)
        return 1
    except (UserError, TamperedRecord, FileNotFoundError) as error:
        print(f"chronata: {error}", file=sys.stderr)
        return 1
    if outcome is not None:
        print(outcome.message)
        if outcome.warning:
            print(outcome.warning, file=sys.stderr)
    return 0
