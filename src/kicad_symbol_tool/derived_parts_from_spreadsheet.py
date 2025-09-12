from pathlib import Path

import pandas as pd

from kicad_symbol_tool.kicad_symlib_util import KiCadSymbolLibrary


def generate_spreadsheet_from_symbol_lib(library_path: Path, output_path: Path) -> None:
    """
    Generates an Excel spreadsheet from a KiCad symbol library, organizing derived symbols by their template.
    For each template symbol (identified by names starting with '~'), this function creates a separate sheet in the
    output Excel file. Each sheet contains a list of all symbols derived from that template, with their parameter
    values as columns. The first column in each sheet is always "Symbol Name".

    If the output Excel file already exists, the function will overwrite sheets corresponding to each template.
    Otherwise, it creates a new Excel file.

    Args:
        library_path (Path): Path to the KiCad symbol library file.
        output_path (Path): Path to the output Excel spreadsheet file.

    Returns:
        None
    
    Raises:
        FileNotFoundError: If the specified library file does not exist.
        AssertionError: If the symbol file cannot be parsed, is not a valid KiCad symbol library.
        KiCadVersionError: If the KiCad version is unsupported.
        KeyError: If a requested symbol or template does not exist.
        ValueError: If attempting to create a symbol with a duplicate name or invalid section/mode.
        sexpdata.ExpectClosingBracket, sexpdata.ExpectNothing, sexpdata.ExpectSExp: There was an error
            parsing the symbol file (an s-expression parsing error).
    """
    lib = KiCadSymbolLibrary(library_path)

    # this is a dictionary with keys of all derived symbols in the library derived from a template and a value of the template they are derived from
    derived_symbols = {s: t for s in lib.get_symbol_names() if (t := lib.symbol_derived_from(s)) and t.startswith("~")}

    # I want a spreadsheet sheet with a list of all symbols derived from each template. Note that there may be no symbols derived from a particular template.
    templates = [t for t in lib.get_symbol_names() if t.startswith("~")]

    for t in templates:
        # this is a list of all symbols derived from template t
        symbols_data = []
        for s in [sym for sym, temp in derived_symbols.items() if temp == t]:
            props = lib.get_symbol_properties(s)
            props = props if isinstance(props, dict) else {}
            # Ensure "Symbol Name" is the first column
            props = {"Symbol Name": s, **props}
            symbols_data.append(props)
        
        if not symbols_data:
            # No symbols derived from this template. Create a sheet with the header only.
            df = pd.DataFrame(columns=["Symbol Name", "Value", "Description", "Footprint", "Datasheet", "Reference", "ki_keywords", "ki_fp_filters"])
        else:
            df = pd.DataFrame(symbols_data)

        # Remove the sheet if it already exists to avoid ValueError
        if output_path.exists():
            with pd.ExcelWriter(output_path, engine='openpyxl', mode='a') as writer:
                if t in writer.book.sheetnames:
                    del writer.book[t]
                df.to_excel(writer, sheet_name=t, index=False)
        else:
            with pd.ExcelWriter(output_path, engine='openpyxl', mode='w') as writer:
                df.to_excel(writer, sheet_name=t, index=False)


def generate_derived_parts_from_spreadsheet(lib_path_in: Path, spreadsheet_path: Path, lib_path_out: Path | None = None) -> None:
    """
    Generates derived symbols in a KiCad symbol library from an Excel spreadsheet.
    Each sheet in the spreadsheet corresponds to a template symbol (identified by names starting with '~').
    The first column in each sheet must be "Symbol Name", which specifies the names of the derived symbols to create.
    Subsequent columns represent parameters to set for each derived symbol.

    If a derived symbol already exists in the library, it will be skipped to avoid duplication.

    Args:
        lib_path_in (Path): Path to the KiCad symbol library file.
        spreadsheet_path (Path): Path to the input Excel spreadsheet file.
        lib_path_out (Path | None): Optional path to save the updated KiCad symbol library file.
                                    If None, the input library file will be overwritten.

    Returns:
        None
    """
    lib = KiCadSymbolLibrary(lib_path_in)

    # Read the Excel file
    xls = pd.ExcelFile(spreadsheet_path)

    if not lib_path_out:
        lib_path_out = lib_path_in

    for sheet_name in xls.sheet_names:
        if not sheet_name.startswith("~"):
            continue

        df = pd.read_excel(xls, sheet_name=sheet_name).astype(str)
        assert "Symbol Name" in df.columns, f"Sheet '{sheet_name}' must have a 'Symbol Name' column."

        for _, row in df.iterrows():
            symbol_name = str(row["Symbol Name"])
            if pd.isna(symbol_name):
                print(f"Skipping row with empty 'Symbol Name' in sheet '{sheet_name}'.")
                continue

            try:
                lib.delete_symbol(symbol_name)  # Move it out of the way
            except KeyError:
                pass  # It's okay if it doesn't exist

            properties = {col: str(row[col]) for col in df.columns if col != "Symbol Name" and not pd.isna(row[col])}

            try:
                lib.derive_symbol_from(symbol_name, sheet_name, properties)
                print(f"Added derived symbol '{symbol_name}' from template '{sheet_name}'.")
            except Exception as e:
                print(f"Failed to add symbol '{symbol_name}': {e}")

    # Write back the updated library
    lib.write_library(lib_path_out)

