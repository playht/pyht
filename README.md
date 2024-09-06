# PlayHT API SDK

**pyht** is a Python SDK for the [PlayHT's AI Text-to-Speech API](https://play.ht/text-to-speech-api/). PlayHT builds conversational voice AI models for realtime use cases. With **pyht**, you can easily convert text into high-quality audio streams in humanlike voice.

## Features

- Stream text-to-speech in real-time.
- Use PlayHT's pre-built voices or create custom voice clones.
- Stream text from LLM, and generate audio stream in real-time.
- Supports WAV, MP3, Mulaw, FLAC, and OGG audio formats as well as raw audio.
- Supports 8KHz, 16KHz, 24KHz, 44.1KHz and 48KHz sample rates.

## Requirements

- Python 3.8+
- `aiohttp`
- `filelock`
- `grpc`
- `requests`

Demo requirements:
- `numpy`
- `soundfile`

## Installation

You can install the **pyht** SDK using pip:

```shell
pip install pyht
```

## Usage

You can use the **pyht** SDK by creating a `Client` instance and calling its `tts` method. Here's a simple example:

```python
from pyht import Client
from dotenv import load_dotenv
from pyht.client import TTSOptions
import os
load_dotenv()

client = Client(
    user_id=os.getenv("PLAY_HT_USER_ID"),
    api_key=os.getenv("PLAY_HT_API_KEY"),
)
options = TTSOptions(voice="s3://voice-cloning-zero-shot/775ae416-49bb-4fb6-bd45-740f205d20a1/jennifersaad/manifest.json")
for chunk in client.tts("Hi, I'm Jennifer from Play. How can I help you today?", options):
    # do something with the audio chunk
    print(type(chunk))
```

It is also possible to stream text instead of submitting it as a string all at once:

```python
for chunk in client.stream_tts_input(some_iterable_text_stream, options):
    # do something with the audio chunk
    print(type(chunk))
```

An asyncio version of the client is also available:

```python
from pyht import AsyncClient

client = AsyncClient(
    user_id=os.getenv("PLAY_HT_USER_ID"),
    api_key=os.getenv("PLAY_HT_API_KEY"),
)
options = TTSOptions(voice="s3://voice-cloning-zero-shot/775ae416-49bb-4fb6-bd45-740f205d20a1/jennifersaad/manifest.json")
async for chunk in client.tts("Hi, I'm Jennifer from Play. How can I help you today?", options):
    # do something with the audio chunk
    print(type(chunk))
```

The `tts` method takes the following arguments:

- `text`: The text to be converted to speech.
    - a string or list of strings.
- `options`: The options to use for the TTS request.
    - a `TTSOptions` object (see below).
- `voice_engine`: The voice engine to use for the TTS request.
    - `Play3.0` (default): Our latest multilingual model, streaming audio over HTTP.
    - `PlayHT2.0`: Our legacy English-only model, streaming audio over gRPC.

### TTSOptions

The `TTSOptions` class is used to specify the options for the TTS request. It has the following members, with these supported values:

- `voice`: The voice to use for the TTS request; a string.
    - A URL pointing to a Play voice manifest file.
- `format`: The format of the audio to be returned; a `Format` enum value.
    - `FORMAT_MP3` (default)
    - `FORMAT_WAV`
    - `FORMAT_MULAW`
    - `FORMAT_FLAC`
    - `FORMAT_OGG`
    - `FORMAT_RAW`
- `sample_rate`: The sample rate of the audio to be returned; an integer.
    - 8000
    - 16000
    - 24000
    - 44100
    - 48000
- `quality`: DEPRECATED (use sample rate to adjust audio quality)
- `speed`: The speed of the audio to be returned, a float (default 1.0).
- `seed`: Random seed to use for audio generation, an integer (default None, will be randomly generated).
- The following options are inference-time hyperparameters of the text-to-speech model; if unset, the model will use default values chosen by PlayHT.
    - `temperature`: The temperature of the model, a float.
    - `top_p`: The top_p of the model, a float.
    - `text_guidance`: The text_guidance of the model, a float.
    - `voice_guidance` (PlayHT2.0 only): The voice_guidance of the model, a float.
    - `style_guidance` (Play3.0 only): The style_guidance of the model, a float.
    - `repetition_penalty`: The repetition_penalty of the model, a float.
- `disable_stabilization` (PlayHT2.0 only): Disable the audio stabilization process, a boolean (default False).
- `language` (Play3.0 only): The language of the text to be spoken, a `Language` enum value or None (default English).
    - `AFRIKAANS`
    - `ALBANIAN`
    - `AMHARIC`
    - `ARABIC`
    - `BENGALI`
    - `BULGARIAN`
    - `CATALAN`
    - `CROATIAN`
    - `CZECH`
    - `DANISH`
    - `DUTCH`
    - `ENGLISH`
    - `FRENCH`
    - `GALICIAN`
    - `GERMAN`
    - `GREEK`
    - `HEBREW`
    - `HINDI`
    - `HUNGARIAN`
    - `INDONESIAN`
    - `ITALIAN`
    - `JAPANESE`
    - `KOREAN`
    - `MALAY`
    - `MANDARIN`
    - `POLISH`
    - `PORTUGUESE`
    - `RUSSIAN`
    - `SERBIAN`
    - `SPANISH`
    - `SWEDISH`
    - `TAGALOG`
    - `THAI`
    - `TURKISH`
    - `UKRAINIAN`
    - `URDU`
    - `XHOSA`

## Command-Line Demo

You can run the provided [demo](https://github.com/playht/pyht/tree/master/demo/) from the command line.

**Note:** This demo depends on the following packages:

```shell
pip install numpy soundfile
```

```shell
python demo/main.py --user $PLAY_HT_USER_ID --key $PLAY_HT_API_KEY --text "Hello from Play!"
```

To run with the asyncio client, use the `--async` flag:

```shell
python demo/main.py --user $PLAY_HT_USER_ID --key $PLAY_HT_API_KEY --text "Hello from Play!" --async
```

To run with the HTTP API, which uses our latest Play3.0 model, use the `--http` flag:

```shell
python demo/main.py --user $PLAY_HT_USER_ID --key $PLAY_HT_API_KEY --text "Hello from Play!" --http
```

The HTTP API can also be used with the async client:

```shell
python demo/main.py --user $PLAY_HT_USER_ID --key $PLAY_HT_API_KEY --text "Hello from Play!" --http --async
```

Alternatively, you can run the demo in interactive mode:

```shell
python demo/main.py --user $PLAY_HT_USER_ID --key $PLAY_HT_API_KEY --interactive
```

In interactive mode, you can input text lines to generate and play audio on-the-fly. An empty line will exit the interactive session.

## Get an API Key

To get started with the **pyht** SDK, you'll need your API Secret Key and User ID. Follow these steps to obtain them:

1. **Access the API Page**:
   Navigate to the [API Access page](https://play.ht/studio/api-access).

2. **Generate Your API Secret Key**:

   - Click the "Generate Secret Key" button under the "Secret Key" section.
   - Your API Secret Key will be displayed. Ensure you copy it and store it securely.

3. **Locate Your User ID**:
   Find and copy your User ID, which can be found on the same page under the "User ID" section.

_**Keep your API Secret Key confidential**. It's crucial not to share it with anyone or include it in publicly accessible code repositories._
