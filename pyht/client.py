from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, Generator, Iterable, Iterator, List, Tuple, Optional, Union
import io
import json
import logging
import os
import queue
import tempfile
import threading
import time
import uuid
from websockets.sync.client import connect, ClientConnection

import filelock
import grpc
from grpc import Channel, insecure_channel, secure_channel, ssl_channel_credentials, StatusCode
import requests

from .inference_coordinates import get_coordinates, InferenceCoordinatesOptions
from .lease import Lease, LeaseFactory
from .protos import api_pb2, api_pb2_grpc
from .telemetry import Metrics, Telemetry
from .utils import prepare_text, SENTENCE_END_REGEX


CLIENT_RETRY_OPTIONS = [
        ("grpc.enable_retries", 1),
        ("grpc.service_config", json.dumps({
            "methodConfig": [{
                "name": [{}],
                "retryPolicy": {
                    "maxAttempts": 3,
                    "initialBackoff": "0.01s",
                    "maxBackoff": "0.3s",
                    "backoffMultiplier": 4,
                    "retryableStatusCodes": ["UNAVAILABLE"],
                },
            }]
        }))
    ]


class Format(Enum):
    FORMAT_RAW = api_pb2.FORMAT_RAW
    FORMAT_MP3 = api_pb2.FORMAT_MP3
    FORMAT_WAV = api_pb2.FORMAT_WAV
    FORMAT_OGG = api_pb2.FORMAT_OGG
    FORMAT_FLAC = api_pb2.FORMAT_FLAC
    FORMAT_MULAW = api_pb2.FORMAT_MULAW
    FORMAT_PCM = api_pb2.FORMAT_PCM


class HTTPFormat(Enum):
    FORMAT_RAW = "raw"
    FORMAT_MP3 = "mp3"
    FORMAT_WAV = "wav"
    FORMAT_OGG = "ogg"
    FORMAT_FLAC = "flac"
    FORMAT_MULAW = "mulaw"
    FORMAT_PCM = "pcm"


# PlayDialog-* and PlayDialogMultilingual-* only
class CandidateRankingMethod(Enum):
    MeanProbRank = "mean_prob"

    # non-streaming only
    DescriptionRank = "description"
    ASRRank = "asr"
    DescriptionASRRank = "description_asr"
    ASRWithMeanProbRank = "asr_with_mean_prob"
    DescriptionASRWithMeanProbRank = "description_asr_with_mean_prob"

    # streaming only
    EndProbRank = "end_prob"
    MeanProbWithEndProbRank = "mean_prob_with_end_prob"


def grpc_format_to_http_format(format: Format) -> HTTPFormat:
    if format == Format.FORMAT_RAW:
        return HTTPFormat.FORMAT_RAW
    elif format == Format.FORMAT_MP3:
        return HTTPFormat.FORMAT_MP3
    elif format == Format.FORMAT_WAV:
        return HTTPFormat.FORMAT_WAV
    elif format == Format.FORMAT_OGG:
        return HTTPFormat.FORMAT_OGG
    elif format == Format.FORMAT_FLAC:
        return HTTPFormat.FORMAT_FLAC
    elif format == Format.FORMAT_MULAW:
        return HTTPFormat.FORMAT_MULAW
    elif format == Format.FORMAT_PCM:
        return HTTPFormat.FORMAT_PCM
    else:
        raise ValueError(f"Unsupported format for HTTP API: {format}")


class Language(Enum):
    AFRIKAANS = "afrikaans"
    ALBANIAN = "albanian"
    AMHARIC = "amharic"
    ARABIC = "arabic"
    BENGALI = "bengali"
    BULGARIAN = "bulgarian"
    CATALAN = "catalan"
    CROATIAN = "croatian"
    CZECH = "czech"
    DANISH = "danish"
    DUTCH = "dutch"
    ENGLISH = "english"
    FRENCH = "french"
    GALICIAN = "galician"
    GERMAN = "german"
    GREEK = "greek"
    HEBREW = "hebrew"
    HINDI = "hindi"
    HUNGARIAN = "hungarian"
    INDONESIAN = "indonesian"
    ITALIAN = "italian"
    JAPANESE = "japanese"
    KOREAN = "korean"
    MALAY = "malay"
    MANDARIN = "mandarin"
    POLISH = "polish"
    PORTUGUESE = "portuguese"
    RUSSIAN = "russian"
    SERBIAN = "serbian"
    SPANISH = "spanish"
    SWEDISH = "swedish"
    TAGALOG = "tagalog"
    THAI = "thai"
    TURKISH = "turkish"
    UKRAINIAN = "ukrainian"
    URDU = "urdu"
    XHOSA = "xhosa"


