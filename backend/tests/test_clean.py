from app.reading.clean import Link, clean_html

PAGE_URL = "https://koeln-market.example/"

SAMPLE = """\
<html>
<head>
  <meta charset="utf-8">
  <title>Weihnachtsmarkt Köln</title>
  <style>.nav { color: red; }</style>
  <script>window.tracking = "secret-script-code";</script>
</head>
<body>
  <nav><a href="/programm">Programm</a> <a href="/programm#dez">Programm im Dezember</a></nav>
  <h1>Weihnachtsmarkt am Dom</h1>
  <p>Der Markt öffnet am <b>19. November 2026</b>.</p>


  <p>Glühwein   und   Süßes</p>
  <table>
    <tr><th>Tage</th><th>Uhrzeit</th></tr>
    <tr><td>Mo–Do</td><td>11–21 Uhr</td></tr>
  </table>
  <footer>
    <a href="/impressum">Impressum</a>
    <a href="mailto:info@koeln-market.example">E-Mail</a>
    <a href="tel:+49000000000">Anrufen</a>
  </footer>
</body>
</html>
"""


def clean_sample():
    return clean_html(SAMPLE.encode("utf-8"), PAGE_URL)


def test_title_is_kept():
    assert clean_sample().title == "Weihnachtsmarkt Köln"


def test_scripts_and_styles_are_removed():
    text = clean_sample().text

    assert "secret-script-code" not in text
    assert "color: red" not in text


def test_bold_date_does_not_break_the_sentence():
    assert "Der Markt öffnet am 19. November 2026." in clean_sample().text.splitlines()


def test_tables_stay_readable():
    lines = clean_sample().text.splitlines()

    assert "Tage | Uhrzeit" in lines
    assert "Mo–Do | 11–21 Uhr" in lines


def test_links_are_full_addresses():
    assert Link("Impressum", "https://koeln-market.example/impressum") in clean_sample().links


def test_footer_links_are_kept():
    urls = [link.url for link in clean_sample().links]

    assert "https://koeln-market.example/impressum" in urls


def test_no_duplicate_links_or_section_endings():
    urls = [link.url for link in clean_sample().links]

    assert urls.count("https://koeln-market.example/programm") == 1
    assert not any("#" in url for url in urls)


def test_email_and_phone_links_are_skipped():
    urls = [link.url for link in clean_sample().links]

    assert not any(url.startswith(("mailto:", "tel:")) for url in urls)


def test_german_letters_survive():
    text = clean_sample().text

    assert "öffnet" in text
    assert "Glühwein und Süßes" in text


def test_empty_lines_and_extra_spaces_are_removed():
    lines = clean_sample().text.splitlines()

    assert "" not in lines
    assert "Glühwein und Süßes" in lines
