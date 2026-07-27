# Bob the Builder Wii Mesh Importer
This Blender add-on allows you to import H3M models from the Wii release of Bob the Builder: Festival of Fun.

## Installation
1. Download the latest version of this add-on from the [releases](https://github.com/jmancoder/btb-wii-model-importer/releases) page. Blender 4.2 and newer is supported.
2. In Blender, open *Edit->Preferences->Add-ons*.
3. Expand the dropdown arrow on the top right, click *Install from Disk*, and select the add-on file.

## Usage
1. Extract the Wii release of Bob the Builder: Festival of Fun.
2. In Blender, click *File->Import->H3M Model (.H3M)*.
3. Select a model file from *DATA\files\Models* and click *Import H3M*.

## TODO
- Fix primitive reading on skinned meshes
- Read remaining Mesh and SkinMesh fields
- Import animation files

## Acknowledgements
lzss3.py was copied from the following respository with the MIT license appended to the top of the file: https://github.com/magical/nlzss.
