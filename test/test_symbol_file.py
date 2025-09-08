from sexpdata import load, dumps  # type: ignore
from kicad_symbol_tool.symbol_file import read_symbol_file, write_symbols_to_xlsx, update_sexp_with_symbols
from pprint import pprint

def test_read_symbol_file_simple():
    with open(r"test\data\My_Resistor-0805.kicad_sym", "r", encoding="utf-8") as f:
        expected = {'~Template': {'Reference': 'R', 'Value': '~Template', 'Footprint': 'Resistor_SMD:R_0805_2012Metric', 'Datasheet': '~', 'Description': 'Resistor, small US symbol', 'Tolerance': '1%', 'Package': '0805', 'ki_keywords': 'r resistor', 'ki_fp_filters': 'R_*'}, '1.5k': {'Reference': 'R', 'Value': '1.5k', 'Footprint': 'Resistor_SMD:R_0805_2012Metric', 'Datasheet': 'https://jlcpcb.com/api/file/downloadByFileSystemAccessId/8579706440690286592', 'Description': '-55℃~+155℃ 1.5kΩ 125mW 150V Thick Film Resistor ±1% ±100ppm/℃ 0805 Chip Resistor - Surface Mount ROHS', 'Package': '0805', 'JLCPCB': 'C4310', 'ki_keywords': 'r resistor basic', 'ki_fp_filters': 'R_*', 'extends': '~Template'}, '20k': {'Reference': 'R', 'Value': '20k', 'Footprint': 'Resistor_SMD:R_0805_2012Metric', 'Datasheet': 'https://jlcpcb.com/api/file/downloadByFileSystemAccessId/8579706440690286592', 'Description': '-55℃~+155℃ 125mW 150V 20kΩ Thick Film Resistor ±1% ±100ppm/℃ 0805 Chip Resistor - Surface Mount ROHS', 'Package': '0805', 'JLCPCB': 'C4328', 'ki_keywords': 'r resistor basic', 'ki_fp_filters': 'R_*', 'extends': '~Template'}}
        result = read_symbol_file(f)

        pprint(result)
        assert result==expected
        assert False

def test_write_xlsx_file():
    with open(r"test\data\My_Resistor-0805.kicad_sym", "r", encoding="utf-8") as f:
        symbols = read_symbol_file(f)
        write_symbols_to_xlsx(symbols, r"test\data\My_Resistor-0805.xlsx")
        assert True

def test_update_sexp():
    with open(r"test\data\My_Resistor-0805.kicad_sym", "r", encoding="utf-8") as f:
        content = load(f)
        pprint(content)
        assert False
        f.seek(0)
        symbols = read_symbol_file(f)

        # make some changes
        symbols['1.5k']['Value'] = '1.6k'
        symbols['1.5k']['new_name'] = '1k6'
        symbols['20k']['Value'] = '21k'
        symbols['20k']['new_name'] = '21k'
        updated_sexp = update_sexp_with_symbols(content, symbols)
        pprint(updated_sexp)
        with open(r"test\data\My_Resistor-0805_updated.kicad_sym", "w", encoding="utf-8") as f:
            f.write(dumps(updated_sexp))

        assert True