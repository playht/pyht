from __future__ import annotations
from typing import AsyncGenerator, AsyncIterable, Generator, Iterable, Literal

import asyncio
import time
import threading
import select
import sys

import numpy as np
import simpleaudio as sa

from pyht.client import Client, TTSOptions
from pyht.async_client import AsyncClient
from pyht.protos import api_pb2


# === SYNC EXAMPLE ===


def play_audio(data: Generator[bytes, None, None] | Iterable[bytes]):
    buff_size = 10485760
    ptr = 0
    start_time = time.time()
    buffer = np.empty(buff_size, np.float16)
    audio = None
    for i, chunk in enumerate(data):
        if i == 0:
            start_time = time.time()
            continue  # Drop the first response, we don't want a header.
        elif i == 1:
            print("First audio byte received in:", time.time() - start_time)
        for sample in np.frombuffer(chunk, np.float16):
            buffer[ptr] = sample
            ptr += 1
        if i == 5:
            # Give a 4 sample worth of breathing room before starting
            # playback
            audio = sa.play_buffer(buffer, 1, 2, 24000)
    approx_run_time = ptr / 24_000
    time.sleep(max(approx_run_time - time.time() + start_time, 0))
    if audio is not None:
        audio.stop()


def main(
    user: str,
    key: str,
    text: Iterable[str],
    voice: str,
    quality: Literal["fast"] | Literal["faster"],
    interactive: bool,
):
    # Setup the client
    client = Client(user, key)

    # Set the speech options
    options = TTSOptions(voice=voice, format=api_pb2.FORMAT_WAV, quality=quality)

    # Get the streams
    in_stream, out_stream = client.get_stream_pair(options)

    # Start a player thread.
    audio_thread = threading.Thread(None, play_audio, args=(out_stream,))
    audio_thread.start()

    # Send some text, play some audio.
    for t in text:
        in_stream(t)
    in_stream.done()

    # cleanup
    audio_thread.join()
    out_stream.close()

    # Maybe play around with an interactive session.
    if interactive:
        print("Starting interactive session.")
        print("Input an empty line to quit.")
        t = input("> ")
        while t:
            play_audio(client.tts(t, options))
            t = input("> ")
        print()
        print("Interactive session closed.")

    # Cleanup.
    client.close()
    return 0


# === ASYNC EXAMPLE ===


async def async_play_audio(data: AsyncGenerator[bytes, None] | AsyncIterable[bytes]):
    buff_size = 10485760
    ptr = 0
    start_time = time.time()
    buffer = np.empty(buff_size, np.float16)
    audio = None
    i = -1
    async for chunk in data:
        i += 1
        if i == 0:
            start_time = time.time()
            continue  # Drop the first response, we don't want a header.
        elif i == 1:
            print("First audio byte received in:", time.time() - start_time)
        for sample in np.frombuffer(chunk, np.float16):
            buffer[ptr] = sample
            ptr += 1
        if i == 5:
            # Give a 4 sample worth of breathing room before starting
            # playback
            audio = sa.play_buffer(buffer, 1, 2, 24000)
    approx_run_time = ptr / 24_000
    await asyncio.sleep(max(approx_run_time - time.time() + start_time, 0))
    if audio is not None:
        audio.stop()


async def async_main(
    user: str,
    key: str,
    text: Iterable[str],
    voice: str,
    quality: Literal["fast"] | Literal["faster"],
    interactive: bool,
    use_async: bool,
):
    del use_async

    # Setup the client
    client = AsyncClient(user, key)

    # Set the speech options
    options = TTSOptions(voice=voice, format=api_pb2.FORMAT_WAV, quality=quality)

    # Get the streams
    in_stream, out_stream = client.get_stream_pair(options)

    audio_task = asyncio.create_task(async_play_audio(out_stream))

    # Send some text, play some audio.
    await in_stream(*text)
    await in_stream.done()

    # cleanup
    await asyncio.wait_for(audio_task, 60)
    out_stream.close()

    async def get_input():
        while not select.select([sys.stdin], [], [], 0)[0]:
            await asyncio.sleep(0.01)
        return sys.stdin.readline().strip()

    # Maybe play around with an interactive session.
    if interactive:
        print("Starting interactive session.")
        print("Input an empty line to quit.")
        t = await get_input()
        while t:
            asyncio.ensure_future(async_play_audio(client.tts(t, options)))
            t = await get_input()
        print()
        print("Interactive session closed.")

    # Cleanup.
    await client.close()


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser("PyHT Streaming Demo")

    parser.add_argument(
        "--async", action="store_true", help="Use the asyncio client.", dest="use_async"
    )

    parser.add_argument(
        "--user", "-u", type=str, required=True, help="Your Play.ht User ID."
    )
    parser.add_argument(
        "--key", "-k", type=str, required=True, help="Your Play.ht API key."
    )
    parser.add_argument(
        "--voice",
        "-v",
        type=str,
        default="s3://voice-cloning-zero-shot/d9ff78ba-d016-47f6-b0ef-dd630f59414e/female-cs/manifest.json",
        help="Voice manifest URI",
    )
    parser.add_argument(
        "--quality",
        "-q",
        choices=["fast", "faster"],
        default="faster",
        help="Quality of the generated audio",
    )

    input_group = parser.add_mutually_exclusive_group(required=True)
    input_group.add_argument(
        "--text",
        "-t",
        type=str,
        nargs="+",
        default=[],
        help="Text to generate, REQUIRED if the `--interactive` flag is not set.",
    )
    input_group.add_argument(
        "--interactive",
        "-i",
        action="store_true",
        help="Run this demo in interactive-input mode, REQUIRED if `--text` is not supplied.",
    )

    args = parser.parse_args()

    if args.use_async:
        asyncio.run(async_main(**vars(args)))
        sys.exit(0)

    sys.exit(main(**vars(args)))
