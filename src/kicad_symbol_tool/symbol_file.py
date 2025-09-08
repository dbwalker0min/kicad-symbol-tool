import io
from typing import Any, Optional
from sexpdata import load, Symbol, dumps  # type: ignore
import pandas as pd
from pathlib import Path
import tomllib


class KiCadVersionError(Exception):
    pass

def get_project_version(pyproject_path: Path) -> str:
    with open(pyproject_path, "rb") as f:
        data = tomllib.load(f)
    # Astral uv projects use [project] table for version
    return data["project"]["version"]

_pyproject_path = Path(__file__).parent.parent.parent / "pyproject.toml"
_project_version = get_project_version(_pyproject_path)


class KiCadSymbolLibrary:
    """Class to represent a KiCad symbol library file."""

    # the header for a kicad symbol file

    _symbol_file_header = [
        Symbol("kicad_symbol_lib"),
        [Symbol("version"), 20241209],
        [Symbol("generator"), "kicad_symbol_tool"],
        [Symbol("generator_version"), _project_version],
    ]

    def __init__(self, symbol_file: Path, sexp: Optional[list] = None) -> None:
        """Initialize the KiCadSymbolLibrary by reading and parsing the symbol file."""
        self.file: Path = symbol_file
        # Keep this for later use
        if sexp:
            self._symbol_sexpr = sexp
        else:
            with open(symbol_file, "r", encoding="utf-8") as f:
                self._symbol_sexpr = load(f)

        # this is for the S-expression content for each symbol which is a template or a non-derived symbol
        self._symbols: dict[str, list] = {}
        # these are for templates. The name of the template always starts with ~
        self._templates: dict[str, list] = {}
        # these are for the derived symbols. The key is the template name, the value is a list of symbols derived from that template.
        self._derived_symbols: dict[str, list[dict[str, Any]]] = {}

        # check the file validity
        assert isinstance(self._symbol_sexpr, list), "Failed to parse symbol file"
        assert self._symbol_sexpr[0] == Symbol("kicad_symbol_lib"), "Not a valid KiCad symbol library file"
        assert self.get_kicad_version(self._symbol_sexpr[1:]) >= 20211014, "KiCad symbol library version must be >= 6.0"
        self._get_symbols()
            
    
    @staticmethod
    def get_kicad_version(sexp) -> int:
        """Extract the KiCad version from the symbol file header."""
        for item in sexp:
            if isinstance(item, list) and len(item) > 0 and item[0] == Symbol("version"):
                return int(item[1])
        return 0
    
    @staticmethod
    def symbol_derived_from(sexp: list) -> Optional[str]:
        """Check if a symbol is derived from a template and return the template name."""
        for item in sexp:
            if isinstance(item, list) and len(item) > 0 and item[0] == Symbol("extends"):
                return item[1]
        return None

    def _get_symbols(self) -> None:
        """Split the symbol file into individual symbols."""
        for item in self._symbol_sexpr[1:]:
            if isinstance(item, list) and len(item) > 0 and item[0] == Symbol("symbol"):
                symbol_name = str(item[1])
                derived_table = self.symbol_derived_from(item)

                assert not derived_table and symbol_name.startswith("~"), f"Symbol {symbol_name} cannot be both a template and derived from another template"
                if derived_table:
                    # buzz though the symbol and pull out the properties into a dictionary
                    properties = {}
                    for subitem in item[2:]:
                        if isinstance(subitem, list) and len(subitem) > 0 and subitem[0] == Symbol("property"):
                            prop_name = str(subitem[1])
                            prop_value = str(subitem[2])
                            properties[prop_name] = prop_value
                # keep all the properties in the symbol but the `Symbol('name')` and the name itself
                self._symbols[symbol_name] = item[2:]


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
            # Always include new_name for renaming
            symbol_dict["new_name"] = symbol_name
            if extends_symbol is not None:
                symbol_dict["extends"] = extends_symbol
            symbols[symbol_name] = symbol_dict
    return symbols


def write_symbols_to_xlsx(symbols: dict[str, dict[str, str]], filename: str):
    """Write symbols to an xlsx file, each template on its own sheet."""
    templates = [name for name in symbols if name.startswith("~")]
    with pd.ExcelWriter(filename) as writer:
        for template in templates:
            template_props = [k for k in symbols[template]
                              if k not in ("extends", "new_name")]
            # Find symbols that extend this template
            derived = []
            for name, props in symbols.items():
                if props.get("extends") == template:
                    row = {"Symbol": name}
                    for prop in template_props:
                        row[prop] = props.get(prop, "")
                    row["new_name"] = props.get("new_name", name)
                    derived.append(row)
            if derived:
                df = pd.DataFrame(derived, columns=[
                                  "Symbol"] + ["new_name"] + template_props)
                df.to_excel(writer, sheet_name=template, index=False)


def update_sexp_with_symbols(content: list, updated_symbols: dict[str, dict[str, str]]) -> list:
    """Traverse the S-expression and update symbol properties and names."""
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
                # Rename symbol if 'new_name' is present and different
                if "new_name" in props and props["new_name"] != symbol_name:
                    item[1] = props["new_name"]
    return content


def write_symbol_dict_to_sexp(symbols: dict[str, dict[str, str]], output_filename: str, original_sexp: list) -> None:
    """Update the original S-expression with new symbol properties and write to file."""
    updated_sexp = update_sexp_with_symbols(original_sexp, symbols)
    with open(output_filename, "w", encoding="utf-8") as f:
        f.write(dumps(updated_sexp))


def read_xlsx_and_apply_to_sexp(xlsx_filename: str, original_symbols: dict[str, dict[str, str]], original_sexp: list, output_filename: str):
    """Read the xlsx file, apply changes to the parsed sexp, and write to a new symbol table."""
    xls = pd.ExcelFile(xlsx_filename)
    updated_symbols = original_symbols.copy()
    for sheet_name in xls.sheet_names:
        df = pd.read_excel(xls, sheet_name=sheet_name)
        for _, row in df.iterrows():
            symbol_name = row["Symbol"]
            if symbol_name in updated_symbols:
                for prop in row.index:
                    if prop != "Symbol" and pd.notnull(row[prop]):
                        updated_symbols[symbol_name][prop] = str(row[prop])
    write_symbol_dict_to_sexp(updated_symbols, output_filename, original_sexp)
