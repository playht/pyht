# PyHT Streaming Client Demo

## Prereqs
This demo depends on the following packages:
```
numpy
simpleaudio
```

## Usage

```
$ python demo/main.py --help

usage: PyHT Streaming Demo [-h] --user USER --key KEY [--voice VOICE] [--quality {fast,faster}] (--text TEXT [TEXT ...] | --interactive)

options:
  -h, --help            show this help message and exit
  --user USER, -u USER  Your Play.ht User ID.
  --key KEY, -k KEY     Your Play.ht API key.
  --voice VOICE, -v VOICE
                        Voice manifest URI
  --quality {fast,faster}, -q {fast,faster}
                        Quality of the generated audio
  --text TEXT [TEXT ...], -t TEXT [TEXT ...]
                        Text to generate, REQUIRED if the `--interactive` flag is not set.
  --interactive, -i     Run this demo in interactive-input mode, REQUIRED if `--text` is not supplied.
```
