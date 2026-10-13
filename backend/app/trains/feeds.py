from dataclasses import dataclass


@dataclass(frozen=True)
class Feed:
    name: str  # short name, also the folder it is saved in
    url: str  # where the GTFS zip is downloaded from
    licence: str
    credit: str  # the attribution the licence asks us to show


# Open timetable feeds (GTFS). Their licences allow reuse with credit, so they
# do not go through the site-review engine. SNCB (Belgium) is not here: its
# feed needs a signed contract, so Brussels <-> Brugge is entered by hand.
FEEDS = [
    Feed(
        name="eurostar",
        url="https://integration-storage.dm.eurostar.com/gtfs-prod/gtfs_static_commercial_v2.zip",
        licence="Licence Ouverte 2.0",
        credit="Eurostar",
    ),
    Feed(
        name="sncf",
        url="https://eu.ftp.opendatasoft.com/sncf/plandata/Export_OpenData_SNCF_GTFS_NewTripId.zip",
        licence="ODbL",
        credit="SNCF Voyageurs",
    ),
    # gtfs.de only covers the next 30 days: download again on or after
    # 1 December to get 15-31 December.
    Feed(
        name="germany_long_distance",
        url="https://download.gtfs.de/germany/fv_free/latest.zip",
        licence="CC BY 4.0",
        credit="gtfs.de",
    ),
    Feed(
        name="germany_regional",
        url="https://download.gtfs.de/germany/rv_free/latest.zip",
        licence="CC BY 4.0",
        credit="gtfs.de",
    ),
]
