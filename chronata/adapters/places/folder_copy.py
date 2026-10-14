import os
from pathlib import Path

from chronata.use_cases.ports import SaveError


def write_changed(folder: Path, bundle: dict[str, bytes]) -> None:
    try:
        for relative, content in bundle.items():
            path = folder / relative
            if path.exists() and path.read_bytes() == content:
                continue
            path.parent.mkdir(parents=True, exist_ok=True)
            temporary = path.with_name(f".{path.name}.chronata-tmp")
            temporary.write_bytes(content)
            os.replace(temporary, path)
    except OSError as error:
        raise SaveError(f"could not write to {folder}: {error.strerror or error}")
