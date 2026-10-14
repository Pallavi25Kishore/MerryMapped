from app.planning.checker import MarketInfo
from app.planning.itinerary import vibe_tiles


def tagged(*tags: str) -> MarketInfo:
    return MarketInfo("A market", "Köln", [{"kind": "tag", "value": {"tag": tag}} for tag in tags]
                      + [{"kind": "detail", "value": {"text": "mulled wine"}}])


def test_tiles_follow_our_tag_list_order_and_stop_at_three():
    market = tagged("stage-programme", "light-show", "family", "sustainable", "cathedral", "artisan")
    assert vibe_tiles(market) == ["Cathedral", "Light show", "Sustainable"]


def test_practical_tags_get_no_tile():
    assert vibe_tiles(tagged("vegan-options", "family", "paid-entry", "accessible")) == ["Family"]


def test_a_market_without_tags_has_no_tiles():
    assert vibe_tiles(tagged()) == []
