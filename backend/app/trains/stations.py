# The station we use for each market city (the city as written in the markets
# table), with every spelling the feeds use for it. Each feed names stations
# its own way, e.g. "Bruxelles-Midi" (Eurostar) and "Bruxelles Midi" (gtfs.de).
#
# Brugge is not here: its trains are SNCB's, so Brussels <-> Brugge is entered
# by hand. Brussels is here only as the station where that hand-entered leg
# joins the trains in the feeds.
STATIONS = {
    "Köln": ["Köln Hbf"],
    "Aachen": ["Aachen Hbf"],
    "Nürnberg": ["Nürnberg Hbf"],
    "Rothenburg ob der Tauber": ["Rothenburg ob der Tauber"],
    "Dresden": ["Dresden Hbf"],
    "Strasbourg": ["Strasbourg"],
    "Colmar": ["Colmar"],
    "Brussels": ["Bruxelles-Midi", "Bruxelles Midi"],
}
