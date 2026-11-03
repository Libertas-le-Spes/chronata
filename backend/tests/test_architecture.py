import ast
import unittest
from pathlib import Path

PACKAGE = Path(__file__).parent.parent / "chronata"
REACHES_OUTSIDE = {"subprocess", "urllib", "http", "socket", "os", "fcntl", "webbrowser", "threading", "pathlib", "shutil", "tempfile", "ssl", "requests"}

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


def imports_of(path: Path) -> list[tuple[int, str]]:
    found = []
    for node in ast.walk(ast.parse(path.read_text())):
        if isinstance(node, ast.ImportFrom) and node.module and node.module.startswith("chronata."):
            found.append((node.lineno, node.module))
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name.startswith("chronata."):
                    found.append((node.lineno, alias.name))
    return found


def modules_imported_by(path: Path) -> list[str]:
    names = []
    for node in ast.walk(ast.parse(path.read_text())):
        if isinstance(node, ast.Import):
            for alias in node.names:
                names.append(alias.name)
        if isinstance(node, ast.ImportFrom) and node.module is not None:
            names.append(node.module)
    return names


class DependenciesPointInward(unittest.TestCase):
    def test_no_ring_imports_a_ring_outside_it(self):
        breaches = []
        for path in sorted(PACKAGE.rglob("*.py")):
            module = ".".join(path.relative_to(PACKAGE.parent).with_suffix("").parts)
            if module in ("chronata.__main__", "chronata.__init__"):
                continue
            allowed = MAY_IMPORT[ring_of(module)]
            for line, imported in imports_of(path):
                if ring_of(imported) not in allowed:
                    breaches.append(f"{path.relative_to(PACKAGE.parent)}:{line} ({ring_of(module)}) imports {imported}")
        self.assertEqual(breaches, [])

    def test_the_core_reaches_nothing_outside_this_computers_memory(self):
        reaching_out = []
        for path in sorted((PACKAGE / "timekeeping").rglob("*.py")):
            for name in modules_imported_by(path):
                if name.split(".")[0] in REACHES_OUTSIDE:
                    reaching_out.append(f"{path.relative_to(PACKAGE.parent)} imports {name}")
        self.assertEqual(reaching_out, [])


if __name__ == "__main__":
    unittest.main()
