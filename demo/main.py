from __future__ import annotations

import asyncio
import select
import sys
import threading
from typing import AsyncGenerator, AsyncIterable, Generator, Iterable, Union

from pyht.async_client import AsyncClient
from pyht.client import Client, TTSOptions, Language


# === SYNC EXAMPLE ===


def save_audio(data: Union[Generator[bytes, None, None], Iterable[bytes]]):
    chunks: bytearray = bytearray()
    for chunk in data:
        chunks.extend(chunk)
    with open("output.wav", "wb") as f:
        f.write(chunks)


def main(
    user: str,
    key: str,
    text: Iterable[str],
    voice: str,
    language: str,
    interactive: bool,
    use_async: bool,
    use_http: bool,
    use_ws: bool,
    use_grpc: bool,
):
    del use_async

    # Setup the client
    client = Client(user, key)

    # Set the speech options
    options = TTSOptions(voice=voice, language=Language(language))

    # Get the streams
    if use_http:
        voice_engine = "Play3.0-mini"
        protocol = "http"
    elif use_ws:
        voice_engine = "Play3.0-mini"
        protocol = "ws"
    else:
        voice_engine = "PlayHT2.0-turbo"
        protocol = "grpc"
    in_stream, out_stream = client.get_stream_pair(options, voice_engine=voice_engine, protocol=protocol)

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


async def async_save_audio(data: Union[AsyncGenerator[bytes, None], AsyncIterable[bytes]]):
    chunks: bytearray = bytearray()
    async for chunk in data:
        chunks.extend(chunk)
    with open("output.wav", "wb") as f:
        f.write(chunks)


async def async_main(
    user: str,
    key: str,
    text: Iterable[str],
    voice: str,
    language: str,
    interactive: bool,
    use_async: bool,
    use_http: bool,
    use_ws: bool,
    use_grpc: bool,
):
    del use_async

    # Setup the client
    client = AsyncClient(user, key)

    # Set the speech options
    options = TTSOptions(voice=voice, language=Language(language))

    # Get the streams
    if use_http:
        voice_engine = "Play3.0-mini"
        protocol = "http"
    elif use_ws:
        voice_engine = "Play3.0-mini"
        protocol = "ws"
    else:
        voice_engine = "PlayHT2.0-turbo"
        protocol = "grpc"
    in_stream, out_stream = client.get_stream_pair(options, voice_engine=voice_engine, protocol=protocol)

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

    api_group = parser.add_mutually_exclusive_group(required=True)
    api_group.add_argument(
        "--ws", action="store_true", help="Use the WebSocket API with the 3.0-mini model.", dest="use_ws"
    )
    api_group.add_argument(
        "--http", action="store_true", help="Use the HTTP API with the 3.0-mini model.", dest="use_http"
    )
    api_group.add_argument(
        "--grpc", action="store_true", help="Use the gRPC API with the 2.0-turbo model.", dest="use_grpc"
    )

    parser.add_argument(
        "--async", action="store_true", help="Use the asyncio client.", dest="use_async"
    )

    parser.add_argument(
        "--user", "-u", type=str, required=True, help="Your Play API user ID."
    )
    parser.add_argument(
        "--key", "-k", type=str, required=True, help="Your Play API key."
    )
    parser.add_argument(
        "--voice",
        "-v",
        type=str,
        default="s3://voice-cloning-zero-shot/d9ff78ba-d016-47f6-b0ef-dd630f59414e/female-cs/manifest.json",
        help="Voice manifest URI",
    )
    parser.add_argument(
        "--language",
        "-l",
        choices=[lang.value for lang in Language],
        default="english",
        help="Language of the text to be spoken.",
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
