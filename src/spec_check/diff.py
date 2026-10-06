"""Minimal unified-diff parser: per file, which lines exist before/after the change."""

import re
from dataclasses import dataclass, field

_HUNK_HEADER = re.compile(r"^@@ -\d+(?:,(\d+))? \+\d+(?:,(\d+))? @@")


@dataclass
class FileDiff:
    path: str
    new_lines: list[str] = field(default_factory=list)  # context + added lines
    old_lines: list[str] = field(default_factory=list)  # context + removed lines
    added_lines: list[str] = field(default_factory=list)


def parse_diff(text: str) -> dict[str, FileDiff]:
    """Return {path: FileDiff}. Paths are relative, without the a/ b/ prefixes."""
    files: dict[str, FileDiff] = {}
    current: FileDiff | None = None
    old_path = ""
    lines = text.splitlines()
    i = 0
    while i < len(lines):
        line = lines[i]
        if line.startswith("--- "):
            old_path = _clean_header_path(line[4:])
        elif line.startswith("+++ "):
            path = _clean_header_path(line[4:])
            if path == "/dev/null":  # deleted file: keep the old name
                path = old_path
            current = files.setdefault(path, FileDiff(path=path))
        elif current is not None and (header := _HUNK_HEADER.match(line)):
            old_count = int(header.group(1) or 1)
            new_count = int(header.group(2) or 1)
            # Consume exactly the number of lines the hunk header announces, so a
            # removed line that happens to start with "--" is not mistaken for a header.
            i += 1
            while i < len(lines) and (old_count > 0 or new_count > 0):
                body = lines[i]
                tag, content = body[:1], body[1:]
                if tag == "+":
                    current.new_lines.append(content)
                    current.added_lines.append(content)
                    new_count -= 1
                elif tag == "-":
                    current.old_lines.append(content)
                    old_count -= 1
                elif tag == "\\":  # "\ No newline at end of file"
                    pass
                else:  # context line (a space, or empty for a blank context line)
                    current.new_lines.append(content)
                    current.old_lines.append(content)
                    old_count -= 1
                    new_count -= 1
                i += 1
            continue
        i += 1
    return files


def _clean_header_path(raw: str) -> str:
    path = raw.split("\t")[0].strip()
    if path.startswith(("a/", "b/")):
        path = path[2:]
    return path


def is_test_file(path: str) -> bool:
    path = "/" + path.replace("\\", "/")
    name = path.rsplit("/", 1)[-1]
    return (
        name.startswith("test_")
        or name.endswith(("_test.py", ".test.ts", ".test.js", ".spec.ts", ".spec.js"))
        or "/tests/" in path
    )
