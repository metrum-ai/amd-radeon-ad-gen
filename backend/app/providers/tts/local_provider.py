# Copyright Advanced Micro Devices, Inc.
#
# SPDX-License-Identifier: MIT

"""Local Kokoro TTS -- same HTTP interface, different URL."""

from app.config import settings
from app.providers.tts.api_provider import APITTSProvider


class LocalTTSProvider(APITTSProvider):
    """Local Kokoro TTS using the same HTTP interface at a local URL."""

    def __init__(self) -> None:
        super().__init__()
        self._base_url = settings.local_tts_url
