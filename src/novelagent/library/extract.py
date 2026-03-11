from __future__ import annotations

import re
from pathlib import Path


CHAPTER_RE = re.compile(r"第(\d{1,5})章")


def extract_first_n_chapters(src: Path, dst: Path, n: int) -> int:
    """
    Extract text from the beginning of src up to (and including) chapter n.
    Chapters are detected by the first occurrence of '第xxx章' patterns.
    Returns the max chapter number included (best-effort).
    """
    if n <= 0:
        raise ValueError("n must be > 0")
    dst.parent.mkdir(parents=True, exist_ok=True)

    current_max = 0
    seen_next_start = False

    with src.open("r", encoding="utf-8", errors="replace") as fin, dst.open("w", encoding="utf-8") as fout:
        for line in fin:
            m = CHAPTER_RE.search(line)
            if m:
                chap = int(m.group(1))
                if chap > current_max:
                    current_max = chap
                if chap == n + 1:
                    seen_next_start = True
                    break
            fout.write(line)

    if not seen_next_start:
        return current_max
    return min(current_max, n)

