from pathlib import Path
from pprint import pprint

import pytest
from kicad_symlib_util.symbol_file_class import KiCadSymbolLibrary
from sexpdata import ExpectClosingBracket, Symbol

test_data_dir = Path(__file__).parent / "data"


def test_basic_symbol_file() -> None:
    """Test basic functionality of KiCadSymbolLibrary."""
    properties_1p5k = {
        "Datasheet": "https://jlcpcb.com/api/file/downloadByFileSystemAccessId/8579706440690286592",
        "Description": "-55℃~+155℃ 1.5kΩ 125mW 150V Thick Film Resistor ±1% ±100ppm/℃ 0805 Chip Resistor - Surface Mount ROHS",
        "Footprint": "Resistor_SMD:R_0805_2012Metric",
        "JLCPCB": "C4310",
        "Package": "0805",
        "Reference": "R",
        "Value": "1.5k",
        "ki_fp_filters": "R_*",
        "ki_keywords": "r resistor basic",
    }

    new_part_properties = {
        "Datasheet": "https://jlcpcb.com/api/file/downloadByFileSystemAccessId/8579706440690286592",
        "Description": "-55℃~+155℃ 125mW 150V 200kΩ Thick Film Resistor ±1% ±100ppm/℃ 0805 Chip Resistor - Surface Mount ROHS",
        "Footprint": "Resistor_SMD:R_0805_2012Metric",
        "JLCPCB": "C4328999",
        "Package": "0805",
        "Reference": "R",
        "Value": "200k",
        "ki_fp_filters": "R_*",
        "ki_keywords": "r resistor extended",
    }

    test_file = Path(__file__).parent / "data" / "My_Resistor-0805.kicad_sym"
    sf = KiCadSymbolLibrary(test_file)
    assert sf.symbol_derived_from("1.5k") == "~Template", "1.5k should be derived from ~Template"
    assert sf.symbol_derived_from("20k") == "~Template", "20k should be derived from ~Template"
    assert sf.symbol_derived_from("~Template") is None, "~Template should not be derived from anything"
    assert sf.symbol_derived_from("NonExistent") is None, "NonExistent should not be derived from anything"
    assert sf.get_kicad_version() == 20241209, "KiCad version should be 20241209"
    assert sf.get_symbol_properties("1.5k") == properties_1p5k, "Symbol properties for 1.5k do not match"
    assert sf.get_symbol_properties("NonExistent") is None, "NonExistent should return None for properties"
    assert sf.get_symbol("~Template") is not None, "Symbol S-expression for ~Template should not be None"
    assert sf.get_symbol("NonExistent") is None, "NonExistent should return None for symbol S-expression"
    assert len(sf.get_symbol("1.5k")) == 10, "Symbol S-expression for 1.5k should not be empty"
    x = sf.get_symbol("1.5k")
    del x[3]
    assert len(sf.get_symbol("1.5k")) == 10, "Modifying returned symbol should not affect library"
    sf.delete_symbol("20k")
    assert sf.get_symbol("20k") is None, "20k should have been deleted"
    assert len(sf._symbols) == 2, "There should be 2 symbols left after deletion"
    sf.derive_symbol_from("200k", "~Template", new_part_properties)
    props = sf.get_symbol_properties("200k")
    assert props['Value'] == "200k", "New symbol 200k should have correct Value property"
    assert props['JLCPCB'] == "C4328999", "New symbol 200k should have correct JLCPCB property"
    assert props['ki_keywords'] == "r resistor extended", "New symbol 200k should have correct ki_keywords property"
    assert sf.symbol_derived_from("200k") == "~Template", "200k should be derived from ~Template"
    sf.write_library(test_data_dir / "modified.kicad_sym")
    with pytest.raises(KeyError, match="Symbol NonExistent not found in library."):
        sf.delete_symbol("NonExistent")
    with pytest.raises(KeyError):
        sf.modify_properties("NonExistent", {})
    with pytest.raises(ValueError, match="Mode must be 'remove' or 'keep'."):
        sf.modify_symbol_sections([Symbol("symbol")], ["junk"], mode="error")
    with pytest.raises(ValueError, match="Sections must be one of .*"):
        sf.modify_symbol_sections([Symbol("symbol")], ["junk"], mode="keep")
    with pytest.raises(KeyError, match="Symbol 1.5k already exists in library"):
        # this already exist
        sf.derive_symbol_from("1.5k", "~Template", new_part_properties)
    with pytest.raises(KeyError, match="Template symbol ~asdf not found in library"):
        sf.derive_symbol_from("asdf", "~asdf", new_part_properties)
    with pytest.raises(AssertionError, match="Template symbol cannot be derived from another derived symbol"):
        sf.derive_symbol_from("asdf", "1.5k", new_part_properties)

def test_bad_kicad_version() -> None:
    """Test handling of unsupported KiCad version."""
    test_sexp = KiCadSymbolLibrary._symbol_file_header
    test_sexp[1][1] = 234  # Unsupported version
    with pytest.raises(AssertionError):
        KiCadSymbolLibrary(None, sexp=test_sexp)

def test_invalid_file_bad_first_token() -> None:
    """Test handling of invalid file."""
    invalid_file = test_data_dir / "Invalid.kicad_sym"
    with pytest.raises(AssertionError):
        KiCadSymbolLibrary(invalid_file)

def test_invalid_file_bad_sexpr() -> None:
    """Test handling of invalid file with a malformed sexpr."""
    invalid_file = test_data_dir / "InvalidSexpr.kicad_sym"
    with pytest.raises(ExpectClosingBracket, match="Not enough closing brackets\. .*"):
        KiCadSymbolLibrary(invalid_file)