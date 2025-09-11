# KiCad Symbol Tool

`kicad-symbol-tool` is a command-line tool that assists with managing KiCad part libraries.

## Introduction

KiCad is an Electrical CAD tool that is used to design schematics and PCBs. A well-designed part will have:

- A proper graphical representation of the part and its pin numbers
- A link to the datasheet
- A link to the proper footprint
- Information on sourcing the part. This can be as basic as a manufacturer and manufacturer part number. Additionally, distributor information could be provided.

Unfortunately, it is laborious to define all this information in KiCad itself, as each part must be created and edited one at a time. This tool aims to remedy this. It is run by running the command:

```powershell
kicad-lilbrary-manager <name of .kicad_sym library file>
```

It then performs the following:

- If the library doesn't exist, it throws an exception.
- If the library format is before 6.0, it throws an exception.
- If the file `<root name of .kicad_sym file>.xlsx` does not exist, it will be created, and the utility will exit.
- If it does exist, then if the `xlsx` file is newer than the `kicad_sym` file, the changes in the `xlsx` file will be applied to the symbol's properties.

## Template Parts

Each library should contain template parts. These parts will be used to derive new symbols. This is particularly useful for resistors and capacitors. These template parts should contain all of the properties that are desired on the derived parts. Note that while KiCad itself does not copy properties to directly derived parts, this tool explicitly copies the properties to the derived symbols. More than one template can exist in a library. 

Generally, you don't want to instantiate these symbols. By convention, I precede the symbol name with a tilde ('~') and set the description to "Do not use - Template."

## Format of `xlsx` file

The `xlsx` file will contain several tabs, one for each template part. Parts that are not derived will not be listed because it is assumed that the properties would have to be manually edited anyway. The data consists of one row for each part.

The following columns will always be present in the spreadsheet:

| Name           | Description                                                  |
| -------------- | ------------------------------------------------------------ |
| Status         | The status of updating the part from the spreadsheet. This can be "OK" (no error), "TemplateError" (the specified template doesn't exist), "PropWarning" (the property does not exist in the template and was ignored). |
| Name           | The name of the symbol                                       |
| Reference      | Symbol reference designator letter(s)                        |
| Value          | The value property (required)                                |
| Footprint      | Symbol footprint (required)                                  |
| Datasheet      | Link to the datasheet                                        |
| ki_keywords    | Keywords used to search for parts                            |
| ki_description | Description of the part                                      |
| ki_fp_filters  | Filters used to select footprints                            |

Additional columns are the additional properties on the template part.

## Installation Instructions

The tool can be run without installation using the Astral UV package manager.

Alternatively, the program is on PyPi under the name `kicad-symbol-tool` so it can be installed with pip or pipx.

## Example Usage

### Astral UV

If `uv` is installed, the program can be run by:

```
uvx kicad-symbol-tool <name of .kicad_sym file>
```

### Pip or Pipx

```
kicad-symbol-tool <name of .kicad_sym file>
```

## Supported KiCad Versions

The dependency is based on the symbol library file format. It has not changed since version 6.0, so it will work for any version greater than or equal to 6.0.

## Contributing Guidelines

To be written...

## License

The license is MIT.

## Limitations and Future Work

To be written.

## Implementation Notes

- The program will be written in Python.
- Astral `uv` will be used as the package manager.
- Packages used:
  - `Typer` to implement the command-line program.
  - `sexpdata` will be used to parse the library file.
  - Unit tests will use `pytest`