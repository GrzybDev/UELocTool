import csv
import json
from abc import ABC, abstractmethod
from io import BufferedReader
from pathlib import Path

from polib import POEntry, POFile

from ueloctool.api.export import ExportMode
from ueloctool.api.string import UnrealString


class Handler(ABC):

    _file_handle: BufferedReader
    _entries: list[UnrealString] = []

    @abstractmethod
    def __init__(self, file: BufferedReader):
        self._file_handle = file

    @abstractmethod
    def parse(self):
        raise NotImplementedError("This method must be implemented by the subclass.")

    def export(self, output_file: Path, mode: ExportMode):
        match mode:
            case ExportMode.JSON:
                self.__export_json(output_file)
            case ExportMode.CSV:
                self.__export_csv(output_file)
            case ExportMode.PO:
                self.__export_po(output_file)
            case _:
                raise Exception("Unsupported export mode.")

    def __export_json(self, output_file: Path):
        result_dict = {}

        for entry in self._entries:
            key = str(entry)

            if key in result_dict:
                raise Exception(f"Duplicate key found: {key}")

            result_dict[key] = entry.value

        with open(output_file, "w", encoding="utf-8") as file_handle:
            json.dump(result_dict, file_handle, indent=4, ensure_ascii=False)

    def __export_csv(self, output_file: Path):
        with open(output_file, "w", encoding="utf-8", newline="") as file_handle:
            writer = csv.DictWriter(
                file_handle, fieldnames=["Key", "SourceString", "TranslatedString"]
            )
            writer.writeheader()

            for entry in self._entries:
                writer.writerow(
                    {
                        "Key": str(entry),
                        "SourceString": entry.value,
                        "TranslatedString": "",
                    }
                )

    def __export_po(self, output_file: Path):
        po = POFile()

        for entry in self._entries:
            po.append(
                POEntry(
                    msgctxt=str(entry),
                    msgid=entry.value,
                    msgstr="",
                )
            )

        po.save(output_file)
