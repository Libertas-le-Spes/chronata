import os
import re
import stat
import subprocess
import tempfile
import unittest
from pathlib import Path

from chronata.wiring import open_app
from tests.fakes import FakeDesktop, FakePower, Fixture, NoTimestamps, hours

PACKAGE = Path(__file__).parent.parent / "chronata"
LAUNCHER = Path(__file__).parent.parent / "bin" / "chronata"
WRITES_OR_DELETES = re.compile(r"\.unlink\(|\.rmdir\(|os\.(unlink|rmdir|remove|replace|rename)\(|rmtree\(|\.write_text\(|\.write_bytes\(|open\([^)]*[\"'](w|a)")
MAY_WRITE_OR_DELETE = {
    "adapters/storage/owner_only_file.py",
    "adapters/storage/owner_only_folder.py",
    "adapters/storage/place_folder.py",
    "adapters/places/transport/git_folder.py",
}


def shared_with_others(folder: Path) -> list[str]:
    found = []
    for path in [folder, *folder.rglob("*")]:
        if ".git" in path.relative_to(folder).parts:
            continue
        if stat.S_IMODE(os.lstat(path).st_mode) & 0o077:
            found.append(f"{oct(stat.S_IMODE(os.lstat(path).st_mode))} {path.relative_to(folder)}")
    return found


class EverythingChronataKeeps(unittest.TestCase):
    def test_only_its_owner_can_open(self):
        f = Fixture("2026-10-14T17:40:00")
        f.app.labels.create("Northwind", hours("08:00", "17:00", "12:00", "60"))
        f.app.corrections.add("2026-10-13", "08:00", "17:00", "written later", "made-up note", "Northwind")
        place = Path(tempfile.mkdtemp())
        f.app.saving.add_place(f.app.log, "folder", "Copy", str(place))
        f.app.log.save_now()
        settings = f.app.saving.places.path.parent
        self.assertEqual(shared_with_others(f.data) + shared_with_others(settings) + shared_with_others(place), [])

    def test_its_folders_are_made_private_when_they_were_not(self):
        data = Path(tempfile.mkdtemp())
        data.chmod(0o755)
        open_app(data, Path(tempfile.mkdtemp()), power=FakePower(), desktop=FakeDesktop(), timestamper=NoTimestamps())
        self.assertEqual(stat.S_IMODE(data.stat().st_mode), 0o700)


class OnlyTheSafeWritersTouchFiles(unittest.TestCase):
    def test_no_other_code_writes_or_deletes_files_itself(self):
        found = []
        for path in sorted(PACKAGE.rglob("*.py")):
            relative = str(path.relative_to(PACKAGE))
            if relative in MAY_WRITE_OR_DELETE:
                continue
            found += [f"{relative}:{number}" for number, line in enumerate(path.read_text().splitlines(), 1) if WRITES_OR_DELETES.search(line)]
        self.assertEqual(found, [])


class TheLauncher(unittest.TestCase):
    def test_does_not_run_code_from_the_folder_it_is_started_in(self):
        planted = Path(tempfile.mkdtemp())
        (planted / "argparse.py").write_text('raise SystemExit("planted code ran")\n')
        (planted / "json.py").write_text('raise SystemExit("planted code ran")\n')
        home = Path(tempfile.mkdtemp())
        environment = {**os.environ, "CHRONATA_HOME": str(home / "data"), "CHRONATA_CONFIG": str(home / "config"),
                       "XDG_RUNTIME_DIR": str(home / "run"), "PYTHONPATH": str(planted)}
        ran = subprocess.run([str(LAUNCHER), "status"], cwd=planted, capture_output=True, text=True, env=environment, timeout=30)
        self.assertEqual((ran.returncode, ran.stdout.strip()), (0, "not clocked in"), ran.stderr)


if __name__ == "__main__":
    unittest.main()
