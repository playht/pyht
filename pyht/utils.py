from __future__ import annotations

import logging
import re
from typing import List, Union, Tuple, Optional

SENTENCE_END_REGEX = re.compile('.*[-.!?;:…]$')


def prepare_text(text: Union[str, List[str]], remove_ssml_tags: bool = True) -> List[str]:
    if isinstance(text, str):
        text = [text]
    if remove_ssml_tags:
        text = [re.sub(r'<[^>]*>', '', x) for x in text]
    return text


def get_voice_engine_and_protocol(voice_engine: Optional[str]) -> Tuple[str, str]:
    if voice_engine is None:
        logging.warning("No voice engine specified; using Play3.0-mini-http")
        voice_engine = "Play3.0-mini"
        protocol = "http"
    elif voice_engine == "PlayHT2.0-turbo":
        protocol = "grpc"
    elif voice_engine == "Play3.0":
        logging.warning("Voice engine Play3.0 is deprecated; use Play3.0-mini-http or Play3.0-mini-ws instead.")
        logging.warning("No protocol specified; using HTTP (if not desired, append '-ws' to the voice engine)")
        voice_engine = "Play3.0-mini"
        protocol = "http"
    elif voice_engine == "Play3.0-http":
        logging.warning("Voice engine Play3.0-http is deprecated; use Play3.0-mini-http instead.")
        voice_engine = "Play3.0-mini"
        protocol = "http"
    elif voice_engine == "Play3.0-ws":
        logging.warning("Voice engine Play3.0-ws is deprecated; use Play3.0-mini-ws instead.")
        voice_engine = "Play3.0-mini"
        protocol = "ws"
    elif voice_engine == "Play3.0-mini" or voice_engine == "PlayDialog" or voice_engine == "PlayDialogMultilingual":
        logging.warning("No protocol specified; using HTTP (if not desired, append '-ws' to the voice engine)")
        protocol = "http"
    else:
        voice_engine, protocol = voice_engine.rsplit("-", 1)

    return voice_engine, protocol
