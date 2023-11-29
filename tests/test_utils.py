import pytest

from pyht import utils


@pytest.fixture(scope="module")
def sample_text() -> str:
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


@pytest.fixture(autouse=True, scope="class")
def _wire_fixtures(request, sample_text):
    request.cls.sample_text = sample_text
    request.cls.sample_text_commas_only = sample_text.replace(".", "")
    request.cls.sample_text_no_breaks = request.cls.sample_text_commas_only.replace(",", "")
    request.cls.sample_sentences = [x.strip() for x in sample_text.split(".")]


class TestNormalize:
    def test_happy_path(self):
        text = utils.normalize(" This  sentence\r\ncontains\ttoo many and the \t\twrong type\n\nof\nspaces.\n")
        expected_text = "This sentence contains too many and the wrong type of spaces."
        assert text == expected_text

    def test_no_op(self):
        text = "already normalized text"
        assert text == utils.normalize(text)


class TestEnsureSentenceEnd:
    def test_happy_path(self):
        expected_text = "This is a sentence."
        text = utils.ensure_sentence_end([expected_text[:-1]])
        assert text == [expected_text]

    def test_no_op(self):
        expected_text = ["This is a sentence."]
        text = utils.ensure_sentence_end(expected_text)
        assert text == expected_text

    def test_only_last_entry(self):
        expected_text = ["this is not a sentence ending, ", "but this is."]
        text = utils.ensure_sentence_end(expected_text[:-1] + [expected_text[-1][:-1]])
        assert text == expected_text

    def test_whitespace_ignored(self):
        expected_text = "This is a sentence."
        text = utils.ensure_sentence_end([expected_text.replace(".", " ")])
        assert text == [expected_text]

    def test_whitespace_ignored_no_op(self):
        expected_text = ["This is a sentence. "]
        text = utils.ensure_sentence_end(expected_text)
        assert text == expected_text


class TestSplitText:

    def test_happy_path(self):
        text = utils.split_text(self.sample_text)
        assert len(text) > 1
        assert self.sample_text == " ".join(text)

    def test_simple_text_no_op(self):
        expected_text = "hello"
        text = utils.split_text(expected_text)
        assert text == [expected_text]

    def test_simple_sentence_no_op(self):
        expected_text = self.sample_sentences[0]
        text = utils.split_text(expected_text)
        assert text == [expected_text]

    def test_soft_max_no_op(self):
        expected_text = self.sample_text[:utils.SOFT_LINE_MAX]
        text = utils.split_text(expected_text, soft_max=utils.SOFT_LINE_MAX)
        assert text == [expected_text]

    def test_splits_between_soft_and_hard_max(self):
        length = utils.SOFT_LINE_MAX + (utils.HARD_LINE_MAX - utils.SOFT_LINE_MAX) // 2
        expected_text = self.sample_text[:length]
        text = utils.split_text(expected_text, soft_max=utils.SOFT_LINE_MAX, hard_max=utils.HARD_LINE_MAX)
        assert len(text) > 1
        assert expected_text == " ".join(text)

    def test_between_soft_and_hard_max_no_op(self):
        length = utils.SOFT_LINE_MAX + (utils.HARD_LINE_MAX - utils.SOFT_LINE_MAX) // 2
        expected_text = self.sample_text_no_breaks[:length]
        text = utils.split_text(expected_text, soft_max=utils.SOFT_LINE_MAX, hard_max=utils.HARD_LINE_MAX)
        assert text == [expected_text]

    def test_comma_fallback(self):
        text = utils.split_text(self.sample_text_commas_only)
        assert len(text) > 1
        assert self.sample_text_commas_only == " ".join(text)

    def test_text_too_long_fails(self):
        with pytest.raises(ValueError, match="text too long:"):
        # with assertRaisesRegex(ValueError, "text too long:"):
            utils.split_text(f"{self.sample_text} {self.sample_text}")

    def test_sentence_too_long_fails(self):
        with pytest.raises(ValueError, match="Unable to split text, sentence too long:"):
        # with assertRaisesRegex(ValueError, "Unable to split text, sentence too long:"):
            utils.split_text(self.sample_text_no_breaks)
