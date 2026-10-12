from dataclasses import dataclass
from urllib.parse import urldefrag, urljoin

from bs4 import BeautifulSoup

# Parts of a page that are never visible text.
INVISIBLE = ["head", "script", "style", "noscript", "template", "svg", "iframe"]

# Elements that start a new line on screen. A line break is added after each one.
BLOCKS = ["p", "div", "br", "li", "h1", "h2", "h3", "h4", "h5", "h6",
          "section", "article", "header", "footer", "nav", "ul", "ol", "table"]


@dataclass(frozen=True)
class Link:
    text: str  # the clickable words, e.g. "Impressum"
    url: str   # the full address


@dataclass(frozen=True)
class CleanPage:
    """A page reduced to what the AI readers need: its title, visible text and links."""

    title: str
    text: str
    links: tuple[Link, ...]


def clean_html(html: bytes | str, page_url: str) -> CleanPage:
    """Strip a downloaded page down to its title, visible text and links."""
    soup = BeautifulSoup(html, "html.parser")
    title = soup.title.get_text(strip=True) if soup.title else ""

    for tag in soup(INVISIBLE):
        tag.decompose()

    links, seen = [], set()
    for a in soup.find_all("a", href=True):
        url, _ = urldefrag(urljoin(page_url, a["href"]))
        if url.startswith(("http://", "https://")) and url not in seen:
            seen.add(url)
            links.append(Link(a.get_text(" ", strip=True), url))

    for row in soup.find_all("tr"):
        cells = [cell.get_text(" ", strip=True) for cell in row.find_all(["td", "th"])]
        row.replace_with(" | ".join(cells) + "\n")

    for tag in soup.find_all(BLOCKS):
        tag.insert_after("\n")

    lines = (" ".join(line.split()) for line in soup.get_text().splitlines())
    text = "\n".join(line for line in lines if line)
    return CleanPage(title, text, tuple(links))
