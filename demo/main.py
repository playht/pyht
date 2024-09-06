from __future__ import annotations

import asyncio
import select
import sys
import threading
from typing import AsyncGenerator, AsyncIterable, Generator, Iterable, Literal

import numpy as np
import soundfile as sf

from pyht.async_client import AsyncClient
from pyht.client import Client, TTSOptions
from pyht.protos import api_pb2


# === SYNC EXAMPLE ===


def save_audio(data: Generator[bytes, None, None] | Iterable[bytes]):
    chunks: bytearray = bytearray()
    for i, chunk in enumerate(data):
        if i == 0:
            continue  # Drop the first response, we don't want a header.
        chunks.extend(chunk)
    sf.write("output.wav", np.frombuffer(chunks, dtype=np.int16), 24000)


def main(
    user: str,
    key: str,
    text: Iterable[str],
    voice: str,
    quality: Literal["fast"] | Literal["faster"],
    interactive: bool,
    use_async: bool,
    use_http: bool,
):
    del use_async

    # Setup the client
    client = Client(user, key)

    # Set the speech options
    options = TTSOptions(voice=voice, format=api_pb2.FORMAT_WAV, quality=quality)

    # Get the streams
    if use_http:
        voice_engine = "Play3.0"
    else:
        voice_engine = "PlayHT2.0"
    in_stream, out_stream = client.get_stream_pair(options, voice_engine=voice_engine)

    # Start a player thread.
    audio_thread = threading.Thread(None, save_audio, args=(out_stream,))
    audio_thread.start()

    # Send some text, play some audio.
    for t in text:
        in_stream(t)
    in_stream.done()

    # cleanup
    audio_thread.join()
    out_stream.close()

    metrics = client.metrics()
    print(str(metrics[-1].timers.get("time-to-first-audio")))

    # Maybe play around with an interactive session.
    if interactive:
        print("Starting interactive session.")
        print("Input an empty line to quit.")
        t = input("> ")
        while t:
            save_audio(client.tts(t, options))
            t = input("> ")
        print()
        print("Interactive session closed.")

    # Cleanup.
    client.close()
    return 0


# === ASYNC EXAMPLE ===


async def async_save_audio(data: AsyncGenerator[bytes, None] | AsyncIterable[bytes]):
    i = -1
    chunks: bytearray = bytearray()
    async for chunk in data:
        i += 1
        if i == 0:
            continue  # Drop the first response, we don't want a header.
        chunks.extend(chunk)
    sf.write("output.wav", np.frombuffer(chunks, dtype=np.int16), 24000)


async def async_main(
    user: str,
    key: str,
    text: Iterable[str],
    voice: str,
    quality: Literal["fast"] | Literal["faster"],
    interactive: bool,
    use_async: bool,
    use_http: bool,
):
    del use_async

    # Setup the client
    client = AsyncClient(user, key)

    # Set the speech options
    options = TTSOptions(voice=voice, format=api_pb2.FORMAT_WAV, quality=quality)

    # Get the streams
    if use_http:
        voice_engine = "Play3.0"
    else:
        voice_engine = "PlayHT2.0"
    in_stream, out_stream = client.get_stream_pair(options, voice_engine=voice_engine)

    audio_task = asyncio.create_task(async_save_audio(out_stream))

    # Send some text, play some audio.
    await in_stream(*text)
    await in_stream.done()

    # cleanup
    await asyncio.wait_for(audio_task, 60)
    out_stream.close()

    metrics = client.metrics()
    print(str(metrics[-1].timers.get("time-to-first-audio")))

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
            asyncio.ensure_future(async_save_audio(client.tts(t, options)))
            t = await get_input()
        print()
        print("Interactive session closed.")

    # Cleanup.
    await client.close()


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser("PyHT Streaming Demo")

    parser.add_argument(
        "--http", action="store_true", help="Use the HTTP API instead of gRPC.", dest="use_http"
    )

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
