from enum import StrEnum


class Purpose(StrEnum):
    """The uses MerryMapped can ask permission for. Each is judged separately."""

    READ_TERMS = "read_terms"                    # read robots.txt and terms pages to learn the rules
    COLLECT_FACTS = "collect_facts"              # a bot or AI reads pages and notes dates, hours, location
    KEEP_EVIDENCE = "keep_evidence"              # store, translate and show one short quoted sentence as proof
    WRITE_SUMMARY = "write_summary"              # reword the market description in our own words, briefly
    SHOW_LINK = "show_link"                      # show a link to the site or its official Instagram
    COPY_TEXT_OR_PHOTOS = "copy_text_or_photos"  # copy descriptions or images: never allowed
