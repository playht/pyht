from __future__ import annotations
from typing import Iterable, Literal

import time

import numpy as np
import simpleaudio as sa

from pyht import client
from pyht.protos import api_pb2


class StreamingClient(client.Client):
    def __init__(
        self,
        user_id: str,
        api_key: str,
        buffer_byte_size: int = 10485760,
    ):
        advanced = client.Client.AdvancedOptions(grpc_addr='prod.turbo.play.ht:443')
        super().__init__(user_id, api_key, advanced=advanced)
        self._buff_size = buffer_byte_size


    def play(
        self,
        text: str,
        voice: str,
        quality: str
    ):
        options = client.TTSOptions(voice=voice, format=api_pb2.FORMAT_WAV, quality=quality)
        ptr = 0
        start_time = time.time()
        audio = None
        buffer = np.empty(self._buff_size, np.float16)
        for i, chunk in enumerate(self.tts(text, options)):
            if i == 0:
                start_time = time.time()
                continue  # Drop the first response, we dont' want a header.
            elif i == 1:
                print('First audio byte received in:', time.time() - start_time)
            for sample in np.frombuffer(chunk, np.float16):
                buffer[ptr] = sample
                ptr += 1
            if i == 2:  # Give a 1 sample worth of breathing room before starting playback
                audio = sa.play_buffer(buffer, 1, 2, 24000)
        approx_run_time = ptr / 24000
        time.sleep(approx_run_time - time.time() + start_time)
        if audio is not None:
            audio.stop()


def main(
    user: str,
    key: str,
    text: Iterable[str],
    voice: str,
    quality: Literal['fast'] | Literal['faster'],
    interactive: bool
):
    # Setup the client.
    client = StreamingClient(user, key)

    # Send some text, play some audio.
    for t in text:
        client.play(t, voice, quality)

    # Maybe play around with an interactive session.
    if interactive:
        print('Starting interactive session.')
        print('Input an empty line to quit.')
        t = input('> ')
        while t:
            client.play(t, voice, quality)
            t = input('> ')
        print()
        print('Interactive session closed.')

    # Cleanup.
    client.close()
    return 0




if __name__ == '__main__':
    import argparse
    import sys


    parser = argparse.ArgumentParser('PyHT Streaming Demo')

    parser.add_argument('--user', '-u', type=str, required=True,
        help='Your Play.ht User ID.')
    parser.add_argument('--key', '-k', type=str, required=True,
        help='Your Play.ht API key.')
    parser.add_argument('--voice', '-v', type=str,
        default='s3://voice-cloning-zero-shot/d9ff78ba-d016-47f6-b0ef-dd630f59414e/female-cs/manifest.json',
        help='Voice manifest URI')
    parser.add_argument('--quality', '-q', choices=['fast', 'faster'], default='faster',
        help='Quality of the generated audio')    

    input_group = parser.add_mutually_exclusive_group(required=True)
    input_group.add_argument('--text', '-t', type=str, nargs='+', default = [],
        help='Text to generate, REQUIRED if the `--interactive` flag is not set.')
    input_group.add_argument('--interactive', '-i', action='store_true',
        help='Run this demo in interactive-input mode, REQUIRED if `--text` is not supplied.')

    args = parser.parse_args()

    sys.exit(main(**vars(args)))