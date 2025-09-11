import io
import tomllib
from pathlib import Path
from typing import Any, Optional

import pandas as pd
from sexpdata import Symbol, dumps, load  # type: ignore


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
        # get all the symbols
        self._parse_symbols()
            
    
    @staticmethod
    def get_kicad_version(sexp) -> int:
        """Extract the KiCad version from the symbol file header."""
        for item in sexp:
            if isinstance(item, list) and len(item) > 0 and item[0] == Symbol("version"):
                return int(item[1])
        return 0
    
    @staticmethod
    def symbol_derived_from(sexp: list) -> str | None:
        """Check if a symbol is derived from a template and return the template name."""
        for item in sexp:
            if isinstance(item, list) and len(item) > 0 and \
                    item[0] == Symbol("extends"):
                return item[1]
        return None

    def _parse_symbols(self) -> None:
        """Split the symbol file into individual symbols."""
        for item in self._symbol_sexpr[1:]:
            if isinstance(item, list) and len(item) > 0 and item[0] == Symbol("symbol"):
                symbol_name = str(item[1])
                derived_from = self.symbol_derived_from(item)
                is_template = symbol_name.startswith("~")

                assert not (derived_from and is_template), (
                    f"Symbol {symbol_name} cannot be both a template "
                    "and derived from another template"
                )
                # Copy all the symbol data to regenerate the symbol file later
                self._symbols[symbol_name] = item[2:]

    def _extract_properties(self, symbol_sexp: list) -> dict[str, str]:
        """Extract properties from a symbol's S-expression."""
        properties = {}
        for subitem in symbol_sexp:
            if isinstance(subitem, list) and len(subitem) > 0 and subitem[0] == Symbol("property"):
                prop_name = str(subitem[1])
                prop_value = str(subitem[2])
                properties[prop_name] = prop_value
        return properties

    def _handle_derived_symbol(self, symbol_name: str, symbol_sexp: list, template_name: str) -> None:
        """Handle a symbol derived from a template."""
        properties = self._extract_properties(symbol_sexp[2:])
        if template_name not in self._derived_symbols:
            self._derived_symbols[template_name] = []
        self._derived_symbols[template_name].append({symbol_name: properties})
        self._symbols[symbol_name] = symbol_sexp[2:]

    def _handle_template_symbol(self, symbol_name: str, symbol_sexp: list) -> None:
        """Handle a template symbol."""
        self._templates[symbol_name] = [
            i for i in symbol_sexp[2:]
            if isinstance(i, list) and len(i) > 0 and i[0] == Symbol("property")
        ]
        self._symbols[symbol_name] = symbol_sexp[2:]

    def _handle_regular_symbol(self, symbol_name: str, symbol_sexp: list) -> None:
        """Handle a regular (non-derived, non-template) symbol."""
        self._symbols[symbol_name] = symbol_sexp[2:]


