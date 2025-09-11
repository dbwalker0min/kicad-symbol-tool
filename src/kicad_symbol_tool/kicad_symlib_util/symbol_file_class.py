import tomllib
from copy import deepcopy
from pathlib import Path

from sexpdata import Symbol, dumps, load

"""
File: symbol_file_class.py

    This module provides the `KiCadSymbolLibrary` class and related utilities for reading, manipulating, and writing KiCad 
    symbol library files in S-expression format. It enables parsing symbol files, extracting and modifying symbol properties, 
    managing symbol inheritance, and generating new derived symbols. The module also handles version checking and supports 
    writing updated symbol libraries back to disk.

    Classes:
        KiCadSymbolLibrary: Represents a KiCad symbol library file and provides methods for symbol management.
        KiCadVersionError: Exception raised for KiCad version-related errors.

    Functions:
        get_project_version(pyproject_path: Path) -> str:
            Reads the project version from a pyproject.toml file.

    Constants:
        _valid_kicad_symbol_sections: List of valid section names within a symbol.

    Typical usage example:
        library = KiCadSymbolLibrary(Path("my_symbols.kicad_sym"))
        properties = library.get_symbol_properties("R_0805")
        library.modify_properties("R_0805", {"Value": "10k"})
        library.write_library(Path("my_symbols_modified.kicad_sym"))
"""


# Sections that are valid within a symbol at the root level
_valid_kicad_symbol_sections = [
    "pin_numbers",
    "pin_names",
    "property",
    "in_bom",
    "on_board",
    "exclude_from_sim",
    "symbol",
    "extends",
]


class KiCadVersionError(Exception):
    """Exception raised for unsupported KiCad versions."""

    pass


def _get_project_version(pyproject_path: Path) -> str:
    """Return the project version.

    Prefer the installed distribution metadata (importlib.metadata). If the
    distribution isn't installed (for example during development), fall back to
    reading a local pyproject.toml if present. If neither is available return
    a safe default.
    """
    # First, try to get the installed package version (works when installed
    # from PyPI or in editable mode with proper metadata).
    try:
        import importlib.metadata as _metadata

        try:
            return _metadata.version("kicad-symbol-tool")
        except _metadata.PackageNotFoundError:
            # Not installed as a distribution in this environment; fall through
            pass
    except Exception:
        # importlib.metadata might not be available for some reason; fall back
        # to reading pyproject.toml below.
        pass

    # Fallback: read pyproject.toml if it's available alongside the source.
    try:
        if pyproject_path.exists():
            with open(pyproject_path, "rb") as f:
                data = tomllib.load(f)
            return data.get("project", {}).get("version", "0.0.0")
    except Exception:
        # Any parsing/IO errors -> return default version
        pass

    # Last resort
    return "0.0.0"


# Access the project version from the pyproject.toml file
_project_version = _get_project_version(Path(__file__).parent.parent.parent.parent / "pyproject.toml")


