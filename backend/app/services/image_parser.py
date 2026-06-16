"""Extract trade alert text from images using Claude Vision API."""
from __future__ import annotations

import base64
import logging

log = logging.getLogger(__name__)

_PROMPT = (
    "You are a trading alert parser. Extract all trading information from this image.\n"
    "Return ONLY the trade alert text as plain text. Include every detail you can see:\n"
    "  - Ticker symbol (e.g. SPX, SPY, QQQ, IWM)\n"
    "  - Strategy type (e.g. bull put spread, iron condor, single leg)\n"
    "  - Option type (CALL / PUT)\n"
    "  - Strike prices\n"
    "  - Expiration date\n"
    "  - Entry price / premium\n"
    "  - Stop loss\n"
    "  - Target / exit prices\n"
    "  - Any other relevant fields\n\n"
    "If this is not a trade alert image, return exactly: NOT_TRADE_ALERT\n"
    "Do not add any explanation or commentary — only the extracted trade text."
)


async def extract_text_from_image(image_bytes: bytes, media_type: str = "image/jpeg") -> str:
    """Return trade alert text extracted from image bytes, or '' if not a trade alert."""
    import anthropic
    from app.core.config import settings

    if not settings.ANTHROPIC_API_KEY:
        log.warning("ANTHROPIC_API_KEY not set — cannot extract text from image")
        return ""

    client = anthropic.AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY)
    image_data = base64.standard_b64encode(image_bytes).decode("utf-8")

    async with client.messages.stream(
        model="claude-haiku-4-5",
        max_tokens=1024,
        messages=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "image",
                        "source": {
                            "type": "base64",
                            "media_type": media_type,
                            "data": image_data,
                        },
                    },
                    {"type": "text", "text": _PROMPT},
                ],
            }
        ],
    ) as stream:
        response = await stream.get_final_message()

    for block in response.content:
        if hasattr(block, "text"):
            text = block.text.strip()
            if text == "NOT_TRADE_ALERT":
                log.info("image is not a trade alert")
                return ""
            log.info("extracted %d chars from image", len(text))
            return text

    return ""
