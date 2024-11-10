from dataclasses import dataclass


@dataclass
class String:
    key: str
    key_hash: int
    value: str
    value_hash: int
