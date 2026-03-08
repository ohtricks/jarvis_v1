"""
_diff_parser.py — Parsers para output de comandos `git diff`.
"""
from __future__ import annotations

import re


def parse_numstat(numstat_out: str) -> list[dict]:
    """
    Parseia output de `git diff --numstat`.

    Cada linha do git tem o formato:
        <adds>\t<dels>\t<filename>
    Para arquivos binários, adds/dels aparecem como "-".

    Retorna:
        [{file: str, additions: int, deletions: int}]
    """
    results: list[dict] = []
    for line in numstat_out.splitlines():
        line = line.strip()
        if not line:
            continue
        parts = line.split("\t", 2)
        if len(parts) < 3:
            continue
        adds_str, dels_str, fname = parts
        try:
            adds = int(adds_str) if adds_str != "-" else 0
            dels = int(dels_str) if dels_str != "-" else 0
        except ValueError:
            continue
        results.append({"file": fname.strip(), "additions": adds, "deletions": dels})
    return results


def parse_diff_sections(raw_diff: str) -> list[dict]:
    """
    Separa o output de `git diff` em seções por arquivo.

    Retorna:
        [{file: str, content: str}]
    onde content é o bloco completo do diff para aquele arquivo.
    """
    if not raw_diff:
        return []

    sections: list[dict] = []
    current_file: str | None = None
    current_lines: list[str] = []

    for line in raw_diff.splitlines():
        if line.startswith("diff --git "):
            # Salva seção anterior
            if current_file is not None:
                sections.append({
                    "file": current_file,
                    "content": "\n".join(current_lines),
                })
            # Extrai caminho: "diff --git a/path b/path" → path
            match = re.match(r"diff --git a/(.*?) b/(.*)$", line)
            current_file = match.group(2) if match else line
            current_lines = [line]
        elif current_file is not None:
            current_lines.append(line)

    if current_file is not None:
        sections.append({
            "file": current_file,
            "content": "\n".join(current_lines),
        })

    return sections


def merge_file_stats(
    unstaged: list[dict],
    staged: list[dict],
) -> list[dict]:
    """
    Merge de duas listas de numstat (unstaged + staged) sem duplicatas.

    Se um arquivo aparece em ambas, soma as linhas.
    """
    merged: dict[str, dict] = {}
    for entry in unstaged + staged:
        fname = entry["file"]
        if fname in merged:
            merged[fname]["additions"] += entry["additions"]
            merged[fname]["deletions"] += entry["deletions"]
        else:
            merged[fname] = dict(entry)
    return list(merged.values())
