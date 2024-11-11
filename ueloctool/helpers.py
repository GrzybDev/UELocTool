import csv
import json
from io import BufferedReader
from pathlib import Path

import polib

from ueloctool.api.enumerators.data_format import DataFormat
from ueloctool.api.enumerators.missing_string import MissingStringBehaviour
from ueloctool.api.formats.locres.main import LocresFile
from ueloctool.api.handler import Handler

AVAILABLE_FORMATS = [LocresFile]


def get_handler(input_file: Path, file_handle: BufferedReader) -> Handler:
    handler: Handler = None

    # Determine the file format
    if input_file.suffix == ".locres":
        handler = LocresFile(file_handle, allow_legacy=True)
    else:
        # Fallback - we don't know the file format based on the extension
        # Try all available formats

        for format in AVAILABLE_FORMATS:
            try:
                handler = format(file_handle)
                break
            except Exception:
                pass

    if handler is None:
        raise Exception("Could not determine the file format.")

    return handler


def parse_language_data(
    input_file: Path, missing_strings: MissingStringBehaviour
) -> dict[str, str]:
    def __get_translated_string(key, original_string, translated_string):
        # Only for CSV and PO files, JSON files are handled in apply methods
        if translated_string:
            return translated_string

        match missing_strings:
            case MissingStringBehaviour.KeyAndOriginal:
                return f"({key}) {original_string}"
            case MissingStringBehaviour.Key:
                return key
            case MissingStringBehaviour.Original:
                return original_string
            case MissingStringBehaviour.Empty:
                return ""
            case MissingStringBehaviour.Remove:
                return None
            case MissingStringBehaviour.Error:
                raise Exception(f"Missing localized string for {key}")

    data_type = DataFormat(input_file.suffix[1:])

    match data_type:
        case DataFormat.JSON:
            with open(input_file, "r", encoding="utf-8") as file_handle:
                return json.load(file_handle)
        case DataFormat.CSV:
            with open(input_file, "r", encoding="utf-8", newline="") as file_handle:
                reader = csv.DictReader(file_handle)
                data = {}

                for row in reader:
                    translated_string = __get_translated_string(
                        row["Key"], row["SourceString"], row["TranslatedString"]
                    )

                    if translated_string is None:
                        continue

                    data[row["Key"]] = translated_string

                return data
        case DataFormat.PO:
            po_file = polib.pofile(input_file)
            data = {}

            for entry in po_file:
                translated_string = __get_translated_string(
                    entry.msgctxt, entry.msgid, entry.msgstr
                )

                if translated_string is None:
                    continue

                data[entry.msgctxt] = translated_string

            return data
