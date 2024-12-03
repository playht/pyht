from __future__ import annotations

import re
from typing import List, Union

SENTENCE_END_REGEX = re.compile('.*[-.!?;:…]$')


def prepare_text(text: Union[str, List[str]], remove_ssml_tags: bool = True) -> List[str]:
    if isinstance(text, str):
        text = [text]
    if remove_ssml_tags:
        text = [re.sub(r'<[^>]*>', '', x) for x in text]
    return text
