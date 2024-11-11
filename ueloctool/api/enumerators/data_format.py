from enum import Enum


class DataFormat(str, Enum):
    JSON = "json"
    CSV = "csv"
    PO = "po"
