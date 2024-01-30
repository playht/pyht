from google.protobuf.internal import containers as _containers
from google.protobuf.internal import enum_type_wrapper as _enum_type_wrapper
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from typing import ClassVar as _ClassVar, Iterable as _Iterable, Mapping as _Mapping, Optional as _Optional, Union as _Union

DESCRIPTOR: _descriptor.FileDescriptor

class Code(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = ()
    CODE_UNSPECIFIED: _ClassVar[Code]
    CODE_COMPLETE: _ClassVar[Code]
    CODE_IN_PROGRESS: _ClassVar[Code]
    CODE_CANCELED: _ClassVar[Code]
    CODE_ERROR: _ClassVar[Code]

class Quality(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = ()
    QUALITY_UNSPECIFIED: _ClassVar[Quality]
    QUALITY_LOW: _ClassVar[Quality]
    QUALITY_DRAFT: _ClassVar[Quality]
    QUALITY_MEDIUM: _ClassVar[Quality]
    QUALITY_HIGH: _ClassVar[Quality]
    QUALITY_PREMIUM: _ClassVar[Quality]

class Format(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = ()
    FORMAT_RAW: _ClassVar[Format]
    FORMAT_MP3: _ClassVar[Format]
    FORMAT_WAV: _ClassVar[Format]
    FORMAT_OGG: _ClassVar[Format]
    FORMAT_FLAC: _ClassVar[Format]
    FORMAT_MULAW: _ClassVar[Format]
CODE_UNSPECIFIED: Code
CODE_COMPLETE: Code
CODE_IN_PROGRESS: Code
CODE_CANCELED: Code
CODE_ERROR: Code
QUALITY_UNSPECIFIED: Quality
QUALITY_LOW: Quality
QUALITY_DRAFT: Quality
QUALITY_MEDIUM: Quality
QUALITY_HIGH: Quality
QUALITY_PREMIUM: Quality
FORMAT_RAW: Format
FORMAT_MP3: Format
FORMAT_WAV: Format
FORMAT_OGG: Format
FORMAT_FLAC: Format
FORMAT_MULAW: Format

class TtsRequest(_message.Message):
    __slots__ = ("lease", "params")
    LEASE_FIELD_NUMBER: _ClassVar[int]
    PARAMS_FIELD_NUMBER: _ClassVar[int]
    lease: bytes
    params: TtsParams
    def __init__(self, lease: _Optional[bytes] = ..., params: _Optional[_Union[TtsParams, _Mapping]] = ...) -> None: ...

class TtsResponse(_message.Message):
    __slots__ = ("sequence", "id", "data", "status")
    SEQUENCE_FIELD_NUMBER: _ClassVar[int]
    ID_FIELD_NUMBER: _ClassVar[int]
    DATA_FIELD_NUMBER: _ClassVar[int]
    STATUS_FIELD_NUMBER: _ClassVar[int]
    sequence: int
    id: str
    data: bytes
    status: Status
    def __init__(self, sequence: _Optional[int] = ..., id: _Optional[str] = ..., data: _Optional[bytes] = ..., status: _Optional[_Union[Status, _Mapping]] = ...) -> None: ...

class TtsParams(_message.Message):
    __slots__ = ("text", "voice", "quality", "format", "sample_rate", "speed", "seed", "temperature", "top_p", "voice_guidance", "text_guidance", "other")
    TEXT_FIELD_NUMBER: _ClassVar[int]
    VOICE_FIELD_NUMBER: _ClassVar[int]
    QUALITY_FIELD_NUMBER: _ClassVar[int]
    FORMAT_FIELD_NUMBER: _ClassVar[int]
    SAMPLE_RATE_FIELD_NUMBER: _ClassVar[int]
    SPEED_FIELD_NUMBER: _ClassVar[int]
    SEED_FIELD_NUMBER: _ClassVar[int]
    TEMPERATURE_FIELD_NUMBER: _ClassVar[int]
    TOP_P_FIELD_NUMBER: _ClassVar[int]
    VOICE_GUIDANCE_FIELD_NUMBER: _ClassVar[int]
    TEXT_GUIDANCE_FIELD_NUMBER: _ClassVar[int]
    OTHER_FIELD_NUMBER: _ClassVar[int]
    text: _containers.RepeatedScalarFieldContainer[str]
    voice: str
    quality: Quality
    format: Format
    sample_rate: int
    speed: float
    seed: int
    temperature: float
    top_p: float
    voice_guidance: float
    text_guidance: float
    other: str
    def __init__(self, text: _Optional[_Iterable[str]] = ..., voice: _Optional[str] = ..., quality: _Optional[_Union[Quality, str]] = ..., format: _Optional[_Union[Format, str]] = ..., sample_rate: _Optional[int] = ..., speed: _Optional[float] = ..., seed: _Optional[int] = ..., temperature: _Optional[float] = ..., top_p: _Optional[float] = ..., voice_guidance: _Optional[float] = ..., text_guidance: _Optional[float] = ..., other: _Optional[str] = ...) -> None: ...

class Status(_message.Message):
    __slots__ = ("code", "message")
    CODE_FIELD_NUMBER: _ClassVar[int]
    MESSAGE_FIELD_NUMBER: _ClassVar[int]
    code: Code
    message: _containers.RepeatedScalarFieldContainer[str]
    def __init__(self, code: _Optional[_Union[Code, str]] = ..., message: _Optional[_Iterable[str]] = ...) -> None: ...
