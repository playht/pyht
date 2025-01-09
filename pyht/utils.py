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


def _convert_deprecated_voice_engine(voice_engine: str, protocol: Optional[str]) -> Tuple[str, str]:
    _voice_engine, _protocol = voice_engine.rsplit("-", 1)
    if not protocol or protocol == _protocol:
        logging.warning(f"Voice engine {_voice_engine}-{_protocol} is deprecated; \
                        separately pass voice_engine='{_voice_engine}' and protocol='{_protocol}'.")
        return _voice_engine, _protocol
    else:
        raise ValueError(f"Got voice engine of deprecated format {voice_engine} \
                         as well as mismatched protocol {protocol}.")


def get_voice_engine_and_protocol(voice_engine: Optional[str], protocol: Optional[str]) -> Tuple[str, str]:
    if protocol and protocol not in ["http", "ws", "grpc"]:
        raise ValueError(f"Invalid protocol: {protocol} (must be http, ws, or grpc).")

    # this is a bunch of tedious backward compatibility

    if not voice_engine:
        if not protocol:
            logging.warning("No voice engine or protocol specified; using Play3.0-mini-http.")
            voice_engine = "Play3.0-mini"
            protocol = "http"
        elif protocol in ["http", "ws"]:
            logging.warning(f"No voice engine specified and protocol is {protocol}; using Play3.0-mini-{protocol}.")
            voice_engine = "Play3.0-mini"
        elif protocol == "grpc":
            logging.warning("No voice engine specified and protocol is grpc; using PlayHT2.0-turbo.")
            voice_engine = "PlayHT2.0-turbo"
        else:
            raise ValueError(f"No voice engine specified and invalid protocol {protocol} (must be http, ws, or grpc).")

    elif voice_engine == "PlayHT2.0-turbo":
        if not protocol:
            protocol = "grpc"
        if protocol != "grpc":
            raise ValueError(f"Voice engine PlayHT2.0-turbo does not support protocol {protocol} (must be grpc).")

    elif voice_engine in ["Play3.0-mini", "Play3.0-mini-http", "Play3.0-mini-ws", "Play3.0-mini-grpc",
                          "Play3.0", "Play3.0-http", "Play3.0-ws", "Play3.0-grpc"]:
        if "mini" not in voice_engine:
            logging.warning("Voice engine Play3.0 is deprecated; use Play3.0-mini.")
            voice_engine = voice_engine.replace("Play3.0", "Play3.0-mini")
        if voice_engine == "Play3.0-mini":
            if not protocol:
                logging.warning("No protocol specified; using http")
                protocol = "http"
            if protocol not in ["http", "ws", "grpc"]:
                raise ValueError(f"Voice engine Play3.0-mini does not support protocol {protocol} \
                                 (must be http, ws, or grpc [grpc for on-prem customers only]).")
        else:
            voice_engine, protocol = _convert_deprecated_voice_engine(voice_engine, protocol)

    elif voice_engine in ["PlayDialog", "PlayDialog-http", "PlayDialog-ws", "PlayDialogMultilingual",
                          "PlayDialogMultilingual-http", "PlayDialogMultilingual-ws"]:
        if voice_engine in ["PlayDialog", "PlayDialogMultilingual"]:
            if not protocol:
                logging.warning("No protocol specified; using http")
                protocol = "http"
            if protocol not in ["http", "ws"]:
                raise ValueError(f"Voice engine {voice_engine} does not support protocol {protocol} \
                                 (must be http or ws).")
        else:
            voice_engine, protocol = _convert_deprecated_voice_engine(voice_engine, protocol)

    else:
        raise ValueError(f"Invalid voice engine: {voice_engine} (must be Play3.0-mini, PlayDialog, \
                         PlayDialogMultilingual, or PlayHT2.0-turbo).")

    return voice_engine, protocol


