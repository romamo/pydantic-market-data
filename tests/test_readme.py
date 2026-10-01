"""Run every ```python block in README.md against the current API.

A block that cannot run standalone is excluded explicitly by putting the marker
``<!-- readme-test: skip -->`` on the line directly before its opening fence.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pytest

README = Path(__file__).resolve().parent.parent / "README.md"
SKIP_MARKER = "<!-- readme-test: skip -->"
OPEN_FENCE = "```python"
CLOSE_FENCE = "```"


@dataclass(frozen=True)
class CodeBlock:
    line: int  # 1-based line number of the opening fence
    source: str
    skipped: bool


def extract_python_blocks(text: str) -> list[CodeBlock]:
    lines = text.splitlines()
    blocks: list[CodeBlock] = []
    index = 0
    while index < len(lines):
        if lines[index].strip() != OPEN_FENCE:
            index += 1
            continue
        start = index
        end = start + 1
        while end < len(lines) and lines[end].strip() != CLOSE_FENCE:
            end += 1
        if end == len(lines):
            raise ValueError(f"README.md:{start + 1}: unterminated ```python block")
        skipped = start > 0 and lines[start - 1].strip() == SKIP_MARKER
        blocks.append(CodeBlock(start + 1, "\n".join(lines[start + 1 : end]) + "\n", skipped))
        index = end + 1
    return blocks


BLOCKS = extract_python_blocks(README.read_text(encoding="utf-8"))


def test_readme_has_runnable_blocks() -> None:
    assert any(not block.skipped for block in BLOCKS)


def test_skip_markers_only_precede_python_blocks() -> None:
    lines = README.read_text(encoding="utf-8").splitlines()
    for number, line in enumerate(lines, start=1):
        if line.strip() == SKIP_MARKER:
            assert number < len(lines) and lines[number].strip() == OPEN_FENCE, (
                f"README.md:{number}: skip marker is not directly before a ```python fence"
            )


@pytest.mark.parametrize(
    "block",
    [
        pytest.param(
            block,
            id=f"README.md:{block.line}",
            marks=pytest.mark.skip(reason=SKIP_MARKER) if block.skipped else (),
        )
        for block in BLOCKS
    ],
)
def test_readme_python_block_runs(block: CodeBlock) -> None:
    code = compile(block.source, f"README.md:{block.line}", "exec")
    exec(code, {"__name__": "__readme__"})  # nosec B102 - executes the repo's own README
