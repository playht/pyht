# PyHT Streaming Client Demo

## Usage

```
$ python demo/main.py --help

usage: PyHT Streaming Demo [-h] (--ws | --http | --grpc) [--async] --user USER --key KEY [--voice VOICE]
                           [--language {afrikaans,albanian,amharic,arabic,bengali,bulgarian,catalan,croatian,czech,danish,dutch,english,french,galician,german,greek,hebrew,hindi,hungarian,indonesian,italian,japanese,korean,malay,mandarin,polish,portuguese,russian,serbian,spanish,swedish,tagalog,thai,turkish,ukrainian,urdu,xhosa}]
                           (--text TEXT [TEXT ...] | --interactive)

options:
  -h, --help            show this help message and exit
  --ws                  Use the WebSocket API with the 3.0-mini model.
  --http                Use the HTTP API with the 3.0-mini model.
  --grpc                Use the gRPC API with the 2.0-turbo model.
  --async               Use the asyncio client.
  --user USER, -u USER  Your Play.ht User ID.
  --key KEY, -k KEY     Your Play.ht API key.
  --voice VOICE, -v VOICE
                        Voice manifest URI
  --language {afrikaans,albanian,amharic,arabic,bengali,bulgarian,catalan,croatian,czech,danish,dutch,english,french,galician,german,greek,hebrew,hindi,hungarian,indonesian,italian,japanese,korean,malay,mandarin,polish,portuguese,russian,serbian,spanish,swedish,tagalog,thai,turkish,ukrainian,urdu,xhosa}, -l {...}
                        Language of the text to be spoken.
  --text TEXT [TEXT ...], -t TEXT [TEXT ...]
                        Text to generate, REQUIRED if the `--interactive` flag is not set.
  --interactive, -i     Run this demo in interactive-input mode, REQUIRED if `--text` is not supplied.
```
