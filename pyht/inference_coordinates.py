from __future__ import annotations

import asyncio
from dataclasses import dataclass
import requests
import time
from typing import Callable, Awaitable, Optional, Dict, Any

import aiohttp

REQUIRED_MODELS = ["Play3.0-mini", "PlayDialog"]
REQUIRED_URLS = ["http_streaming_url", "websocket_url"]


@dataclass
class InferenceCoordinatesOptions:
    api_url: str = "https://api.play.ht/api/v3"
    coordinates_generator_function: Optional[Callable[[str, str, InferenceCoordinatesOptions],
                                                      Dict[str, Any]]] = None
    coordinates_generator_function_async: Optional[Callable[[str, str, InferenceCoordinatesOptions],
                                                            Awaitable[Dict[str, Any]]]] = None
    coordinates_expiration_minimal_frequency_ms: int = 60_000
    coordinates_expiration_advance_refresh_ms: int = 300_000
    coordinates_get_api_call_max_retries: int = 3


def default_coordinates_generator(user_id: str, api_key: str,
                                  options: InferenceCoordinatesOptions) -> Dict[str, Any]:
    try:
        response = requests.post(f"{options.api_url}/auth?dialog",
                                 headers={"x-user-id": user_id, "authorization": f"Bearer {api_key}"})
        response.raise_for_status()
        return response.json()
    except requests.RequestException as e:
        raise RuntimeError(f"Failed to get inference coordinates: {e}") from e


async def default_coordinates_generator_async(user_id: str, api_key: str,
                                              options: InferenceCoordinatesOptions) -> Dict[str, Any]:
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(f"{options.api_url}/auth?dialog",
                                    headers={"x-user-id": user_id,
                                             "authorization": f"Bearer {api_key}"}) as response:
                response.raise_for_status()
                return await response.json()
    except requests.RequestException as e:
        raise RuntimeError(f"Failed to get inference coordinates: {e}") from e


def get_coordinates(user_id: str, api_key: str,
                    options: InferenceCoordinatesOptions, attempt: int = 1) -> Dict[str, Any]:
    try:
        if options.coordinates_generator_function is not None:
            coordinates = options.coordinates_generator_function(user_id, api_key, options)
        else:
            coordinates = default_coordinates_generator(user_id, api_key, options)
        assert "expires_at_ms" in coordinates, "Coordinates response must contain expires_at_ms"
        # schedule next refresh
        coordinates["refresh_at_ms"] = min(coordinates["expires_at_ms"] -
                                           options.coordinates_expiration_advance_refresh_ms,
                                           time.time_ns() // 1000000 +
                                           options.coordinates_expiration_minimal_frequency_ms)
        for model in REQUIRED_MODELS:
            assert model in coordinates, f"Coordinates response must contain model {model}"
            for url in REQUIRED_URLS:
                assert url in coordinates[model], \
                    f"Coordinates response must contain {url} for model {model}"
            coordinates[model]["http_nonstreaming_url"] = \
                coordinates[model]["http_streaming_url"].replace("stream", "")
        return coordinates
    except Exception as e:
        if attempt >= options.coordinates_get_api_call_max_retries:
            raise e
        else:
            time.sleep(0.5 ** (attempt + 1))
            return get_coordinates(user_id, api_key, options, attempt + 1)


async def get_coordinates_async(user_id: str, api_key: str,
                                options: InferenceCoordinatesOptions, attempt: int = 1) -> Dict[str, Any]:
    try:
        if options.coordinates_generator_function_async is not None:
            coordinates = await options.coordinates_generator_function_async(user_id, api_key, options)
        else:
            coordinates = await default_coordinates_generator_async(user_id, api_key, options)
        assert "expires_at_ms" in coordinates, "Coordinates response must contain expires_at_ms"
        # schedule next refresh
        coordinates["refresh_at_ms"] = min(coordinates["expires_at_ms"] -
                                           options.coordinates_expiration_advance_refresh_ms,
                                           time.time_ns() // 1000000 +
                                           options.coordinates_expiration_minimal_frequency_ms)
        for model in REQUIRED_MODELS:
            assert model in coordinates, f"Coordinates response must contain model {model}"
            for url in REQUIRED_URLS:
                assert url in coordinates[model], \
                    f"Coordinates response must contain {url} for model {model}"
            coordinates[model]["http_nonstreaming_url"] = \
                coordinates[model]["http_streaming_url"].replace("stream", "")
        return coordinates
    except Exception as e:
        if attempt >= options.coordinates_get_api_call_max_retries:
            raise e
        else:
            await asyncio.sleep(0.5 ** (attempt + 1))
            return await get_coordinates_async(user_id, api_key, options, attempt + 1)