class KiCadSymbolLibrary:
    """
    KiCadSymbolLibrary(symbol_file: Path, sexp: list | None = None)
    Represents a KiCad symbol library file, providing methods to read, parse, manipulate, and write
    the symbol definitions in the KiCad S-expression format.

    This class allows you to:
    - Load and parse a KiCad symbol library file or a pre-parsed S-expression.
    - Access and modify symbol properties.
    - Derive new symbols from templates.
    - Delete symbols from the library.
    - Write the modified library back to disk.

    Attributes:
        file (Path): Path to the KiCad symbol library file.
        _symbol_sexpr (list): Parsed S-expression content of the symbol file.
        _symbols (dict[str, list]): Dictionary mapping symbol names to their S-expression data.
        _kicad_version (int | None): Version of the KiCad symbol library format.

    Methods:
        get_kicad_version() -> int:
            Returns the KiCad symbol library version number.
        symbol_derived_from(symbol_name: str) -> str | None:
            Returns the name of the template symbol if the specified symbol is derived from one.
        get_symbol_properties(symbol_name: str) -> dict[str, str] | None:
            Retrieves the properties of a specified symbol as a dictionary.
        delete_symbol(symbol_name: str) -> None:
        get_symbol(symbol_name: str) -> list | None:
            Retrieves a deep copy of the full S-expression for the specified symbol.
        modify_properties(symbol_name: str, new_properties: dict[str, str]) -> None:
            Updates the properties of a specified symbol by replacing existing property values.
        modify_symbol_sections(symbol_sexp: list, sections: list[str], mode: str) -> list:
        derive_symbol_from(new_symbol_name: str, template_symbol_name: str, properties: dict[str, str]) -> None:
            Creates a new symbol derived from a template symbol with specified properties.
        write_library(output_path: Path | None = None) -> None:
    """

    # the header for a kicad symbol utility file
    _symbol_file_header = [
        Symbol("kicad_symbol_lib"),
        [Symbol("version"), 20241209],
        [Symbol("generator"), "kicad-symlib-util"],
        [Symbol("generator_version"), _project_version],
    ]

    def __init__(self, symbol_file: Path, sexp: list | None = None) -> None:
        """
        Initialize the KiCadSymbolLibrary by reading and parsing the symbol file.

        Args:
            symbol_file (Path): Path to the KiCad symbol library file.
            sexp (list, optional): Pre-parsed S-expression list representing the symbol file content.
                If not provided, the file will be read and parsed.
        Raises:
            AssertionError: If the symbol file cannot be parsed, is not a valid KiCad symbol library.
            KiCadVersionError: If the KiCad version is unsupported.
                    AssertionError: If the symbol file cannot be parsed, is not a valid KiCad symbol library.
            KeyError: If a requested symbol or template does not exist.
            ValueError: If attempting to create a symbol with a duplicate name or invalid section/mode.
            KiCadVersionError: If the KiCad version is unsupported.
            sexpdata.ExpectClosingBracket, sexpdata.ExpectNothing, sexpdata.ExpectSExp: There was an error
                parsing the symbol file (an s-expression parsing error).


        Side Effects:
            - Loads and stores the S-expression content of the symbol file.
            - Extracts individual symbols into a dictionary for later use.
            - Stores the version of the KiCad symbol library format.
        """
        self.file: Path = symbol_file
        # Keep this for later use
        if sexp:
            self._symbol_sexpr = sexp
        else:
            with open(symbol_file, encoding="utf-8") as f:
                self._symbol_sexpr = load(f)

        # this is for the S-expression content for each symbol which is a template or a non-derived symbol
        self._symbols: dict[str, list] = {}

        # the version of the kicad symbol library format
        self._kicad_version: int | None = None

        # check the file validity
        assert isinstance(self._symbol_sexpr, list), "Failed to parse symbol file"
        assert self._symbol_sexpr[0] == Symbol("kicad_symbol_lib"), "Not a valid KiCad symbol library file"
        assert self.get_kicad_version() >= 20211014, "KiCad symbol library version must be >= 6.0"

        # Split the symbol file into individual symbols.
        for item in self._symbol_sexpr[1:]:
            if isinstance(item, list) and len(item) > 0 and item[0] == Symbol("symbol"):
                # Copy all the symbol data to regenerate the symbol file later
                self._symbols[str(item[1])] = item[2:]

    def get_kicad_version(self) -> int:
        """
        Extracts and returns the KiCad version number from the symbol file.
        Returns:
            int: The KiCad version number if found, otherwise 0.
        """

        # the version has already been extracted and cached
        if self._kicad_version is not None:
            return self._kicad_version

        for item in self._symbol_sexpr[1:]:
            if isinstance(item, list) and len(item) > 0 and item[0] == Symbol("version"):
                self._kicad_version = int(item[1])
                return int(item[1])
        # The version was not found. Return 0 (a guaranteed bad version)
        return 0

    def symbol_derived_from(self, symbol_name: str) -> str | None:
        """
        Determines if the specified symbol is derived from a template.

        Args:
            symbol_name (str): The name of the symbol to check.

        Returns:
            str | None: The name of the template symbol if the symbol is derived from one, otherwise None.
        """
        for item in self._symbols.get(symbol_name, []):
            if isinstance(item, list) and len(item) > 0 and item[0] == Symbol("extends"):
                return item[1]
        return None

    def get_symbol_properties(self, symbol_name: str) -> dict[str, str] | None:
        """
        Retrieve the properties of a specified symbol as a dictionary.

        Args:
            symbol_name (str): The name of the symbol to retrieve properties for.

        Returns:
            dict[str, str] | None: A dictionary containing property names and their corresponding values
            if the symbol exists, otherwise None.
        """
        symbol_sexp = self._symbols.get(symbol_name)
        if not symbol_sexp:
            return None

        properties = {}
        for subitem in self._symbols[symbol_name]:
            if isinstance(subitem, list) and len(subitem) > 0 and subitem[0] == Symbol("property"):
                prop_name = str(subitem[1])
                prop_value = str(subitem[2])
                properties[prop_name] = prop_value
        return properties

    def delete_symbol(self, symbol_name: str) -> None:
        """
        Removes the specified symbol from the library.

        Args:
            symbol_name (str): The name of the symbol to delete.

        Raises:
            KeyError: If the symbol with the given name does not exist in the library.
        """
        try:
            del self._symbols[symbol_name]
        except KeyError as e:
            raise KeyError(f"Symbol {symbol_name} not found in library.") from e

    def get_symbol(self, symbol_name: str) -> list | None:
        """
        Retrieves a deep copy of the full S-expression for the specified symbol from the library.

        This method ensures that the returned symbol data is a deep copy, so any modifications to the result
        will not affect the original symbol stored in the library. If the symbol isn't found, it returns None.

        Args:
            symbol_name (str): The name of the symbol to retrieve.

        Returns:
            list | None: A deep copy of the symbol's S-expression as a list, or None if the symbol is not found.

        Example:
            >>> symbol = symbol_file.get_symbol("R_0805")
            >>> if symbol:
            ...     # Work with a safe copy of the symbol's S-expression
            ...     pass
        """
        if symbol_name not in self._symbols:
            return None
        return deepcopy(self._symbols[symbol_name])

    def modify_properties(self, symbol_name: str, new_properties: dict[str, str]) -> None:
        """
        Updates the properties of a specified symbol by replacing existing template properties with new values.
        If the property does not exist in the symbol, it is created.

        Args:
            symbol_name (str): The name of the symbol whose properties are to be modified.
            new_properties (dict[str, str]): A dictionary mapping property names to their new values.

        Raises:
            KeyError: If the specified symbol does not exist in the library.
        """

        try:
            # note that this is a reference to the symbol in the library, so modifying it modifies the library
            symbol_sexp = self._symbols[symbol_name]
        except KeyError as e:
            raise KeyError(f"Symbol {symbol_name} not found in library.") from e

        # copy it because I will be modifying it
        new_properties_copy = new_properties.copy()

        # Find the properties section
        default_position_and_text_effects = None
        for item in symbol_sexp:
            if isinstance(item, list) and len(item) > 0 and item[0] == Symbol("property"):
                # Update existing property with the same name
                property_name = str(item[1])
                if property_name == "Description":
                    # pull the addition property information (id, postion, text effects) for adding properties later
                    default_position_and_text_effects = item[3:]
                if property_name in new_properties_copy:
                    # replace the properties value. Because lists are mutable, this modifies the symbol in place
                    item[2] = new_properties_copy[property_name]

                    # keep track of which properties remain to be added
                    del new_properties_copy[property_name]

        assert default_position_and_text_effects, "Failed to find Description property to copy position and text effects from."

        # Add any new properties that were not found in the existing properties
        for prop_name, prop_value in new_properties_copy.items():
            # Create a new property entry using the default position and text effects
            new_property = [Symbol("property"), prop_name, prop_value] + default_position_and_text_effects
            symbol_sexp.append(new_property)

        # write the modified symbol back to the library
        self._symbols[symbol_name] = symbol_sexp

    def modify_symbol_sections(self, symbol_sexp: list, sections: list[str], mode: str) -> list:
        """
        Removes or keeps specified sections from a symbol's S-expression.

        Args:
            symbol_sexp (list): The S-expression of the symbol. As a list, this is edited in place.
            sections (list[str]): Section names to remove or keep.
            mode (str): "remove" to remove sections, "keep" to keep only these sections.

        Raises:
            ValueError: If mode is not "remove" or "keep".

        """
        if mode not in ["remove", "keep"]:
            raise ValueError("Mode must be 'remove' or 'keep'.")
        if any(sec not in _valid_kicad_symbol_sections for sec in sections):
            raise ValueError(f"Sections must be one of {_valid_kicad_symbol_sections}.")

        modified_sexp = []
        for item in symbol_sexp:
            if (
                isinstance(item, list)
                and len(item) > 0
                and (mode == "remove" and str(item[0]) in sections or mode == "keep" and str(item[0]) not in sections)
            ):
                continue
            modified_sexp.append(deepcopy(item))
        return modified_sexp

    def derive_symbol_from(self, new_symbol_name: str, template_symbol_name: str, properties: dict[str, str]) -> None:
        """
        Create a new symbol derived from a template symbol with specified properties.
        The property must already exist in the template symbol, otherwise it is ignored.

        Args:
            new_symbol_name (str): The name of the new symbol to create.
            template_symbol_name (str): The name of the template symbol to derive from.
            properties (dict[str, str]): A dictionary of properties to set on the new symbol.

        Raises:
            KeyError: If the template symbol does not exist in the library.
            ValueError: If the new symbol name already exists in the library.
            AssertionError: If the template symbol is itself derived from another symbol.
        """
        if new_symbol_name in self._symbols:
            raise KeyError(f"Symbol {new_symbol_name} already exists in library.")
        if template_symbol_name not in self._symbols:
            raise KeyError(f"Template symbol {template_symbol_name} not found in library.")
        assert self.symbol_derived_from(template_symbol_name) is None, "Template symbol cannot be derived from another derived symbol."

        # Start with a deep copy of the template symbol's S-expression
        new_symbol_sexp = self.get_symbol(template_symbol_name)

        # Remove everything except the properties
        new_symbol_sexp = self.modify_symbol_sections(new_symbol_sexp, ["property"], mode="keep")

        # I need to add the `extends` section to indicate the template
        new_symbol_sexp.insert(0, [Symbol("extends"), template_symbol_name])

        # place the symbol in the library
        self._symbols[new_symbol_name] = new_symbol_sexp

        # Update properties
        self.modify_properties(new_symbol_name, properties)

    def get_symbol_names(self) -> list[str]:
        """
        Returns a list of all symbol names in the library.

        Returns:
            list[str]: A list of symbol names.
        """
        return list(self._symbols.keys())

    def write_library(self, output_path: Path | None = None) -> None:
        """
        Writes the current symbol library to the specified file path.

        Args:
            output_path (Path): The path to write the symbol library file.
        """
        # Compose the full S-expression for the library
        sexp = deepcopy(self._symbol_file_header)
        for symbol_name, symbol_sexp in self._symbols.items():
            sexp.append([Symbol("symbol"), symbol_name] + deepcopy(symbol_sexp))

        # Write to the specified file or overwrite the original file if not specified
        if output_path is None:
            output_path = self.file
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(dumps(sexp))