# https://github.com/playht/tts.cpp/blob/8adf892e1464069a9ce4b1b7639db962f1cd0deb/play_tts/parrot/parrot_params.py#L31-L73
LanguageIdentifiers = {
    Language.AFRIKAANS: 20,
    Language.ALBANIAN: 33,
    Language.AMHARIC: 32,
    Language.ARABIC: 5,
    Language.BENGALI: 25,
    Language.BULGARIAN: 16,
    Language.CATALAN: 34,
    Language.CROATIAN: 29,
    Language.CZECH: 13,
    Language.DANISH: 31,
    Language.DUTCH: 11,
    Language.ENGLISH: 0,
    Language.FRENCH: 7,
    Language.GALICIAN: 36,
    Language.GERMAN: 10,
    Language.GREEK: 18,
    Language.HEBREW: 17,
    Language.HINDI: 2,
    Language.HUNGARIAN: 30,
    Language.INDONESIAN: 24,
    Language.ITALIAN: 8,
    Language.JAPANESE: 3,
    Language.KOREAN: 4,
    Language.MALAY: 23,
    Language.MANDARIN: 1,
    Language.POLISH: 14,
    Language.PORTUGUESE: 9,
    Language.RUSSIAN: 15,
    Language.SERBIAN: 26,
    Language.SPANISH: 6,
    Language.SWEDISH: 12,
    Language.TAGALOG: 22,
    Language.THAI: 27,
    Language.TURKISH: 19,
    Language.UKRAINIAN: 35,
    Language.URDU: 28,
    Language.XHOSA: 21,
}


@dataclass
class TTSOptions:
    voice: str
    format: Format = Format.FORMAT_WAV
    sample_rate: Optional[int] = None
    speed: float = 1.0
    seed: Optional[int] = None
    temperature: Optional[float] = None
    top_p: Optional[float] = None

    # only applies to Play3.0-* and PlayHT2.0-turbo
    text_guidance: Optional[float] = None
    voice_guidance: Optional[float] = None
    repetition_penalty: Optional[float] = None

    # only applies to Play3.0-*
    style_guidance: Optional[float] = None

    # only applies to PlayHT2.0-*
    disable_stabilization: Optional[bool] = None

    # only applies to Play3.0-* and PlayDialogMultilingual-*
    language: Optional[Language] = None

    # only applies to PlayDialog-* and PlayDialogMultilingual-*
    # leave the _2 params None if generating single-speaker audio
    voice_2: Optional[str] = None
    turn_prefix: Optional[str] = None
    turn_prefix_2: Optional[str] = None
    voice_conditioning_seconds: Optional[int] = None
    voice_conditioning_seconds_2: Optional[int] = None
    scene_description: Optional[str] = None
    turn_clip_description: Optional[str] = None
    num_candidates: Optional[int] = None
    candidate_ranking_method: Optional[CandidateRankingMethod] = None

    # DEPRECATED (use sample rate to adjust audio quality)
    quality: Optional[str] = None

    def tts_params(self, text: list[str], voice_engine: Optional[str]) -> api_pb2.TtsParams:

        if voice_engine is None:
            voice_engine = "PlayHT2.0-turbo"
        elif voice_engine != "Play3.0-mini" and voice_engine != "PlayHT2.0-turbo":
            raise ValueError(f"gRPC API only supports PlayHT2.0-turbo, Play3.0-mini (on-prem only); got {voice_engine}")

        language_identifier = None
        if self.language is not None:
            language_identifier = LanguageIdentifiers[self.language]
        params = api_pb2.TtsParams(
            text=text,
            voice=self.voice,
            format=self.format.value,
            quality=api_pb2.QUALITY_DRAFT,  # DEPRECATED (use sample rate to adjust audio quality)
            sample_rate=self.sample_rate,
            language_identifier=language_identifier,
            speed=self.speed,
        )
        # If the hyperparams are unset, let the proto fallback to default.
        if self.temperature is not None:
            params.temperature = self.temperature
        if self.top_p is not None:
            params.top_p = self.top_p
        if self.text_guidance is not None:
            params.text_guidance = self.text_guidance
        if self.voice_guidance is not None:
            params.voice_guidance = self.voice_guidance
        if self.seed is not None:
            params.seed = self.seed
        return params


