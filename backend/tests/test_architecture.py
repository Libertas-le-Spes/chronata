import unittest
from pathlib import Path

from tests.source_scan import WHOLE_PACKAGE, Source

PACKAGE = Path(__file__).parent.parent / "chronata"
CORE = PACKAGE / "timekeeping"
CORE_MAY_IMPORT = {"collections", "dataclasses", "datetime", "difflib", "hashlib", "json", "typing", "unicodedata"}
CORE_MAY_NOT_NAME = {"open", "__import__", "eval", "exec", "compile", "input", "print", "breakpoint", "globals", "vars", "locals",
                     "getattr", "setattr", "delattr", "__builtins__"}
CORE_MAY_NOT_REACH = {"sys", "os", "modules", "builtins", "__builtins__", "__dict__", "__globals__", "__subclasses__", "__import__",
                      "__loader__", "__spec__", "system", "popen"}

MAY_IMPORT = {
    "timekeeping": {"timekeeping"},
    "use_cases": {"timekeeping", "use_cases"},
    "presenters": {"timekeeping", "use_cases", "presenters"},
    "adapters": {"timekeeping", "use_cases", "adapters"},
    "entrypoints": {"timekeeping", "use_cases", "presenters", "entrypoints", "wiring"},
    "wiring": {"timekeeping", "use_cases", "presenters", "adapters", "wiring"},
}


def ring_of(module: str) -> str:
    return module.split(".")[1]


def source_of(path: Path) -> Source:
    return Source(path.read_text())


def shown(path: Path) -> str:
    return str(path.relative_to(PACKAGE.parent))


def core_may_import(name: str) -> bool:
    if name == "chronata.timekeeping" or name.startswith("chronata.timekeeping."):
        return True
    return name.split(".")[0] in CORE_MAY_IMPORT


class DependenciesPointInward(unittest.TestCase):
    def test_no_ring_imports_a_ring_outside_it(self):
        breaches = []
        for path in sorted(PACKAGE.rglob("*.py")):
            module = ".".join(path.relative_to(PACKAGE.parent).with_suffix("").parts)
            if module in ("chronata.__main__", "chronata.__init__"):
                continue
            allowed = MAY_IMPORT[ring_of(module)]
            for line, imported in source_of(path).chronata_imports():
                if imported == WHOLE_PACKAGE or ring_of(imported) not in allowed:
                    breaches.append(f"{shown(path)}:{line} ({ring_of(module)}) imports {imported}")
        self.assertEqual(breaches, [])

    def test_no_module_uses_a_relative_import_the_ring_check_would_not_see(self):
        relative = []
        for path in sorted(PACKAGE.rglob("*.py")):
            if source_of(path).has_relative_import():
                relative.append(shown(path))
        self.assertEqual(relative, [])


class TheCoreStaysInsideThisProgram(unittest.TestCase):
    def test_the_core_imports_only_what_it_is_allowed(self):
        not_allowed = []
        for path in sorted(CORE.rglob("*.py")):
            for name in source_of(path).modules():
                if not core_may_import(name):
                    not_allowed.append(f"{shown(path)} imports {name}")
        self.assertEqual(not_allowed, [])

    def test_the_core_names_no_built_in_that_reads_files_or_runs_code(self):
        not_allowed = []
        for path in sorted(CORE.rglob("*.py")):
            for name in sorted(source_of(path).names_used() & CORE_MAY_NOT_NAME):
                not_allowed.append(f"{shown(path)} names {name}")
        self.assertEqual(not_allowed, [])

    def test_the_core_reaches_nothing_through_an_allowed_module(self):
        not_allowed = []
        for path in sorted(CORE.rglob("*.py")):
            for name in sorted(source_of(path).attributes_used() & CORE_MAY_NOT_REACH):
                not_allowed.append(f"{shown(path)} reaches .{name}")
        self.assertEqual(not_allowed, [])


if __name__ == "__main__":
    unittest.main()
