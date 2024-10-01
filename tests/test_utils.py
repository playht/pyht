from pyht import utils


class TestSsmlRemoval:
    def test_happy_path(self):
        expected_text = "This sentence contains SSML tags."
        text = utils.prepare_text("<speak>This sentence contains SSML tags.</speak>")
        assert text == [expected_text]

    def test_no_op(self):
        expected_text = "already normalized text"
        text = utils.prepare_text(expected_text)
        assert text == [expected_text]