def output_format_to_mime_type(format: Format) -> str:
    http_format = grpc_format_to_http_format(format)
    if http_format == HTTPFormat.FORMAT_RAW:
        return "audio/basic"
    elif http_format == HTTPFormat.FORMAT_MP3:
        return "audio/mpeg"
    elif http_format == HTTPFormat.FORMAT_WAV:
        return "audio/wav"
    elif http_format == HTTPFormat.FORMAT_OGG:
        return "audio/ogg"
    elif http_format == HTTPFormat.FORMAT_FLAC:
        return "audio/flac"
    elif http_format == HTTPFormat.FORMAT_MULAW:
        return "audio/basic"
    else:
        return "audio/mpeg"  # mp3 by default


def http_prepare_dict(text: List[str], options: TTSOptions, voice_engine: str) -> Dict[str, Any]:
    if voice_engine.startswith("Play3.0"):
        version = "v3"
    elif voice_engine.startswith("PlayHT2.0"):
        version = "v2"
    elif voice_engine.startswith("PlayDialog"):
        version = "ldm"
    else:
        raise ValueError(f"Unknown voice engine: {voice_engine}")
    return {
        "text": text,
        "voice": options.voice,
        "output_format": grpc_format_to_http_format(options.format).value,
        "speed": options.speed,
        "sample_rate": options.sample_rate,
        "voice_engine": voice_engine,
        **{k: v for k, v in {
            "seed": options.seed,
            "temperature": options.temperature,
            "top_p": options.top_p,
            "text_guidance": options.text_guidance,
            "voice_guidance": options.voice_guidance,
            "style_guidance": options.style_guidance,
            "repetition_penalty": options.repetition_penalty,
        }.items() if v is not None},
        "language": options.language.value if options.language is not None else None,
        "version": version,

        # PlayDialog-* and PlayDialogMultilingual-*
        # leave the _2 params None if generating single-speaker audio
        "voice_2": options.voice_2,
        "turn_prefix": options.turn_prefix,
        "turn_prefix_2": options.turn_prefix_2,
        "voice_conditioning_seconds": options.voice_conditioning_seconds,
        "voice_conditioning_seconds_2": options.voice_conditioning_seconds_2,
        "scene_description": options.scene_description,
        "turn_clip_description": options.turn_clip_description,
        "num_candidates": options.num_candidates,
        "candidate_ranking_method": options.candidate_ranking_method.value
        if options.candidate_ranking_method is not None else None,
    }


class CongestionCtrl(Enum):
    """
    Enumerates a streaming congestion control algorithm, used to optimize the rate at which text is sent to Play.
    """

    # The client will not do any congestion control.
    OFF = 0

    # The client will retry requests to the primary address up to two times with a 50ms backoff between attempts.
    #
    # Then it will fall back to the fallback address (if one is configured).  No retry attempts will be made
    # against the fallback address.
    #
    # If you're using Play On-Prem, you should probably be using this congestion control algorithm.
    STATIC_MAR_2023 = 1


