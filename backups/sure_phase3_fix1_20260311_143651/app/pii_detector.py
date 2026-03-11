from dataclasses import dataclass

from .detectors_polish_ids import detect_polish_ids
from .detectors_personal_pl import detect_personal_pl
from .detectors_financial_technical import detect_financial_technical
from .detectors_basic import detect_basic


@dataclass(frozen=True)
class Entity:
    start: int
    end: int
    type: str
    value: str


def detect(text):
    # Priority:
    # 1) Polish IDs
    # 2) Financial / technical identifiers
    # 3) Personal/address data
    # 4) Basic email/pesel/phone
    raw_entities = (
        detect_polish_ids(text)
        + detect_financial_technical(text)
        + detect_personal_pl(text)
        + detect_basic(text)
    )

    entities = [Entity(start, end, entity_type, value) for start, end, entity_type, value in raw_entities]

    entities.sort(key=lambda e: (e.start, -(e.end - e.start)))
    cleaned = []
    last_end = -1
    for e in entities:
        if e.start >= last_end:
            cleaned.append(e)
            last_end = e.end

    return cleaned
