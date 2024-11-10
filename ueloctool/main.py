from pathlib import Path
from typing import Annotated, Optional

import typer

from ueloctool.api.enumerators.export import ExportMode
from ueloctool.helpers import get_handler

app = typer.Typer()


@app.command(name="export")
def cmd_export(
    input_file: Annotated[
        Path, typer.Option(exists=True, file_okay=True, readable=True)
    ],
    output_file: Annotated[Optional[Path], typer.Option(writable=True)] = None,
    output_type: Optional[ExportMode] = ExportMode.JSON,
):
    with open(input_file, "rb") as file_handle:
        handler = get_handler(input_file, file_handle)
        handler.parse()

    if not output_file:
        output_file = input_file.with_suffix(f".{output_type.value}")

    handler.export(output_file, output_type)

