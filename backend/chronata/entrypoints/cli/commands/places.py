from chronata.use_cases.log.outcome import Outcome
from chronata.wiring import App


def save(args, app: App) -> Outcome:
    return app.log.save_now()


def list_places(args, app: App) -> None:
    statuses = app.saving.statuses()
    if not statuses:
        print("only saved on this computer; add a place with: chronata place-add KIND WHERE")
    kinds = app.saving.places.kinds()
    for place, last in statuses:
        state = f"failed: {last['error']}" if last.get("error") else (f"saved {last['saved'][:19]}" if last.get("saved") else "not saved yet")
        print(f"{place.id:16} {kinds[place.kind].label:22} {place.name:14} {place.target}  [{state}]")
    print("\nkinds of place you can add: " + ", ".join(f"{kind} ({described.label})" for kind, described in kinds.items()))


def add_place(args, app: App) -> Outcome:
    return app.saving.add_place(app.log, args.kind, args.name or "", args.where, args.username or "", args.password or "", args.folder or "")


def remove_place(args, app: App) -> Outcome:
    return app.saving.remove_place(args.id)


def register(commands) -> None:
    command = commands.add_parser("save", help="timestamp the log and save it to every place now")
    command.set_defaults(run=save)

    command = commands.add_parser("places", help="where the log is saved")
    command.set_defaults(run=list_places)

    command = commands.add_parser("place-add", help="save the log somewhere else too")
    command.add_argument("kind", help="the kind of place; chronata places lists them")
    command.add_argument("where", help="a folder path, a git URL or a web server address")
    command.add_argument("--folder", help="for git-folder: the folder inside the repository, e.g. 'Work Logs'")
    command.add_argument("--name")
    command.add_argument("--username")
    command.add_argument("--password")
    command.set_defaults(run=add_place)

    command = commands.add_parser("place-remove", help="stop saving to a place")
    command.add_argument("id")
    command.set_defaults(run=remove_place)