def main():
    assert get_voice_engine_and_protocol(None, "http") == ("Play3.0-mini", "http")
    assert get_voice_engine_and_protocol("", "http") == ("Play3.0-mini", "http")
    assert get_voice_engine_and_protocol(None, "ws") == ("Play3.0-mini", "ws")
    assert get_voice_engine_and_protocol("", "ws") == ("Play3.0-mini", "ws")
    assert get_voice_engine_and_protocol(None, None) == ("Play3.0-mini", "http")
    assert get_voice_engine_and_protocol("", None) == ("Play3.0-mini", "http")
    assert get_voice_engine_and_protocol(None, "") == ("Play3.0-mini", "http")
    assert get_voice_engine_and_protocol("", "") == ("Play3.0-mini", "http")
    assert get_voice_engine_and_protocol("Play3.0-mini", "http") == ("Play3.0-mini", "http")
    assert get_voice_engine_and_protocol("Play3.0-mini", "ws") == ("Play3.0-mini", "ws")
    assert get_voice_engine_and_protocol("Play3.0-mini", "grpc") == ("Play3.0-mini", "grpc")
    assert get_voice_engine_and_protocol("Play3.0-mini", None) == ("Play3.0-mini", "http")
    assert get_voice_engine_and_protocol("Play3.0-mini", "") == ("Play3.0-mini", "http")
    assert get_voice_engine_and_protocol("Play3.0-mini-http", "http") == ("Play3.0-mini", "http")
    assert get_voice_engine_and_protocol("Play3.0-mini-http", None) == ("Play3.0-mini", "http")
    assert get_voice_engine_and_protocol("Play3.0-mini-http", "") == ("Play3.0-mini", "http")
    assert get_voice_engine_and_protocol("Play3.0-mini-ws", "ws") == ("Play3.0-mini", "ws")
    assert get_voice_engine_and_protocol("Play3.0-mini-ws", None) == ("Play3.0-mini", "ws")
    assert get_voice_engine_and_protocol("Play3.0-mini-ws", "") == ("Play3.0-mini", "ws")
    assert get_voice_engine_and_protocol("Play3.0-mini-grpc", "grpc") == ("Play3.0-mini", "grpc")
    assert get_voice_engine_and_protocol("Play3.0-mini-grpc", None) == ("Play3.0-mini", "grpc")
    assert get_voice_engine_and_protocol("Play3.0-mini-grpc", "") == ("Play3.0-mini", "grpc")
    assert get_voice_engine_and_protocol("Play3.0", "http") == ("Play3.0-mini", "http")
    assert get_voice_engine_and_protocol("Play3.0", "ws") == ("Play3.0-mini", "ws")
    assert get_voice_engine_and_protocol("Play3.0", "grpc") == ("Play3.0-mini", "grpc")
    assert get_voice_engine_and_protocol("Play3.0", None) == ("Play3.0-mini", "http")
    assert get_voice_engine_and_protocol("Play3.0", "") == ("Play3.0-mini", "http")
    assert get_voice_engine_and_protocol("Play3.0-http", "http") == ("Play3.0-mini", "http")
    assert get_voice_engine_and_protocol("Play3.0-http", None) == ("Play3.0-mini", "http")
    assert get_voice_engine_and_protocol("Play3.0-http", "") == ("Play3.0-mini", "http")
    assert get_voice_engine_and_protocol("Play3.0-ws", "ws") == ("Play3.0-mini", "ws")
    assert get_voice_engine_and_protocol("Play3.0-ws", None) == ("Play3.0-mini", "ws")
    assert get_voice_engine_and_protocol("Play3.0-ws", "") == ("Play3.0-mini", "ws")
    assert get_voice_engine_and_protocol("Play3.0-grpc", "grpc") == ("Play3.0-mini", "grpc")
    assert get_voice_engine_and_protocol("Play3.0-grpc", None) == ("Play3.0-mini", "grpc")
    assert get_voice_engine_and_protocol("Play3.0-grpc", "") == ("Play3.0-mini", "grpc")

    assert get_voice_engine_and_protocol("PlayDialog", "http") == ("PlayDialog", "http")
    assert get_voice_engine_and_protocol("PlayDialog", "ws") == ("PlayDialog", "ws")
    assert get_voice_engine_and_protocol("PlayDialog", None) == ("PlayDialog", "http")
    assert get_voice_engine_and_protocol("PlayDialog", "") == ("PlayDialog", "http")
    assert get_voice_engine_and_protocol("PlayDialog-http", "http") == ("PlayDialog", "http")
    assert get_voice_engine_and_protocol("PlayDialog-http", None) == ("PlayDialog", "http")
    assert get_voice_engine_and_protocol("PlayDialog-http", "") == ("PlayDialog", "http")
    assert get_voice_engine_and_protocol("PlayDialog-ws", "ws") == ("PlayDialog", "ws")
    assert get_voice_engine_and_protocol("PlayDialog-ws", None) == ("PlayDialog", "ws")
    assert get_voice_engine_and_protocol("PlayDialog-ws", "") == ("PlayDialog", "ws")

    assert get_voice_engine_and_protocol("PlayDialogMultilingual", "http") == ("PlayDialogMultilingual", "http")
    assert get_voice_engine_and_protocol("PlayDialogMultilingual", "ws") == ("PlayDialogMultilingual", "ws")
    assert get_voice_engine_and_protocol("PlayDialogMultilingual", None) == ("PlayDialogMultilingual", "http")
    assert get_voice_engine_and_protocol("PlayDialogMultilingual", "") == ("PlayDialogMultilingual", "http")
    assert get_voice_engine_and_protocol("PlayDialogMultilingual-http", "http") == ("PlayDialogMultilingual", "http")
    assert get_voice_engine_and_protocol("PlayDialogMultilingual-http", None) == ("PlayDialogMultilingual", "http")
    assert get_voice_engine_and_protocol("PlayDialogMultilingual-http", "") == ("PlayDialogMultilingual", "http")
    assert get_voice_engine_and_protocol("PlayDialogMultilingual-ws", "ws") == ("PlayDialogMultilingual", "ws")
    assert get_voice_engine_and_protocol("PlayDialogMultilingual-ws", None) == ("PlayDialogMultilingual", "ws")
    assert get_voice_engine_and_protocol("PlayDialogMultilingual-ws", "") == ("PlayDialogMultilingual", "ws")

    assert get_voice_engine_and_protocol(None, "grpc") == ("PlayHT2.0-turbo", "grpc")
    assert get_voice_engine_and_protocol("", "grpc") == ("PlayHT2.0-turbo", "grpc")
    assert get_voice_engine_and_protocol("PlayHT2.0-turbo", "grpc") == ("PlayHT2.0-turbo", "grpc")
    assert get_voice_engine_and_protocol("PlayHT2.0-turbo", None) == ("PlayHT2.0-turbo", "grpc")
    assert get_voice_engine_and_protocol("PlayHT2.0-turbo", "") == ("PlayHT2.0-turbo", "grpc")


if __name__ == "__main__":
    main()
