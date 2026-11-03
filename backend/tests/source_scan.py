import ast

WHOLE_PACKAGE = "chronata"


class Source:
    def __init__(self, text: str):
        self.tree = ast.parse(text)

    def chronata_imports(self) -> list[tuple[int, str]]:
        found = []
        for node in ast.walk(self.tree):
            if isinstance(node, ast.Import):
                found += _chronata_names(node.lineno, [alias.name for alias in node.names])
            if isinstance(node, ast.ImportFrom):
                found += _chronata_names(node.lineno, _from_names(node))
        return found

    def modules(self) -> list[str]:
        names = []
        for node in ast.walk(self.tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    names.append(alias.name)
            if isinstance(node, ast.ImportFrom) and node.module is not None:
                names.append(node.module)
        return names

    def names_imported_from(self) -> list[tuple[str, str]]:
        found = []
        for node in ast.walk(self.tree):
            if isinstance(node, ast.ImportFrom) and node.level == 0 and node.module is not None:
                for alias in node.names:
                    found.append((node.module, alias.name))
        return found

    def modules_bound(self) -> dict[str, str]:
        bound = {}
        for node in ast.walk(self.tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    bound[_bound_name(alias)] = alias.name
        return bound

    def attributes_of(self, name: str) -> list[str]:
        found = []
        for node in ast.walk(self.tree):
            if isinstance(node, ast.Attribute) and isinstance(node.value, ast.Name) and node.value.id == name:
                found.append(node.attr)
        return found

    def has_relative_import(self) -> bool:
        for node in ast.walk(self.tree):
            if isinstance(node, ast.ImportFrom) and node.level > 0:
                return True
        return False

    def names_used(self) -> set[str]:
        used = set()
        for node in ast.walk(self.tree):
            if isinstance(node, ast.Name):
                used.add(node.id)
        return used

    def attributes_used(self) -> set[str]:
        used = set()
        for node in ast.walk(self.tree):
            if isinstance(node, ast.Attribute):
                used.add(node.attr)
        return used


def _bound_name(alias: ast.alias) -> str:
    if alias.asname is not None:
        return alias.asname
    return alias.name.split(".")[0]


def _from_names(node: ast.ImportFrom) -> list[str]:
    if node.module != WHOLE_PACKAGE:
        return [node.module]
    names = []
    for alias in node.names:
        names.append(f"{WHOLE_PACKAGE}.{alias.name}")
    return names


def _chronata_names(line: int, names: list[str]) -> list[tuple[int, str]]:
    found = []
    for name in names:
        if name is not None and _inside_chronata(name):
            found.append((line, name))
    return found


def _inside_chronata(name: str) -> bool:
    return name == WHOLE_PACKAGE or name.startswith(f"{WHOLE_PACKAGE}.")
