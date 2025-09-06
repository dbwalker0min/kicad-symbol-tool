import io
from sexpdata import load, Symbol, dumps  # type: ignore
import pandas as pd


class KiCadVersionError(Exception):
    pass

def read_symbol_file(file: io.TextIOBase) -> dict[str, dict[str, str]]:
    """Read a KiCad symbol library file and return a dictionary of symbols property values."""
    content = load(file)
    return _parse_symbol_file(content)

def _parse_symbol_file(content: list) -> dict[str, dict[str, str]]:
    """Recursively parse the S-expression content of a KiCad symbol library."""
    # Find version
    version = None
    for item in content:
        if isinstance(item, list) and len(item) > 0 and item[0] == Symbol("version"):
            version = float(item[1])
            break
    if version is None or version < 6.0:
        raise KiCadVersionError("KiCad symbol library version must be >= 6.0")

    symbols = {}
    for item in content:
        if isinstance(item, list) and len(item) > 0 and item[0] == Symbol("symbol"):
            symbol_name = str(item[1])
            properties = {}
            extends_symbol = None
            for subitem in item:
                if isinstance(subitem, list) and len(subitem) > 0:
                    if subitem[0] == Symbol("property"):
                        prop_name = str(subitem[1])
                        prop_value = str(subitem[2])
                        properties[prop_name] = prop_value
                    elif subitem[0] == Symbol("extends"):
                        extends_symbol = str(subitem[1])
            symbol_dict = properties.copy()
            if extends_symbol is not None:
                symbol_dict["extends"] = extends_symbol
            symbols[symbol_name] = symbol_dict
    return symbols

def write_symbols_to_xlsx(symbols: dict[str, dict[str, str]], filename: str):
    templates = [name for name in symbols if name.startswith("~")]
    with pd.ExcelWriter(filename) as writer:
        for template in templates:
            template_props = [k for k in symbols[template] if k != "extends"]
            # Find symbols that extend this template
            derived = []
            for name, props in symbols.items():
                if props.get("extends") == template:
                    row = {"Symbol": name}
                    for prop in template_props:
                        row[prop] = props.get(prop, "")
                    derived.append(row)
            if derived:
                df = pd.DataFrame(derived, columns=["Symbol"] + template_props)
                df.to_excel(writer, sheet_name=template, index=False)

def update_sexp_with_symbols(content: list, updated_symbols: dict[str, dict[str, str]]) -> list:
    # Traverse the S-expression and update symbol properties
    for item in content:
        if isinstance(item, list) and len(item) > 0 and item[0] == Symbol("symbol"):
            symbol_name = str(item[1])
            if symbol_name in updated_symbols:
                props = updated_symbols[symbol_name]
                # Update properties in-place
                for subitem in item:
                    if isinstance(subitem, list) and len(subitem) > 0 and subitem[0] == Symbol("property"):
                        prop_name = str(subitem[1])
                        if prop_name in props:
                            subitem[2] = props[prop_name]
    return content

def write_symbol_dict_to_sexp(symbols: dict[str, dict[str, str]], output_filename: str, original_sexp: list) -> None:
    # Update the original S-expression with new symbol properties
    updated_sexp = update_sexp_with_symbols(original_sexp, symbols)
    # Write to file
    with open(output_filename, "w", encoding="utf-8") as f:
        f.write(dumps(updated_sexp))