class Client:
    LEASE_DATA: Optional[bytes] = None
    LEASE_CACHE_PATH: str = os.path.join(tempfile.gettempdir(), 'playht.temporary.lease')
    LEASE_LOCK = threading.Lock()

    @dataclass
    class AdvancedOptions:
        api_url: str = "https://api.play.ht/api"
        congestion_ctrl: CongestionCtrl = CongestionCtrl.OFF
        metrics_buffer_size: int = 1000
        remove_ssml_tags: bool = False

        # gRPC (PlayHT2.0-turbo and Play3.0-mini-grpc)
        grpc_addr: Optional[str] = None
        insecure: bool = False
        fallback_enabled: bool = False
        auto_refresh_lease: bool = True
        disable_lease_disk_cache: bool = False

        # HTTP/WebSocket (Play3.0-mini-http, Play3.0-mini-ws)
        inference_coordinates_options: InferenceCoordinatesOptions = field(default_factory=InferenceCoordinatesOptions)

    def __init__(
        self,
        user_id: str,
        api_key: str,
        auto_connect: bool = True,
        advanced: Optional["Client.AdvancedOptions"] = None,
    ):
        assert user_id, "user_id is required"
        assert api_key, "api_key is required"

        self._advanced = advanced or self.AdvancedOptions()

        def lease_factory() -> Lease:
            _factory = LeaseFactory(user_id, api_key, self._advanced.api_url)
            if self._advanced.disable_lease_disk_cache:
                return _factory()
            maybe_data = self._lease_cache_read()
            if maybe_data is not None:
                lease = Lease(maybe_data)
                if lease.expires > datetime.now() + timedelta(minutes=5):
                    return lease
            lease = _factory()
            self._lease_cache_write(lease.data)
            return lease

        self._lease_factory = lease_factory
        self._lease: Optional[Lease] = None
        self._rpc: Optional[Tuple[str, Channel]] = None
        self._fallback_rpc: Optional[Tuple[str, Channel]] = None
        self._lock = threading.Lock()
        self._timer: Optional[threading.Timer] = None
        self._telemetry = Telemetry(self._advanced.metrics_buffer_size)
        self._user_id = user_id
        self._api_key = api_key
        self._inference_coordinates: Optional[Dict[str, Any]] = None
        self._ws: Optional[ClientConnection] = None

        if self._advanced.congestion_ctrl == CongestionCtrl.STATIC_MAR_2023:
            self._max_attempts = 3
            self._backoff = 0.05
        else:
            self._max_attempts = 1
            self._backoff = 0

        if auto_connect:
            self.refresh_lease()
            self.warmup()

    def ensure_inference_coordinates(self, force: bool = False):
        if self._inference_coordinates is None or \
                self._inference_coordinates["refresh_at_ms"] < time.time_ns() // 1000000 or \
                force:
            if self._advanced.inference_coordinates_options.coordinates_generator_function is not None:
                self._inference_coordinates = self._advanced.inference_coordinates_options.\
                    coordinates_generator_function(self._user_id, self._api_key,
                                                   self._advanced.inference_coordinates_options)
            else:
                self._inference_coordinates = get_coordinates(self._user_id, self._api_key,
                                                              self._advanced.inference_coordinates_options)

        assert self._inference_coordinates is not None, "No connection"

    def warmup(self):
        self.ensure_inference_coordinates()

        try:
            assert self._inference_coordinates is not None, "No connection"
            requests.options(self._inference_coordinates["Play3.0-mini"]["http_streaming_url"],
                             headers={"Origin": "https://play.ht",
                                      "Access-Control-Request-Method": "POST"})
        except Exception as e:
            logging.warning(f"Failed to warmup: {e}")

    @classmethod
    def _lease_cache_read(cls) -> Optional[bytes]:
        with cls.LEASE_LOCK:
            if cls.LEASE_DATA is not None:
                return cls.LEASE_DATA
            try:
                with filelock.FileLock(cls.LEASE_CACHE_PATH + '.lock'):
                    if not os.path.exists(cls.LEASE_CACHE_PATH):
                        return None
                    with open(cls.LEASE_CACHE_PATH, 'rb') as fp:
                        return fp.read()
            except IOError:
                return None

    @classmethod
    def _lease_cache_write(cls, data: bytes):
        with cls.LEASE_LOCK:
            cls.LEASE_DATA = data
            try:
                with filelock.FileLock(cls.LEASE_CACHE_PATH + '.lock'):
                    with open(cls.LEASE_CACHE_PATH, 'wb') as fp:
                        fp.write(data)
            except IOError:
                return

    def _schedule_refresh(self):
        assert self._lock.locked
        if self._lease is None:
            refresh_in = timedelta(minutes=4, seconds=45).total_seconds()
        else:
            refresh_in = (
                self._lease.expires - timedelta(minutes=5) - datetime.now()
            ).total_seconds()
        self._timer = threading.Timer(refresh_in, self.refresh_lease)
        self._timer.start()

    def refresh_lease(self):
        """Manually refresh credentials with Play."""
        with self._lock:
            if self._lease and self._lease.expires > datetime.now() + timedelta(minutes=5):
                if self._advanced.auto_refresh_lease and self._timer is None:
                    self._schedule_refresh()
                return
            self._lease = self._lease_factory()

            grpc_addr = self._advanced.grpc_addr or self._lease.metadata["inference_address"]

            if self._rpc and self._rpc[0] != grpc_addr:
                self._rpc[1].close()
                self._rpc = None
            if not self._rpc:
                insecure = self._advanced.insecure or "on-prem.play.ht" in grpc_addr
                channel = (
                    insecure_channel(grpc_addr, options=CLIENT_RETRY_OPTIONS) if insecure
                    else secure_channel(grpc_addr, ssl_channel_credentials(), options=CLIENT_RETRY_OPTIONS)
                )
                self._rpc = (grpc_addr, channel)

            # Maybe set up a fallback grpc client
            if self._advanced.fallback_enabled:
                # Choose the fallback address
                # For now, this always is the inference address in the lease, but we can extend in the future
                fallback_addr = self._lease.metadata["inference_address"]

                # Only do fallback if the fallback address is not the same as the primary address
                if grpc_addr != fallback_addr:
                    if self._fallback_rpc and self._fallback_rpc[0] != fallback_addr:
                        self._fallback_rpc[1].close()
                        self._fallback_rpc = None
                    if not self._fallback_rpc:
                        channel = (
                            insecure_channel(fallback_addr, options=CLIENT_RETRY_OPTIONS) if self._advanced.insecure
                            else secure_channel(fallback_addr, ssl_channel_credentials(), options=CLIENT_RETRY_OPTIONS)
                        )
                        self._fallback_rpc = (fallback_addr, channel)

            if self._timer:
                self._timer.cancel()

            if self._advanced.auto_refresh_lease:
                self._schedule_refresh()

    def stream_tts_input(
        self,
        text_stream: Union[Generator[str, None, None], Iterable[str]],
        options: TTSOptions,
        voice_engine: Optional[str] = None
    ) -> Iterable[bytes]:
        """Stream input to Play.ht via the text_stream object."""
        buffer = io.StringIO()
        for text in text_stream:
            t = text.strip()
            buffer.write(t)
            buffer.write(" ")  # normalize word spacing.
            if SENTENCE_END_REGEX.match(t) is None:
                continue
            yield from self.tts(buffer.getvalue(), options, voice_engine)
            buffer = io.StringIO()
        # If text_stream closes, send all remaining text, regardless of sentence structure.
        if buffer.tell() > 0:
            yield from self.tts(buffer.getvalue(), options, voice_engine)

    def tts(
            self,
            text: Union[str, List[str]],
            options: TTSOptions,
            voice_engine: Optional[str] = None,
            streaming: bool = True
    ) -> Iterable[bytes]:
        metrics = self._telemetry.start("tts-request")
        try:
            if voice_engine is None:
                voice_engine = "Play3.0-mini"
                protocol = "http"
            elif voice_engine == "PlayHT2.0-turbo":
                protocol = "grpc"
            elif voice_engine == "Play3.0":
                logging.warning("Voice engine Play3.0 is deprecated; use Play3.0-mini-http instead.")
                voice_engine = "Play3.0-mini"
                protocol = "http"
            elif voice_engine == "Play3.0-ws":
                logging.warning("Voice engine Play3.0-ws is deprecated; use Play3.0-mini-ws instead.")
                voice_engine = "Play3.0-mini"
                protocol = "ws"
            else:
                voice_engine, protocol = voice_engine.rsplit("-", 1)

            if protocol == "http":
                return self._tts_http(text, options, voice_engine, metrics, streaming)
            elif protocol == "ws":
                if streaming:
                    return self._tts_ws(text, options, voice_engine, metrics)
                else:
                    raise ValueError("Non-streaming is not supported for WebSocket API")
            elif protocol == "grpc":
                if streaming:
                    return self._tts_grpc(text, options, voice_engine, metrics)
                else:
                    raise ValueError("Non-streaming is not supported for gRPC API")
            else:
                raise ValueError(f"Unknown protocol {protocol}")
        except Exception as e:
            metrics.finish_error(str(e))
            raise e

    def _tts_grpc(
            self,
            text: Union[str, List[str]],
            options: TTSOptions,
            voice_engine: Optional[str],
            metrics: Metrics
    ) -> Iterable[bytes]:

        supported_voice_engines = ["Play3.0-mini", "PlayHT2.0-turbo"]
        if voice_engine not in supported_voice_engines:
            raise ValueError(f"Only {supported_voice_engines} are supported in the gRPC API; got {voice_engine}")

        start = time.perf_counter()
        self.refresh_lease()
        with self._lock:
            assert self._lease is not None and self._rpc is not None, "No connection"
            lease_data = self._lease.data

        text = prepare_text(text, self._advanced.remove_ssml_tags)
        metrics.append("text", str(text)).append("endpoint", str(self._rpc[0]))

        if options.format == Format.FORMAT_PCM:
            raise ValueError("PCM format is not supported in the gRPC API")
        request = api_pb2.TtsRequest(params=options.tts_params(text, voice_engine), lease=lease_data)

        for attempt in range(1, self._max_attempts + 1):
            try:
                stub = api_pb2_grpc.TtsStub(self._rpc[1])
                stream = stub.Tts(request)  # type: Iterable[api_pb2.TtsResponse]
                chunk_idx = -1
                for chunk in stream:
                    chunk_idx += 1
                    if chunk_idx == _audio_begins_at(options.format):
                        metrics.set_timer("time-to-first-audio", time.perf_counter() - start)
                    yield chunk.data
                metrics.finish_ok()
                break
            except grpc.RpcError as e:
                error_code = getattr(e, "code")()
                logging.debug(f"Error: {error_code}")
                if error_code not in {StatusCode.RESOURCE_EXHAUSTED, StatusCode.UNAVAILABLE}:
                    metrics.finish_error(str(e))
                    raise

                if attempt < self._max_attempts:
                    # It's poor customer experience to show internal details about retries, so we only debug log here.
                    logging.debug(f"Retrying in {self._backoff*1000} ms ({attempt} attempts so far); ({error_code})")
                    metrics.inc("retry").append("retry.reason", str(error_code))
                    metrics.start_timer("retry-backoff")
                    if self._backoff > 0:
                        time.sleep(self._backoff)
                    metrics.finish_timer("retry-backoff")
                    continue

                if self._fallback_rpc is None:
                    metrics.finish_error(str(e))
                    raise

                # We log fallbacks to give customers an extra signal that they should scale up their on-prem appliance
                # (e.g. by paying for more GPU quota)
                logging.info(f"Falling back to {self._fallback_rpc[0]} because {self._rpc[0]} threw: {error_code}")
                metrics.inc("fallback").append("fallback.reason", str(error_code))
                try:
                    metrics.append("text", str(request.params.text)).append("endpoint", str(self._fallback_rpc[0]))
                    stub = api_pb2_grpc.TtsStub(self._fallback_rpc[1])
                    stream = stub.Tts(request)  # type: Iterable[api_pb2.TtsResponse]
                    chunk_idx = -1
                    for chunk in stream:
                        chunk_idx += 1
                        if chunk_idx == _audio_begins_at(options.format):
                            metrics.set_timer("time-to-first-audio", time.perf_counter() - start)
                        yield chunk.data
                    metrics.finish_ok()
                    break
                except grpc.RpcError as fallback_e:
                    metrics.finish_error(str(fallback_e))
                    raise fallback_e from e

    def _tts_http(
            self,
            text: Union[str, List[str]],
            options: TTSOptions,
            voice_engine: Optional[str],
            metrics: Metrics,
            streaming: bool = True
    ) -> Iterable[bytes]:
        supported_voice_engines = ["Play3.0-mini", "PlayDialog", "PlayDialogMultilingual"]
        if voice_engine not in supported_voice_engines:
            raise ValueError(f"Only {supported_voice_engines} are supported in the HTTP API; got {voice_engine}")

        start = time.perf_counter()
        self.ensure_inference_coordinates()
        assert self._inference_coordinates is not None, "No connection"

        if streaming:
            url = self._inference_coordinates[voice_engine]["http_streaming_url"]
        else:
            url = self._inference_coordinates[voice_engine]["http_nonstreaming_url"]

        text = prepare_text(text, self._advanced.remove_ssml_tags)
        metrics.append("text", str(text)).append("endpoint", str(url))

        for attempt in range(1, self._max_attempts + 1):
            try:
                assert self._inference_coordinates is not None, "No connection"
                response = requests.post(
                        url,
                        headers={
                            "accept": output_format_to_mime_type(options.format),
                        },
                        json=http_prepare_dict(text, options, voice_engine),
                        stream=True
                    )
                if response.status_code != 200:
                    raise Exception(f"HTTP {response.status_code}: {response.text}", response.status_code)
                chunk_idx = -1
                for chunk in response.iter_content(chunk_size=None):
                    chunk_idx += 1
                    if chunk_idx == _audio_begins_at(options.format):
                        metrics.set_timer("time-to-first-audio", time.perf_counter() - start)
                    yield chunk
                metrics.finish_ok()
                break
            except Exception as e:
                logging.debug(f"Error: {e}")
                if e.args[1] == "401":
                    self.ensure_inference_coordinates()
                elif e.args[1] not in {429, 503}:  # HTTP equivalent to gRPC RESOURCE_EXHAUSTED, UNAVAILABLE
                    metrics.finish_error(str(e))
                    raise

                if attempt < self._max_attempts:
                    # It's poor customer experience to show internal details about retries, so we only debug log here.
                    logging.debug(f"Retrying in {self._backoff*1000} ms ({attempt} attempts so far); ({e.args[1]})")
                    metrics.inc("retry").append("retry.reason", str(e.args[1]))
                    metrics.start_timer("retry-backoff")
                    if self._backoff > 0:
                        time.sleep(self._backoff)
                    metrics.finish_timer("retry-backoff")
                    continue

                metrics.finish_error(str(e))
                raise

    def _tts_ws(
            self,
            text: Union[str, List[str]],
            options: TTSOptions,
            voice_engine: Optional[str],
            metrics: Metrics
    ) -> Iterable[bytes]:
        supported_voice_engines = ["Play3.0-mini", "PlayDialog", "PlayDialogMultilingual"]
        if voice_engine not in supported_voice_engines:
            raise ValueError(f"Only {supported_voice_engines} are supported in the WebSocket API; got {voice_engine}")

        start = time.perf_counter()
        self.ensure_inference_coordinates()

        text = prepare_text(text, self._advanced.remove_ssml_tags)
        assert self._inference_coordinates is not None, "No connection"
        metrics.append("text", str(text)).append("endpoint",
                                                 str(self._inference_coordinates[voice_engine]["websocket_url"]))
        request_id = str(uuid.uuid4())
        json_data = http_prepare_dict(text, options, voice_engine)
        json_data["request_id"] = request_id

        for attempt in range(1, self._max_attempts + 1):
            try:
                assert self._inference_coordinates is not None, "No connection"
                ws_address = self._inference_coordinates[voice_engine]["websocket_url"]
                if self._ws is None:
                    self._ws = connect(ws_address)
                self._ws.send(json.dumps(json_data))
                chunk_idx = -1
                for chunk in self._ws:
                    chunk_idx += 1
                    if isinstance(chunk, str):
                        msg = json.loads(chunk)
                        if msg["type"] == "end":
                            break
                        else:
                            continue
                    elif chunk_idx == _audio_begins_at(options.format):
                        metrics.set_timer("time-to-first-audio", time.perf_counter() - start)
                    yield chunk
                metrics.finish_ok()
                break
            except Exception as e:
                logging.debug(f"Error: {e}")
                if attempt < self._max_attempts:
                    # It's poor customer experience to show internal details about retries, so we only debug log here.
                    logging.debug(f"Retrying in {self._backoff*1000} ms ({attempt} attempts so far); ({e.args[1]})")
                    metrics.inc("retry").append("retry.reason", str(e.args[1]))
                    metrics.start_timer("retry-backoff")
                    if self._backoff > 0:
                        time.sleep(self._backoff)
                    metrics.finish_timer("retry-backoff")
                    # In case it was an expired token, refresh it
                    self.ensure_inference_coordinates(force=True)
                    continue
                metrics.finish_error(str(e))
                raise

    def get_stream_pair(
        self,
        options: TTSOptions,
        voice_engine: Optional[str] = None
    ) -> Tuple['_InputStream', '_OutputStream']:
        """Get a linked pair of (input, output) streams.

        These stream objects are thread-aware and safe to use in separate threads.
        """
        shared_q = queue.Queue()
        return (
            _InputStream(self, options, shared_q, voice_engine),
            _OutputStream(shared_q)
        )

    def close(self):
        if self._timer:
            self._timer.cancel()
            self._timer = None
        if self._rpc:
            self._rpc[1].close()
            self._rpc = None
        if self._fallback_rpc:
            self._fallback_rpc[1].close()
            self._fallback_rpc = None

    def __del__(self):
        self.close()

    def metrics(self) -> List[Metrics]:
        return self._telemetry.metrics()


