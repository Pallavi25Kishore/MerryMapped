# The station we use for each market city (the city as written in the markets
# table), with every spelling the feeds use for it. Each feed names stations
# its own way, e.g. "Bruxelles-Midi" (Eurostar) and "Bruxelles Midi" (gtfs.de).
# Accents and country tags such as "(DE)" are ignored when names are compared,
# so "Köln Hbf (DE)" (SNCB) matches "Köln Hbf".
#
# Brussels is not a market city: it is where most trips to Brugge change trains.
STATIONS = {
    "Köln": ["Köln Hbf"],
    "Aachen": ["Aachen Hbf"],
    "Nürnberg": ["Nürnberg Hbf"],
    "Rothenburg ob der Tauber": ["Rothenburg ob der Tauber"],
    "Dresden": ["Dresden Hbf"],
    "Strasbourg": ["Strasbourg"],
    "Colmar": ["Colmar"],
    "Brussels": ["Bruxelles-Midi", "Bruxelles Midi"],
    "Brugge": ["Brugge", "Bruges"],  # SNCB's feed uses French names
}

# Where each station is (latitude, longitude). Some names are used for more than
# one place, e.g. "Bruges" is also a town near Bordeaux in SNCF's feed: only the
# station near this position counts as the city's station.
POSITIONS = {
    "Köln": (50.943, 6.959),
    "Aachen": (50.768, 6.091),
    "Nürnberg": (49.446, 11.083),
    "Rothenburg ob der Tauber": (49.377, 10.191),
    "Dresden": (51.040, 13.732),
    "Strasbourg": (48.585, 7.734),
    "Colmar": (48.074, 7.348),
    "Brussels": (50.836, 4.336),
    "Brugge": (51.197, 3.217),
}

# The country each city is in, for showing the cities grouped on the website.
COUNTRIES = {
    "Köln": "Germany", "Aachen": "Germany", "Nürnberg": "Germany", "Rothenburg ob der Tauber": "Germany",
    "Dresden": "Germany", "Strasbourg": "France", "Colmar": "France", "Brussels": "Belgium", "Brugge": "Belgium",
}

# Cities that are train hubs only, with no market of their own.
HUBS = {"Brussels"}
