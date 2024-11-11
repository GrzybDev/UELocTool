import csv
import json
from abc import ABC, abstractmethod
from io import BufferedReader
from pathlib import Path

from polib import POEntry, POFile

from ueloctool.api.enumerators.data_format import DataFormat
from ueloctool.api.enumerators.missing_string import MissingStringBehaviour


class Handler(ABC):

    _file_handle: BufferedReader

    @abstractmethod
    def __init__(self, file: BufferedReader):
        self._file_handle = file

    @abstractmethod
    def parse(self):
        raise NotImplementedError("This method must be implemented by the subclass.")

    def export(self, data: tuple[str, str], output_file: Path, mode: DataFormat):
        match mode:
            case DataFormat.JSON:
                self.__export_json(data, output_file)
            case DataFormat.CSV:
                self.__export_csv(data, output_file)
            case DataFormat.PO:
                self.__export_po(data, output_file)
            case _:
                raise Exception("Unsupported export mode.")

    def __export_json(self, data: tuple[str, str], output_file: Path):
        result_dict = {}

        for key, value in data:
            if key in result_dict:
                raise Exception(f"Duplicate key found: {key}")

            result_dict[key] = value

        with open(output_file, "w", encoding="utf-8") as file_handle:
            json.dump(result_dict, file_handle, indent=4, ensure_ascii=False)

    def __export_csv(self, data: tuple[str, str], output_file: Path):
        with open(output_file, "w", encoding="utf-8", newline="") as file_handle:
            writer = csv.DictWriter(
                file_handle, fieldnames=["Key", "SourceString", "TranslatedString"]
            )
            writer.writeheader()

            for key, value in data:
                writer.writerow(
                    {
                        "Key": key,
                        "SourceString": value,
                        "TranslatedString": "",
                    }
                )

    def __export_po(self, data: tuple[str, str], output_file: Path):
        po = POFile()

        for key, value in data:
            po.append(POEntry(msgctxt=key, msgid=value))

        po.save(output_file)

    @abstractmethod
    def apply_language_data(
        self, data: dict[str, str], missing_strings_behaviour: MissingStringBehaviour
    ):
        raise NotImplementedError("This method must be implemented by the subclass.")

    @abstractmethod
    def save(self, output_file: Path):
        raise NotImplementedError("This method must be implemented by the subclass.")
