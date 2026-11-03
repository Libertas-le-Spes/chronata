import ast
import unittest
from pathlib import Path

PACKAGE = Path(__file__).parent.parent / "chronata"
CORE_MAY_IMPORT = {"collections", "dataclasses", "datetime", "difflib", "hashlib", "json", "typing", "unicodedata"}
CORE_MAY_NOT_CALL = {"open", "__import__", "eval", "exec", "compile", "input", "print", "breakpoint", "globals", "vars"}

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
        if isinstance(node, ast.ImportFrom):
            names.append(_imported_from(node))
    return names


def _imported_from(node: ast.ImportFrom) -> str:
    if node.level > 0 or node.module is None:
        return "a relative import"
    return node.module


def builtins_called_by(path: Path) -> list[str]:
    names = []
    for node in ast.walk(ast.parse(path.read_text())):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
            names.append(node.func.id)
    return names


def core_may_import(name: str) -> bool:
    if name.startswith("chronata.timekeeping."):
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
            for line, imported in imports_of(path):
                if ring_of(imported) not in allowed:
                    breaches.append(f"{path.relative_to(PACKAGE.parent)}:{line} ({ring_of(module)}) imports {imported}")
        self.assertEqual(breaches, [])

    def test_no_module_uses_a_relative_import_the_ring_check_would_not_see(self):
        relative = []
        for path in sorted(PACKAGE.rglob("*.py")):
            if "a relative import" in modules_imported_by(path):
                relative.append(str(path.relative_to(PACKAGE.parent)))
        self.assertEqual(relative, [])

    def test_the_core_imports_only_what_it_is_allowed(self):
        not_allowed = []
        for path in sorted((PACKAGE / "timekeeping").rglob("*.py")):
            for name in modules_imported_by(path):
                if not core_may_import(name):
                    not_allowed.append(f"{path.relative_to(PACKAGE.parent)} imports {name}")
        self.assertEqual(not_allowed, [])

    def test_the_core_calls_no_built_in_that_reads_files_or_runs_code(self):
        not_allowed = []
        for path in sorted((PACKAGE / "timekeeping").rglob("*.py")):
            for name in builtins_called_by(path):
                if name in CORE_MAY_NOT_CALL:
                    not_allowed.append(f"{path.relative_to(PACKAGE.parent)} calls {name}")
        self.assertEqual(not_allowed, [])

if __name__ == "__main__":
    unittest.main()
