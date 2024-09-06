from __future__ import annotations

import asyncio
from dataclasses import dataclass
import requests
from threading import Timer
import time
from typing import Callable, Awaitable, Optional

import aiohttp


@dataclass
class InferenceCoordinatesOptions:
    api_url: str = "https://api.play.ht/api/v3"
    coordinates_generator_function: Optional[Callable[[str, str, InferenceCoordinatesOptions],
                                                      "InferenceCoordinates"]] = None
    coordinates_generator_function_async: Optional[Callable[[str, str, InferenceCoordinatesOptions],
                                                            Awaitable["InferenceCoordinates"]]] = None
    coordinates_expiration_minimal_frequency_ms: int = 60_000
    coordinates_expiration_advance_refresh_ms: int = 300_000
    coordinates_get_api_call_max_retries: int = 3


@dataclass
class InferenceCoordinates:
    address: str
    expires_ms: int

    @classmethod
    def default_generator(cls, user_id: str, api_key: str,
                          options: InferenceCoordinatesOptions) -> "InferenceCoordinates":
        try:
            response = requests.post(f"{options.api_url}/auth",
                                     headers={"x-user-id": user_id, "authorization": f"Bearer {api_key}"})
            response.raise_for_status()
            data = response.json()
            return cls(data["inference_address"], data["expires_at_ms"])
        except requests.RequestException as e:
            raise RuntimeError(f"Failed to get inference coordinates: {e}") from e

    @classmethod
    async def default_generator_async(cls, user_id: str, api_key: str,
                                      options: InferenceCoordinatesOptions) -> "InferenceCoordinates":
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(f"{options.api_url}/auth",
                                        headers={"x-user-id": user_id,
                                                 "authorization": f"Bearer {api_key}"}) as response:
                    response.raise_for_status()
                    data = await response.json()
            return cls(data["inference_address"], data["expires_at_ms"])
        except requests.RequestException as e:
            raise RuntimeError(f"Failed to get inference coordinates: {e}") from e

    @classmethod
    def get(cls, user_id: str, api_key: str,
            options: InferenceCoordinatesOptions, attempt: int = 1) -> "InferenceCoordinates":
        try:
            if options.coordinates_generator_function is not None:
                coordinates = options.coordinates_generator_function(user_id, api_key, options)
            else:
                coordinates = cls.default_generator(user_id, api_key, options)
            # schedule next refresh
            refresh_delay_ms = max(options.coordinates_expiration_minimal_frequency_ms,
                                   coordinates.expires_ms - time.time_ns() // 1_000_000 -
                                   options.coordinates_expiration_advance_refresh_ms)
            timer = Timer(refresh_delay_ms / 1_000, cls.get, args=(user_id, api_key, options, attempt))
            timer.daemon = True
            timer.start()
            return coordinates
        except Exception as e:
            if attempt >= options.coordinates_get_api_call_max_retries:
                raise e
            else:
                time.sleep(0.5 * (attempt + 1))
                return cls.get(user_id, api_key, options, attempt + 1)

    @classmethod
    async def get_async(cls, user_id: str, api_key: str,
                        options: InferenceCoordinatesOptions, attempt: int = 1) -> "InferenceCoordinates":
        try:
            if options.coordinates_generator_function_async is not None:
                coordinates = await options.coordinates_generator_function_async(user_id, api_key, options)
            else:
                coordinates = await cls.default_generator_async(user_id, api_key, options)
            # schedule next refresh
            refresh_delay_ms = max(options.coordinates_expiration_minimal_frequency_ms,
                                   coordinates.expires_ms - time.time_ns() // 1_000_000 -
                                   options.coordinates_expiration_advance_refresh_ms)
            timer = Timer(refresh_delay_ms / 1_000, cls.get_async, args=(user_id, api_key, options, attempt))
            timer.daemon = True
            timer.start()
            return coordinates
        except Exception as e:
            if attempt >= options.coordinates_get_api_call_max_retries:
                raise e
            else:
                await asyncio.sleep(0.5 * (attempt + 1))
                return await cls.get_async(user_id, api_key, options, attempt + 1)
