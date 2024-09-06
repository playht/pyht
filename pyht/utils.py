from __future__ import annotations

import re
from typing import List


SENTENCE_END_REGEX = re.compile('.*[-.!?;:…]$')
SENTENCE_SPLIT_REGEX = re.compile('\\w[-.!?;:…]\\W')
BIG_SENTENCE_SPLIT_REGEX = re.compile('\\w[-.,!?;:…]\\W')  # Also split on comma.
REMOVE_NEWLINE = re.compile('(\\r?\\n\\r?)+')
NORMALIZE_WHITESPACE = re.compile('(\\t| )+')

MAX_LINE_COUNT = 6
HARD_LINE_MAX = 500
SOFT_LINE_MAX = 350
_WINDOW = 10


def normalize(text: str) -> str:
    return NORMALIZE_WHITESPACE.sub(" ", REMOVE_NEWLINE.sub(" ", text)).strip()


def ensure_sentence_end(text: list[str]) -> list[str]:
    if not text:
        return text
    if SENTENCE_END_REGEX.match(text[-1].strip()):
        return text
    return text[:-1] + [f"{text[-1].strip()}."]


def _split_index(text: str, soft_max: int, hard_max: int, window: int, pattern: re.Pattern) -> int:
    l_ptr = soft_max - window
    r_ptr = soft_max + window
    index = len(text)
    # for _ in range(soft_max // window * 2):
    while l_ptr >= 0 or r_ptr < len(text):
        if l_ptr < 0 and r_ptr > hard_max:
            raise ValueError(
                f"Unable to split text, sentence too long: ({len(text[:hard_max])} chars), {text[:hard_max]}"
            )
        if l_ptr >= 0:
            left = text[l_ptr:l_ptr + window]
            matches = [x for x in pattern.finditer(left)]
            if matches:
                index = l_ptr + matches[-1].span()[1]
                break
        if r_ptr < len(text) and r_ptr < hard_max:
            right = text[r_ptr - window:r_ptr]
            matches = [x for x in pattern.finditer(right)]
            if matches:
                index = r_ptr - window + matches[0].span()[1]
                break

        l_ptr -= window // 2
        r_ptr += window // 2

    return index


def split_text(
    text: str,
    hard_max: int = HARD_LINE_MAX,
    soft_max: int = SOFT_LINE_MAX,
    max_lines: int = MAX_LINE_COUNT,
    window: int = _WINDOW
) -> list[str]:
    if len(text) > max_lines * hard_max:
        raise ValueError(f'text too long: {len(text)} > {max_lines * hard_max}')

    if len(text) <= soft_max:
        return [text]

    output: list[str] = []
    for _ in range(max_lines):
        # End-of-text edge case:
        if len(text) <= soft_max:
            break
        try:
            index = _split_index(text, soft_max, hard_max, window, SENTENCE_SPLIT_REGEX)
        except ValueError as e:
            try:
                # Try again, but now split on commas, too.
                index = _split_index(text, soft_max, hard_max, window, BIG_SENTENCE_SPLIT_REGEX)
            except ValueError:
                raise e

        output.append(text[:index].strip())
        text = text[index:]

    if text:
        output.append(text.strip())
    return output


def prepare_text(text: str | List[str], remove_ssml_tags: bool = True) -> List[str]:
    if isinstance(text, str):
        text = split_text(text)
    if remove_ssml_tags:
        text = [re.sub(r'<[^>]*>', '', x) for x in text]
    text = [normalize(x) for x in text]
    text = ensure_sentence_end(text)
    return text
