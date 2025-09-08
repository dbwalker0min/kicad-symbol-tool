from pathlib import Path

from sexpdata import Symbol, dumps, load  # type: ignore

from kicad_symbol_tool.symbol_file import KiCadSymbolLibrary


def test_get_version_number() -> None:
    sexpr = [Symbol("kicad_symbol_lib"), [Symbol("version"), 20241209]]
    version = KiCadSymbolLibrary.get_kicad_version(sexpr)
    assert version == 20241209


def test_symbol_derived_from() -> None:
    sexpr = [Symbol("extends"), "~Template"]
    assert KiCadSymbolLibrary.symbol_derived_from(sexpr) == "~Template"


def test_init() -> None:
    lib = KiCadSymbolLibrary(Path(__file__).parent / "data" / "My_Resistor-0805.kicad_sym")
    raise AssertionError(lib)  # for debugging purposes
