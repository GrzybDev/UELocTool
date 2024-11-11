from pathlib import Path
from typing import Annotated, Optional

import typer

from ueloctool.api.enumerators.data_format import DataFormat
from ueloctool.api.enumerators.missing_string import MissingStringBehaviour
from ueloctool.helpers import get_handler, parse_language_data

app = typer.Typer()


@app.command(name="export")
def cmd_export(
    input_file: Annotated[
        Path, typer.Option(exists=True, file_okay=True, readable=True)
    ],
    output_file: Annotated[Optional[Path], typer.Option(writable=True)] = None,
    output_type: Optional[DataFormat] = DataFormat.JSON,
):
    with open(input_file, "rb") as file_handle:
        handler = get_handler(input_file, file_handle)
        handler.parse()

    if not output_file:
        output_file = input_file.with_suffix(f".{output_type.value}")

    handler.export(output_file, output_type)


@app.command(name="import")
def cmd_import(
    original_file: Annotated[
        Path, typer.Option(exists=True, file_okay=True, readable=True)
    ],
    localization_data_file: Annotated[
        Path, typer.Option(exists=True, file_okay=True, readable=True)
    ],
    output_file: Annotated[Optional[Path], typer.Option(writable=True)] = None,
    missing_strings: Optional[
        MissingStringBehaviour
    ] = MissingStringBehaviour.KeyAndOriginal,
):
    with open(original_file, "rb") as file_handle:
        handler = get_handler(original_file, file_handle)
        handler.parse()

    lang_data = parse_language_data(localization_data_file, missing_strings)

    handler.apply_language_data(lang_data, missing_strings)

    if not output_file:
        output_file = original_file

    handler.save(output_file)
