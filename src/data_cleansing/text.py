"""Clean names, bracketed annotations, and delimited text."""

import re

from ._scalars import is_missing


def split_text(name: str | None, symbol: str) -> list[str]:
    """Split text and discard empty and n.a. fields."""
    if is_missing(name):
        return ["Empty"]
    return [part for part in name.split(symbol) if part not in ("", "n.a.")]


def clean_car_model(text_0: object) -> str:
    """Uppercase and trim a car model, dropping its parenthetical suffix."""
    return "" if is_missing(text_0) else str(text_0).partition("(")[0].strip().upper()


def complete_model_name(brand: str | None, model_name: str | None) -> str:
    """Uppercase a model name and prepend the brand if it is absent."""
    brand = "" if is_missing(brand) else brand.upper()
    model_name = "" if is_missing(model_name) else model_name.upper()
    return model_name if brand in model_name else f"{brand} {model_name}".strip()


def clean_province(text: object) -> object:
    """Remove administrative suffixes used in Chinese province names."""
    if is_missing(text):
        return text
    cleaned = str(text)
    for suffix in ("省", "市", "自治区", "壮族", "维吾尔", "回族"):
        cleaned = cleaned.replace(suffix, "")
    return cleaned


def find_content_in_bracket(name: str | None) -> str | list[str]:
    """Extract text in parentheses, or return an empty string if absent."""
    if is_missing(name) or "(" not in name:
        return ""
    return re.findall(r"\((.*?)\)", name, flags=re.DOTALL)


def clean_content_in_bracket(name: str | None) -> str:
    """Remove parenthetical annotations and trim the remaining text."""
    return "" if is_missing(name) else re.sub(r"\(.*?\)", "", name).strip()


def find_content_in_square_bracket(name: str | None) -> str | list[str]:
    """Extract text in square brackets, or return an empty string if absent."""
    if is_missing(name) or "[" not in name:
        return ""
    return re.findall(r"\[(.*?)\]", name, flags=re.DOTALL)


def clean_content_in_square_bracket(name: str | None) -> str:
    """Remove square-bracketed annotations and trim the remaining text."""
    return "" if is_missing(name) else re.sub(r"\[.*?\]", "", name).strip()


def clean_name_space(name: str | None) -> str:
    """Normalize horizontal whitespace and add a space before opening brackets."""
    if is_missing(name):
        return ""
    return re.sub(r"[ \t]+", " ", name.replace("[", " [").replace("(", " (")).strip()


def complete_bracket(name: str | None) -> str:
    """Append closing parentheses for excess opening parentheses."""
    if is_missing(name):
        return ""
    return name + ")" * (name.count("(") - name.count(")"))


def complete_square_bracket(name: str | None) -> str:
    """Append closing square brackets for excess opening brackets."""
    if is_missing(name):
        return ""
    return name + "]" * (name.count("[") - name.count("]"))


def clean_content_before_colon(name: str | None) -> str:
    """Return the trimmed text after the final ASCII or full-width colon."""
    return "" if is_missing(name) else name.replace("：", ":").rsplit(":", 1)[-1].strip()
