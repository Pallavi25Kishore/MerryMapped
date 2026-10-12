import httpx

from app.fetcher.robots import get_robots_txt, make_client

PAGE = "https://www.koeln-market.example/markt/termine"


def pretend_site(handler):
    """A downloader wired to a pretend website: handler decides every answer."""
    return make_client(transport=httpx.MockTransport(handler))


def always(status, text=""):
    """A pretend website that gives the same answer to every request."""
    return pretend_site(lambda request: httpx.Response(status, text=text))


def test_found_file_gives_its_text():
    assert get_robots_txt(PAGE, always(200, "User-agent: *\nDisallow: /markt\n")) == (
        "User-agent: *\nDisallow: /markt\n"
    )


def test_missing_file_gives_empty_text():
    assert get_robots_txt(PAGE, always(404)) == ""


def test_server_error_gives_none():
    assert get_robots_txt(PAGE, always(500)) is None


def test_too_many_requests_gives_none():
    assert get_robots_txt(PAGE, always(429)) is None


def test_no_answer_gives_none():
    def no_answer(request):
        raise httpx.ConnectError("site unreachable")

    assert get_robots_txt(PAGE, pretend_site(no_answer)) is None


def test_moved_file_is_followed():
    def moved(request):
        if request.url.host == "www.koeln-market.example":
            return httpx.Response(301, headers={"Location": "https://koeln-market.example/robots.txt"})
        return httpx.Response(200, text="User-agent: *\nDisallow:\n")

    assert get_robots_txt(PAGE, pretend_site(moved)) == "User-agent: *\nDisallow:\n"


def test_asks_for_robots_txt_on_the_pages_own_site():
    asked = []

    def record(request):
        asked.append(str(request.url))
        return httpx.Response(404)

    get_robots_txt(PAGE, pretend_site(record))

    assert asked == ["https://www.koeln-market.example/robots.txt"]


def test_sends_our_bot_name():
    seen = []

    def record(request):
        seen.append(request.headers["User-Agent"])
        return httpx.Response(404)

    get_robots_txt(PAGE, pretend_site(record))

    assert seen[0].startswith("MerryMappedBot")
