"""Shared text helpers for ATS normalization."""

from __future__ import annotations

import html
import re
from html.parser import HTMLParser


class _HTMLToText(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self._parts: list[str] = []

    def handle_data(self, data: str) -> None:
        if data:
            self._parts.append(data)

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag in {"p", "br", "li", "div", "h1", "h2", "h3", "h4", "tr"}:
            self._parts.append("\n")

    def text(self) -> str:
        return "".join(self._parts)


def html_to_text(value: str) -> str:
    """Strip HTML to plain text for keyword filters and matching prompts."""
    parser = _HTMLToText()
    parser.feed(value)
    parser.close()
    text = html.unescape(parser.text())
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()
