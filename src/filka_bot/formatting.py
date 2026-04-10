EMOJI_PREFIX = "🙄🤖 "


def with_emoji_prefix(text: str) -> str:
    text = text.strip()
    if not text:
        return EMOJI_PREFIX.strip()
    if text.startswith(EMOJI_PREFIX):
        return text
    return f"{EMOJI_PREFIX}{text}"

