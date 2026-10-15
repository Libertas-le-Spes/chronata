import ast
import unittest
from pathlib import Path

PACKAGE = Path(__file__).parent.parent / "chronata"

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
            found += [(node.lineno, alias.name) for alias in node.names if alias.name.startswith("chronata.")]
    return found


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

    def test_the_core_needs_nothing_but_the_standard_library(self):
        outside = {"subprocess", "urllib", "http", "socket", "os", "fcntl", "webbrowser", "threading", "pathlib"}
        for path in (PACKAGE / "timekeeping").glob("*.py"):
            for node in ast.walk(ast.parse(path.read_text())):
                names = [a.name for a in node.names] if isinstance(node, ast.Import) else [node.module or ""] if isinstance(node, ast.ImportFrom) else []
                for name in names:
                    self.assertNotIn(name.split(".")[0], outside, f"{path.name} reaches outside with {name}")


if __name__ == "__main__":
    unittest.main()
