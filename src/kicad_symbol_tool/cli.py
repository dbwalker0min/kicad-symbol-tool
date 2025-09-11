import os
import shutil
import sys
from pathlib import Path

import typer
from sexpdata import ExpectClosingBracket, ExpectNothing, ExpectSExp

from kicad_symbol_tool import (
    KiCadVersionError,
    generate_derived_parts_from_spreadsheet,
    generate_spreadsheet_from_symbol_lib,
)

app = typer.Typer()


def _process_lib_file(lib_file: Path, force: bool) -> None:
    # the name of the excel file is the same as the library file but with an .xlsx extension
    xlsx_file = lib_file.with_suffix(".xlsx")

    if not xlsx_file.exists() or force:
        # create the template spreadsheet
        try:
            generate_spreadsheet_from_symbol_lib(lib_file, xlsx_file)
        except FileNotFoundError as e:
            sys.exit(f'File not found: {e}', code=1)
        except (ValueError, AssertionError, KiCadVersionError, KeyError, ExpectClosingBracket, ExpectNothing, ExpectSExp) as e:
            sys.exit(f'Error: {e}', code=1)

        # set the time of the xlsx file to be the same as the lib file so it doesn't try to update it next time
        lib_mtime_ns = os.stat(lib_file).st_mtime_ns
        os.utime(xlsx_file, ns=(lib_mtime_ns, lib_mtime_ns))
        print(f"Created {xlsx_file}. Please populate it and rerun the utility.")
        return

    xlsx_mtime = os.stat(xlsx_file).st_mtime_ns
    lib_mtime_ns = os.stat(lib_file).st_mtime_ns

    # this checks for strictly greater than, so if they are the same time (like it was just created), it won't try to update
    if xlsx_mtime > lib_mtime_ns:
        # Make a backup of the lib_file before modifying it
        backup_file = lib_file.with_suffix(lib_file.suffix + ".bak")
        try:
            shutil.copy2(lib_file, backup_file)
            print(f"Backup created: {backup_file}")
        except Exception as e:
            sys.exit(f'Failed to create backup: {e}', code=1)

        try:
            generate_derived_parts_from_spreadsheet(lib_file, xlsx_file)
        except (ValueError, AssertionError, KiCadVersionError, KeyError, ExpectClosingBracket, ExpectNothing, ExpectSExp) as e:
            sys.exit(f'Error: {e}', code=1)
    else:
        print(f"No changes to apply for {lib_file}.")


@app.command()
def main(lib_file_or_dir: Path, force: bool = False) -> None:
    """
    Synchronizes KiCad symbol library files (.kicad_sym) with their corresponding Excel spreadsheets (.xlsx).
    If the spreadsheet does not exist, it will be created as a template.
    If the spreadsheet is newer than the symbol library, changes from the spreadsheet will be applied to the symbol library.

    Args:
        lib_file_or_dir (Path): Path to a .kicad_sym file or a directory containing .kicad_sym files.
        force (bool): If set to True, forces the creation of the xlsx template even if the file exists.
    """
    if not lib_file_or_dir.exists():
        sys.exit(f'Library file or directory "{lib_file_or_dir}" does not exist.', code=1)

    if lib_file_or_dir.is_dir():
        for lib_file in lib_file_or_dir.glob("*.kicad_sym"):
            _process_lib_file(lib_file, force)
    else:
        _process_lib_file(lib_file_or_dir, force)


if __name__ == "__main__":
    app()
