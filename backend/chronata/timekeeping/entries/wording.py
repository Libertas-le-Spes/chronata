def quoted(text: str | None) -> str:
    return f"“{text.strip()}”" if text and text.strip() else ""


def detail(*parts: str) -> str:
    return " · ".join(part for part in parts if part)
