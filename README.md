# Play API SDK

**pyht** is a Python SDK for [Play's AI Text-to-Speech API](https://play.ht/text-to-speech-api/). Play builds conversational voice AI models for realtime use cases. With **pyht**, you can easily convert text into high-quality audio streams with humanlike voices.

Currently the library supports only streaming and non-streaming text-to-speech. For the full set of functionalities provided by the Play API such as [Voice Cloning](https://docs.play.ht/reference/api-create-instant-voice-clone), see the [Play docs](https://docs.play.ht/reference/api-getting-started)

## Features

- Stream text-to-speech in real-time, synchronous or asynchronous.
- Generate non-streaming text-to-speech, synchronous or asynchronous.
- Use Play's pre-built voices or your own custom voice clones.
- Stream text from LLM, and generate audio stream in real-time.
- Supports WAV, MP3, Mulaw, FLAC, and OGG audio formats as well as raw audio.
- Supports 8KHz, 16KHz, 24KHz, 44.1KHz and 48KHz sample rates.

## Requirements

- Python 3.8+
- `aiohttp`
- `filelock`
- `grpc`
- `requests`
- `websockets`

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

- `text`: The text to be converted to speech; a string or list of strings.
- `options`: The options to use for the TTS request; a `TTSOptions` object [(see below)](#ttsoptions).
- `voice_engine`: The voice engine to use for the TTS request; a string (default `Play3.0-mini-http`).
    - `PlayDialog`: Our large, expressive English model, which also supports multi-turn two-speaker dialogues.
    - `PlayDialogMultilingual`: Our large, expressive multilingual model, which also supports multi-turn two-speaker dialogues.
    - `Play3.0-mini`: Our small, fast multilingual model.
    - `PlayHT2.0-turbo`: Our legacy English-only model
- `protocol`: The protocol to use to communicate with the Play API (`http` by default except for `PlayHT2.0-turbo` which is `grpc` by default).
    - `http`: Streaming and non-streaming audio over HTTP (supports `Play3.0-mini`, `PlayDialog`, and `PlayDialogMultilingual`).
    - `ws`: Streaming audio over WebSockets (supports `Play3.0-mini`, `PlayDialog`, and `PlayDialogMultilingual`).
    - `grpc`: Streaming audio over gRPC (supports `PlayHT2.0-turbo` for all, and `Play3.0-mini` ONLY for Play On-Prem customers).
- `streaming`: Whether or not to stream the audio in chunks (default True); non-streaming is only enabled for HTTP endpoints.

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
- `sample_rate`: The sample rate of the audio to be returned; an integer or `None` (Play backend will choose by default).
    - 8000
    - 16000
    - 24000
    - 44100
    - 48000
- `quality`: DEPRECATED (use sample rate to adjust audio quality)
- `speed`: The speed of the audio to be returned, a float (default `1.0`).
- `seed`: Random seed to use for audio generation, an integer (default `None`, will be randomly generated).
- The following options are inference-time hyperparameters of the text-to-speech model; if unset, the model will use default values chosen by Play.
    - `temperature` (all models): The temperature of the model, a float.
    - `top_p` (all models): The top_p of the model, a float.
    - `text_guidance` (`Play3.0-mini` and `PlayHT2.0-turbo` only): The text_guidance of the model, a float.
    - `voice_guidance` (`Play3.0-mini` and `PlayHT2.0-turbo` only): The voice_guidance of the model, a float.
    - `style_guidance` (`Play3.0-mini` only): The style_guidance of the model, a float.
    - `repetition_penalty` (`Play3.0-mini` and `PlayHT2.0-turbo` only): The repetition_penalty of the model, a float.
- `disable_stabilization` (`PlayHT2.0-turbo` only): Disable the audio stabilization process, a boolean (default `False`).
- `language` (`Play3.0` and `PlayDialogMultilingual` only): The language of the text to be spoken, a `Language` enum value or `None` (default `ENGLISH`).
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
- The following options are additional inference-time hyperparameters which only apply to the `PlayDialog` and `PlayDialogMultilingual` models; if unset, the model will use default values chosen by Play.
    - `voice_2` (multi-turn dialogue only): The second voice to use for a multi-turn TTS request; a string.
        - A URL pointing to a Play voice manifest file.
    - `turn_prefix` (multi-turn dialogue only): The prefix for the first speaker's turns in a multi-turn TTS request; a string.
    - `turn_prefix_2` (multi-turn dialogue only): The prefix for the second speaker's turns in a multi-turn TTS request; a string.
    - `voice_conditioning_seconds`: How much of the voice's reference audio to pass to the model as a guide; an integer.
    - `voice_conditioning_seconds_2` (multi-turn dialogue only): How much of the second voice's reference audio to pass to the model as a guide; an integer.
    - `scene_description`: A description of the overall scene (single- or multi-turn) to guide the model; a string (NOTE: currently not recommended).
    - `turn_clip_description` (multi-turn dialogue only): A description of each turn (with turn prefixes) to guide the model; a string (NOTE: currently not recommended).
    - `num_candidates`: How many candidates to rank to choose the best one; an integer.
    - `candidate_ranking_method`: The method for the model to use to rank candidates; a `CandidateRankingMethod` enum value or `None` (let Play choose the method by default).
        - Methods valid for streaming and non-streaming requests:
            - `MeanProbRank`: Rank candidates based on mean probability of the output sequence.
        - Methods valid for streaming requests only:
            - `EndProbRank`: Rank candidates based on probability of end of sequence.
            - `MeanProbWithEndProbRank`: Combination of `MeanProbRank` and `EndProbRank`.
        - Methods valid for non-streaming requests only:
            - `DescriptionRank`: Rank candidates based on adherence to description.
            - `ASRRank`: Rank candidates based on comparison of ASR transcription with the ground-truth text.
            - `DescriptionASRRank`: Combination of `DescriptionRank` and `ASRRank`.
            - `ASRWithMeanProbRank`: Combination of `ASRRank` and `MeanProbRank`.
            - `DescriptionASRWithMeanProbRank`: Combination of `DescriptionASRRank` and `MeanProbRank`.


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

To run with the HTTP API, which uses our latest Play3.0-mini model, use the `--http` flag:

```shell
python demo/main.py --user $PLAY_HT_USER_ID --key $PLAY_HT_API_KEY --text "Hello from Play!" --http
```

To run with the WebSockets API, which also uses our latest Play3.0-mini model, use the `--ws` flag:

```shell
python demo/main.py --user $PLAY_HT_USER_ID --key $PLAY_HT_API_KEY --text "Hello from Play!" --ws
```

The HTTP and WebSockets APIs can also be used with the async client:

```shell
python demo/main.py --user $PLAY_HT_USER_ID --key $PLAY_HT_API_KEY --text "Hello from Play!" --http --async
python demo/main.py --user $PLAY_HT_USER_ID --key $PLAY_HT_API_KEY --text "Hello from Play!" --ws --async
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
