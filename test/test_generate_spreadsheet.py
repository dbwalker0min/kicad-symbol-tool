from pathlib import Path

from kicad_symbol_tool.derived_parts_from_spreadsheet import generate_derived_parts_from_spreadsheet, generate_spreadsheet_from_symbol_lib


def test_generate_spreadsheet() -> None:
    """Test generating a spreadsheet from a symbol library."""

    test_file = Path(__file__).parent / "data" / "My_Resistor-0805.kicad_sym"
    output_file = Path(__file__).parent / "data" / "My_Resistor-0805.xlsx"
    generate_spreadsheet_from_symbol_lib(test_file, output_file)
    assert output_file.exists()

def test_spreadsheet_to_symbol_library() -> None:
    """Test generating derived parts from a spreadsheet."""

    test_file = Path(__file__).parent / "data" / "My_Resistor-0805.kicad_sym"
    spreadsheet_file = Path(__file__).parent / "data" / "My_Resistor-0805.xlsx"
    output_file = Path(__file__).parent / "data" / "My_Resistor-0805-out.kicad_sym"

    generate_derived_parts_from_spreadsheet(test_file, spreadsheet_file, output_file)
    assert output_file.exists()