from pathlib import Path
from typing import Annotated, Optional

import typer

from ueloctool.api.export import ExportMode
from ueloctool.api.formats.locres.main import LocresFile
from ueloctool.api.handler import Handler

app = typer.Typer()

available_formats = [LocresFile]


@app.command()
def export(
    input_file: Annotated[
        Path, typer.Option(exists=True, file_okay=True, readable=True)
    ],
    output_file: Annotated[Optional[Path], typer.Option(writable=True)] = None,
    output_type: Optional[ExportMode] = ExportMode.JSON,
):
    with open(input_file, "rb") as file_handle:
        handler: Handler = None

        # Determine the file format
        if input_file.suffix == ".locres":
            handler = LocresFile(file_handle, allow_legacy=True)
        else:
            # Fallback - we don't know the file format based on the extension
            # Try all available formats

            for format in available_formats:
                try:
                    handler = format(file_handle)
                    break
                except Exception:
                    pass

        if handler is None:
            raise Exception("Could not determine the file format.")

        handler.parse()

        if not output_file:
            output_file = input_file.with_suffix(f".{output_type.value}")

        # Export the parsed data
        handler.export(output_file, output_type)
