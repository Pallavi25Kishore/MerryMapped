from app.planning.checker import MarketInfo
from app.reading.market_reader import TAGS

TILES = 3  # vibe tiles shown per market
PRACTICAL = {"vegan-options", "accessible", "paid-entry"}  # facilities, not vibe: no tile


def label(tag: str) -> str:
    return tag.replace("-", " ").capitalize()


def vibe_tiles(market: MarketInfo) -> list[str]:
    """Up to three tiles showing a market's vibe: its checked tags in the order of our tag list
    (setting, then theme, then food and extras), leaving out practical ones."""
    tags = {fact["value"]["tag"] for fact in market.facts if fact["kind"] == "tag"}
    return [label(tag) for tag in TAGS if tag in tags and tag not in PRACTICAL][:TILES]