class TextStream(Iterator[str]):
    def __init__(self, q: Optional[queue.Queue] = None):
        super().__init__()
        self._q = q or queue.Queue()

    def __iter__(self) -> Iterator[str]:
        return self

    def __next__(self) -> str:
        value = self._q.get()
        if value is None:
            raise StopIteration()
        return value

    def __call__(self, *args: str):
        for a in args:
            self._q.put(a)

    def close(self):
        self._q.put(None)


class _InputStream:
    """Input stream handler for text.

    usage:
       input_stream('send', 'multiple', 'words', 'in', 'one', 'call.')
       input_stream += 'Add another sentence to the stream.'
       input_stream.done()
    """
    def __init__(self, client: Client, options: TTSOptions, q: queue.Queue[Optional[bytes]],
                 voice_engine: Optional[str]):
        self._input = TextStream()

        def listen():
            for output in client.stream_tts_input(self._input, options, voice_engine):
                q.put(output)
            q.put(None)

        self._listener = threading.Thread(None, listen, 'listen-thread')
        self._listener.start()

    def __call__(self, *args: str):
        self._input(*args)

    def __iadd__(self, input: str):
        self._input(input)

    def done(self):
        self._input.close()
        self._listener.join()


class _OutputStream(Iterator[bytes]):
    """Iterator for output audio.

    usage:
       for audio in output_stream:
           <do stuff with audio bytes>
        output_stream.close()
    """
    def __init__(self, q: queue.Queue[Optional[bytes]]):
        self._close = threading.Event()
        self._q = q

    def __iter__(self) -> Iterator[bytes]:
        return self

    def __next__(self) -> bytes:
        while True:
            try:
                value = self._q.get(timeout=0.05)
                break
            except queue.Empty as e:
                if self._close.is_set():
                    raise StopIteration() from e
                continue
        if value is None:
            raise StopIteration()
        return value

    def close(self):
        self._close.set()


def _audio_begins_at(fmt: Format) -> int:
    return 0 if fmt in {Format.FORMAT_RAW, Format.FORMAT_MULAW} else 1
