from google.protobuf.internal import containers as _containers
from google.protobuf.internal import enum_type_wrapper as _enum_type_wrapper
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from typing import ClassVar as _ClassVar, Iterable as _Iterable, Mapping as _Mapping, Optional as _Optional, Union as _Union

CODE_CANCELED: Code
CODE_COMPLETE: Code
CODE_ERROR: Code
CODE_IN_PROGRESS: Code
CODE_UNSPECIFIED: Code
DESCRIPTOR: _descriptor.FileDescriptor
FORMAT_FLAC: Format
FORMAT_MP3: Format
FORMAT_MULAW: Format
FORMAT_OGG: Format
FORMAT_PCM: Format
FORMAT_RAW: Format
FORMAT_WAV: Format
QUALITY_DRAFT: Quality
QUALITY_HIGH: Quality
QUALITY_LOW: Quality
QUALITY_MEDIUM: Quality
QUALITY_PREMIUM: Quality
QUALITY_UNSPECIFIED: Quality

class Status(_message.Message):
    __slots__ = ["code", "message"]
    CODE_FIELD_NUMBER: _ClassVar[int]
    MESSAGE_FIELD_NUMBER: _ClassVar[int]
    code: Code
    message: _containers.RepeatedScalarFieldContainer[str]
    def __init__(self, code: _Optional[_Union[Code, str]] = ..., message: _Optional[_Iterable[str]] = ...) -> None: ...

class TtsParams(_message.Message):
    __slots__ = ["format", "language_identifier", "other", "quality", "sample_rate", "seed", "speed", "temperature", "text", "text_guidance", "top_p", "voice", "voice_guidance"]
    FORMAT_FIELD_NUMBER: _ClassVar[int]
    LANGUAGE_IDENTIFIER_FIELD_NUMBER: _ClassVar[int]
    OTHER_FIELD_NUMBER: _ClassVar[int]
    QUALITY_FIELD_NUMBER: _ClassVar[int]
    SAMPLE_RATE_FIELD_NUMBER: _ClassVar[int]
    SEED_FIELD_NUMBER: _ClassVar[int]
    SPEED_FIELD_NUMBER: _ClassVar[int]
    TEMPERATURE_FIELD_NUMBER: _ClassVar[int]
    TEXT_FIELD_NUMBER: _ClassVar[int]
    TEXT_GUIDANCE_FIELD_NUMBER: _ClassVar[int]
    TOP_P_FIELD_NUMBER: _ClassVar[int]
    VOICE_FIELD_NUMBER: _ClassVar[int]
    VOICE_GUIDANCE_FIELD_NUMBER: _ClassVar[int]
    format: Format
    language_identifier: int
    other: str
    quality: Quality
    sample_rate: int
    seed: int
    speed: float
    temperature: float
    text: _containers.RepeatedScalarFieldContainer[str]
    text_guidance: float
    top_p: float
    voice: str
    voice_guidance: float
    def __init__(self, text: _Optional[_Iterable[str]] = ..., voice: _Optional[str] = ..., quality: _Optional[_Union[Quality, str]] = ..., format: _Optional[_Union[Format, str]] = ..., sample_rate: _Optional[int] = ..., speed: _Optional[float] = ..., seed: _Optional[int] = ..., temperature: _Optional[float] = ..., top_p: _Optional[float] = ..., voice_guidance: _Optional[float] = ..., language_identifier: _Optional[int] = ..., text_guidance: _Optional[float] = ..., other: _Optional[str] = ...) -> None: ...

class TtsRequest(_message.Message):
    __slots__ = ["lease", "params"]
    LEASE_FIELD_NUMBER: _ClassVar[int]
    PARAMS_FIELD_NUMBER: _ClassVar[int]
    lease: bytes
    params: TtsParams
    def __init__(self, lease: _Optional[bytes] = ..., params: _Optional[_Union[TtsParams, _Mapping]] = ...) -> None: ...

class TtsResponse(_message.Message):
    __slots__ = ["data", "id", "sequence", "status"]
    DATA_FIELD_NUMBER: _ClassVar[int]
    ID_FIELD_NUMBER: _ClassVar[int]
    SEQUENCE_FIELD_NUMBER: _ClassVar[int]
    STATUS_FIELD_NUMBER: _ClassVar[int]
    data: bytes
    id: str
    sequence: int
    status: Status
    def __init__(self, sequence: _Optional[int] = ..., id: _Optional[str] = ..., data: _Optional[bytes] = ..., status: _Optional[_Union[Status, _Mapping]] = ...) -> None: ...

class Code(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = []

class Quality(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = []

class Format(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = []
