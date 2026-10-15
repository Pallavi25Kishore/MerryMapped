# MerryMapped

**Your Christmas markets trip, planned reliably around accurate opening hours and train schedules.**

Plan a December trip through the Christmas markets of Germany, Belgium and France, travelling only by
train. Tell it your dates, where to start and end, your pace and your wishes in your own words. It
plans a day-by-day route of markets and real trains and shows it on a map.

## Why it exists

The internet is full of Christmas market information that is out of date, copied from other sites or
simply made up. A blog says a market is open on the 24th; it isn't. A trip built on that is ruined.

MerryMapped uses only two sources:

- **Each market's own official website**, read only where that site's terms allow it.
- **Real train timetables**, from open timetable data published by the railways.

Every fact shown can be traced back to a quote on the official page and the date it was checked,
behind a **"Why can I see this?"** button on each market.

## Two promises, enforced in code

1. **You never land at a closed market.** Every plan is checked against the markets' checked opening
   days and hours and real train times before you see it.
2. **The app never uses data it isn't allowed to use.** A rules engine decides, before every single
   download, whether the site's robots.txt and terms permit it.

## Features

- **Plan in plain words:** pick dates on a December calendar, tap start and end cities on a map, set
  your pace (earliest train, hours per market, train time per day, markets per day) and type wishes
  like "somewhere medieval, with good mulled wine". A confirm screen shows how it was understood.
- **A checked itinerary:** a flowing day-by-day timeline with every train leg, change and wait, the
  railway that runs it, and travel days and free days where markets are closed.
- **Holiday map:** the route drawn as a railway with a little train travelling along it.
- **Market stories:** a short description written in the app's own words, "Don't miss" details and
  vibe tiles, all taken from checked facts.
- **The proof:** "Why can I see this?" opens each fact's source quote (with an English translation),
  page, check date, and what that website's terms allow the app to do, with the reason.
- **Wish review:** each wish is judged against the planned markets' checked facts.
- **Your trips:** every planned trip is saved until you delete it; deleting removes everything and
  shows a receipt.

## System design

```
                  OFFLINE: building the data                         ONLINE: planning a trip

 market website ──► Rules engine ──► Safe fetcher ──► AI reader      Web app (Next.js)
 (robots.txt,        (may we?)        (the only path    (facts +            │
  terms pages)          ▲              to the web,       quotes)             ▼
                        │              logged, polite)      │         FastAPI ──► understand the request (AI + code)
              Site review (YAML,                            ▼                 │
              AI-drafted, approved          Code checks + second AI           ▼
              by a person)                  verifier (quote really on   AI planner drafts a route
                                            page, dates real, no              │
                                            contradictions)                   ▼
                                                    │                   Checker (code) holds it to hard rules
 open GTFS timetables ──► train reader ──► every    │                         │  problems sent back, up to N rounds
 (Eurostar, SNCF,          city-to-city journey     ▼                         ▼
  Deutsche Bahn data,      for each December  ──► Postgres (Neon) ◄──── Repair (code) removes only what breaks,
  SNCB)                    day, up to 2 changes                          with a tip; wishes reviewed; trip saved
```

### 1. Rules engine (legal permission as code)
Every use of a website is a separate **purpose**: read its rules, collect facts, keep short quotes as
proof, write a summary, show a link. The engine answers each one with an explainable decision, and
the first rule that applies decides:

1. App policy: never copy descriptions or photos, whatever the site says.
2. robots.txt blocks the page for our bot, **or for any well-known AI crawler**.
3. Reading a site's robots.txt and terms is always allowed, so they can be reviewed.
4. Instagram is link-only (its terms forbid automated collection).
5. No approved review for the site yet: nothing else is allowed.
6. The site's terms forbid bots: nothing that reads pages.
7. Otherwise, the approved review's answer for that purpose.

Site reviews are drafted by AI from the site's terms pages against a clause guide, then checked and
approved by a person before the engine uses them. Each answer quotes the clause it relies on.

### 2. Safe fetcher and fact pipeline
The **safe fetcher** is the only code path to the web. It asks the engine before every request, sends
a named user agent, waits between requests (longer if robots.txt asks), limits size and redirects,
and logs every attempted visit.

An AI agent navigates a market's site and reads its pages into typed facts: opening and closing
dates, weekly hours, closed days, special hours, address, details and tags. **Each fact must carry
a short quote** from the page. Code then drops anything that fails:

- the quote isn't really on the page, or is too long;
- the dates or times aren't real, or aren't stated in the quote;
- the year isn't stated, or the dates fall outside the 2026 season;
- facts contradict each other (two opening dates, or hours that clash on the same weekday).

A second AI verifier reads each fact against its own quote, and code applies its verdicts. Market
descriptions are written in the app's own words, and code rejects any that share more than five
words in a row with the site.

### 3. Train data (open data)
Timetables come from five official open **GTFS** feeds:

| Feed | Source | Licence |
|---|---|---|
| Eurostar | Eurostar | Licence Ouverte 2.0 |
| SNCF | SNCF Voyageurs | ODbL |
| German long-distance | DELFI e.V. via gtfs.de | CC BY 4.0 |
| German regional | DELFI e.V. via gtfs.de | CC BY 4.0 |
| SNCB | NMBS/SNCB, via transportdata.be | free download (licence not stated) |

A reader matches station names across feeds (for example "Bruxelles-Midi" and "Bruxelles Midi") and
finds every journey between the market cities for each day of the trip, direct or with up to two
changes, respecting boarding rules. When a feed doesn't yet cover a December day, the same weekday's
trains are used and clearly marked as an estimate. Nothing about trains is entered by hand.

### 4. Planner: AI drafts, code decides
Claude drafts a route from the request, the markets' checked facts and the real train options. A
**checker written in plain code** holds every draft to hard rules:

- one day per date, starting and ending where asked;
- each market open on that day, with enough time while it's open, and not repeated on the same day;
- a real train for every journey, within the traveller's pace;
- the route moves onward (no doubling back), new markets before second visits.

Problems go back to the AI to fix, for a few rounds. If something still breaks the rules, a **repair
step in code** removes only what breaks and suggests the smallest change to a setting that would fit
it back in. The AI never has the last word.

## Privacy and security

- One access code protects the whole API; it is compared in constant time, and if none is set,
  everything is refused.
- Trips store only the request and the itinerary: no names, accounts or emails.
- Deleting a trip removes it completely; the receipt is shown once and not stored.
- Secrets live only in an untracked `.env` file.

## Tech stack

**Frontend**
- **Next.js 16** (App Router) with **React 19** and **TypeScript**
- **Tailwind CSS 4** for styling; Fraunces and Nunito fonts via `next/font`
- **SVG** for the maps, drawn from Natural Earth country shapes, with SVG path animation for the
  route and the train; **Canvas** for the sparkles and the night sky
- **Web Audio API** for the optional sound effects (off by default)
- Next.js rewrites proxy `/api` to the backend, so the browser talks to one address

**Backend**
- **Python 3.13** with **FastAPI** (Pydantic models, dependency injection for the database and the
  access code)
- **Anthropic Claude API** (Claude Sonnet 5.5) with **structured JSON output** checked against a
  schema, used for the onboarding agent (tool use), fact reading, fact verifying, site review
  drafting, descriptions, reading requests, planning and the wish review
- **httpx** for fetching, **Protego** for robots.txt, **Beautiful Soup** for cleaning pages,
  **PyYAML** for site reviews
- **GTFS** timetable reader written from scratch (no transit library)

**Database**
- **PostgreSQL** on **Neon** (serverless), through **SQLAlchemy 2** and **psycopg 3**
- Tables for markets, facts (each with its quote, page and check date), train links and trips;
  JSON columns for train journeys and itineraries

**Testing and tooling**
- **pytest**: about 390 tests; AI calls are replaced with pretend answers and the database with
  in-memory SQLite, so the tests run in seconds
- ESLint and TypeScript checks for the frontend; headless Chrome for checking pages during
  development

## Running it

```bash
# Backend: needs backend/.env with ANTHROPIC_API_KEY, DATABASE_URL and ACCESS_CODE
cd backend && python -m venv .venv && .venv/bin/pip install -r requirements-dev.txt
.venv/bin/uvicorn app.main:app --port 8000 --reload
.venv/bin/python -m pytest

# Frontend
cd frontend && npm install && npm run dev   # http://localhost:3000
```

The background picture isn't included because of its licence; see `frontend/README.md` to download it.

## Credits

Train timetables: Eurostar, SNCF Voyageurs, DELFI e.V. via gtfs.de and NMBS/SNCB. Country shapes:
Natural Earth. Background designed by Magnific. Market facts belong to each market's official
website, linked from every market.
