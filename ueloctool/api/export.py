from enum import Enum


class ExportMode(str, Enum):
    JSON = "json"
    CSV = "csv"
    PO = "po"
