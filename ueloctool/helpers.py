from io import BufferedReader
from pathlib import Path

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
