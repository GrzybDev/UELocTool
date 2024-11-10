from dataclasses import dataclass


@dataclass
class UnrealString:
    namespace: str = None
    key: str = None
    value: str = None

    def __str__(self) -> str:
        return f"{self.namespace}::{self.key}" if self.namespace else self.key
