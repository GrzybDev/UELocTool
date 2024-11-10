from dataclasses import dataclass, field

from ueloctool.api.formats.locres.string import String


@dataclass
class Namespace:
    name: str
    hash: int | None = None
    strings: list[String] = field(default_factory=lambda: [])
