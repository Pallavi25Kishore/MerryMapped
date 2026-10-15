from urllib.parse import urlparse

import httpx

# Our bot's name tag, sent with every request. The link says who runs it.
BOT_USER_AGENT = "MerryMappedBot/0.1 (+https://github.com/Pallavi25Kishore/MerryMapped)"


def make_client(transport: httpx.BaseTransport | None = None) -> httpx.Client:
    """The downloader every fetch uses: our name tag and a 10-second time limit."""
    return httpx.Client(headers={"User-Agent": BOT_USER_AGENT}, timeout=10.0, transport=transport)


def robots_url(page_url: str) -> str:
    """The robots.txt address for a page's site."""
    parts = urlparse(page_url)
    return f"{parts.scheme}://{parts.netloc}/robots.txt"


def get_robots_txt(page_url: str, client: httpx.Client) -> str | None:
    """Download the robots.txt for a page's site, in the form the rules engine expects.

    Returns its text, "" if the site has none, or None if it could not be fetched (RFC 9309).
    """
    try:
        response = client.get(robots_url(page_url), follow_redirects=True)
    except httpx.HTTPError:
        return None  # no answer at all: treat as everything blocked

    if response.status_code == 200:
        return response.text
    if response.status_code == 429:
        return None  # "too many requests" is not "no rules"
    if 400 <= response.status_code < 500:
        return ""    # no robots.txt: no restrictions
    return None      # server error: treat as everything blocked
