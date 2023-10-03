# PlayHT API SDK

**pyht** is a Python SDK for the [PlayHT's Text-to-Speech API](https://docs.play.ht/). With **pyht**, you can easily convert text into high-quality audio streams in humanlike voice.

## Features

- Stream text-to-speech in real-time.
- Use prebuilt voices or custom voice clones.
- Supports WAV, MP3, PCM, Mulaw, FLAC, and OGG audio formats.

## Requirements

- Python 3.8+
- `numpy`
- `simpleaudio`

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
options = TTSOptions(voice="s3://voice-cloning-zero-shot/d9ff78ba-d016-47f6-b0ef-dd630f59414e/female-cs/manifest.json")
for chunk in client.tts("Can you tell me your account email or, ah your phone number?", options):
    # do something with the audio chunk
    print(type(chunk))
```

For a more detailed example with command-line arguments and interactive mode, refer to the provided demo.

## Command-Line Demo

You can run the provided [demo](https://github.com/playht/pyht/tree/master/demo/) from the command line.

**Note:** This demo depends on the following packages:

```shell
pip install numpy simpleaudio
```

```shell
python demo/main.py --user YOUR_USER_ID --key YOUR_API_KEY --text "Hello from Play!"
```

Alternatively, you can run the demo in interactive mode:

```shell
python demo/main.py --user YOUR_USER_ID --key YOUR_API_KEY --interactive
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
