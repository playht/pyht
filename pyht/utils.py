from __future__ import annotations
import re


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


if __name__ == '__main__':
    import unittest

    class NormalizeTests(unittest.TestCase):
        def test_happy_path(self):
            text = normalize(" This  sentence\r\ncontains\ttoo many and the \t\twrong type\n\nof\nspaces.\n")
            expected_text = "This sentence contains too many and the wrong type of spaces."
            self.assertEqual(text, expected_text)

        def test_no_op(self):
            text = "already normalized text"
            self.assertEqual(text, normalize(text))

    class EnsureSentenceEndTests(unittest.TestCase):
        def test_happy_path(self):
            expected_text = "This is a sentence."
            text = ensure_sentence_end([expected_text[:-1]])
            self.assertListEqual(text, [expected_text])

        def test_no_op(self):
            expected_text = ["This is a sentence."]
            text = ensure_sentence_end(expected_text)
            self.assertListEqual(text, expected_text)

        def test_only_last_entry(self):
            expected_text = ["this is not a sentence ending, ", "but this is."]
            text = ensure_sentence_end(expected_text[:-1] + [expected_text[-1][:-1]])
            self.assertListEqual(text, expected_text)

        def test_whitespace_ignored(self):
            expected_text = "This is a sentence."
            text = ensure_sentence_end([expected_text.replace(".", " ")])
            self.assertListEqual(text, [expected_text])

        def test_whitespace_ignored_no_op(self):
            expected_text = ["This is a sentence. "]
            text = ensure_sentence_end(expected_text)
            self.assertListEqual(text, expected_text)

    class SplitTests(unittest.TestCase):
        @property
        def sample_text(self) -> str:
            return (
                "The world is vast, filled with endless wonders and mysteries. Throughout history, people have sought "
                "answers, gazing at stars, scaling peaks, and diving deep, ever driven by insatiable curiosity. Every "
                "sunrise is nature's masterpiece, a vibrant blend of hues. Each dawn, colors dance, reminding us anew "
                "of life's beauty, fleeting moments to cherish, fleeting yet eternally unforgettable. In the depths of "
                "oceans, mysteries and wonders abound. From luminescent creatures to ancient shipwrecks, there's a "
                "world waiting to be explored, a testament to life's boundless diversity. Small towns have a rhythm, a "
                "heartbeat unique to them. Beneath a calm exterior, tales of love, adventure, and intrigue unfold, "
                "waiting for someone to listen, to discover, and to share. Modern cities echo with countless stories "
                "and dreams. Every corner, every street, every building has a narrative, a blend of histories and "
                "hopes, all unfolding in real-time, every single day. Timeless libraries, silent and vast, are portals "
                "to other worlds. Amidst their stacks, tales of the past, present, and future beckon, each page a door "
                "to knowledge and imagination. Nature, in its quiet moments, whispers profound truths. The rustle of "
                "leaves, the distant call of a bird, each sound is a note in a grand symphony that speaks of life's "
                "intricate dance. Every artist, with passion and skill, creates magic. Each canvas becomes a world, "
                "every brushstroke a narrative, capturing emotions, dreams, and memories in vibrant, unending colors. "
                "The realm of technology is ceaselessly evolving, expanding. New inventions reshape our lives, "
                "redefine boundaries, and challenge conventions, pushing us toward an unknown horizon. Books transport "
                "us to realms beyond reality. Immersed in a tale, boundaries blur, and for a while, the heartbeats of "
                "characters become ours, their joys, sorrows, and dreams intertwined with ours."
            )

        @property
        def sample_text_commas_only(self) -> str:
            """Sample text with only commas as break points."""
            return self.sample_text.replace(".", "")

        @property
        def sample_text_no_breaks(self) -> str:
            """Sample text as a complete run-on sentence."""
            return self.sample_text_commas_only.replace(",", "")

        @property
        def sample_sentences(self) -> list[str]:
            """Sample text as a list of sentences."""
            return [x.strip() for x in self.sample_text.split(".")]

        def test_happy_path(self):
            text = split_text(self.sample_text)
            self.assertGreater(len(text), 1)
            self.assertEqual(self.sample_text, " ".join(text))

        def test_simple_text_no_op(self):
            expected_text = "hello"
            text = split_text(expected_text)
            self.assertListEqual(text, [expected_text])

        def test_simple_sentence_no_op(self):
            expected_text = self.sample_sentences[0]
            text = split_text(expected_text)
            self.assertListEqual(text, [expected_text])

        def test_soft_max_no_op(self):
            expected_text = self.sample_text[:SOFT_LINE_MAX]
            text = split_text(expected_text, soft_max=SOFT_LINE_MAX)
            self.assertListEqual(text, [expected_text])

        def test_splits_between_soft_and_hard_max(self):
            length = SOFT_LINE_MAX + (HARD_LINE_MAX - SOFT_LINE_MAX) // 2
            expected_text = self.sample_text[:length]
            text = split_text(expected_text, soft_max=SOFT_LINE_MAX, hard_max=HARD_LINE_MAX)
            self.assertGreater(len(text), 1)
            self.assertEqual(expected_text, " ".join(text))

        def test_between_soft_and_hard_max_no_op(self):
            length = SOFT_LINE_MAX + (HARD_LINE_MAX - SOFT_LINE_MAX) // 2
            expected_text = self.sample_text_no_breaks[:length]
            text = split_text(expected_text, soft_max=SOFT_LINE_MAX, hard_max=HARD_LINE_MAX)
            self.assertListEqual(text, [expected_text])

        def test_comma_fallback(self):
            text = split_text(self.sample_text_commas_only)
            self.assertGreater(len(text), 1)
            self.assertEqual(self.sample_text_commas_only, " ".join(text))

        def test_text_too_long_fails(self):
            with self.assertRaisesRegex(ValueError, "text too long:"):
                split_text(f"{self.sample_text} {self.sample_text}")

        def test_sentence_too_long_fails(self):
            with self.assertRaisesRegex(ValueError, "Unable to split text, sentence too long:"):
                split_text(self.sample_text_no_breaks)

    unittest.main()
