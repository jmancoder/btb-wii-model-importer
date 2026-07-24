bl_info = {
    "name": "ADDON_NAME",
    "author": "AUTHOR_NAME",
    "description": "",
    "blender": (2, 80, 0),
    "version": (0, 0, 1),
    "location": "File > Import",
    "category": "Import-Export",
}


import bpy

from bpy_extras.io_utils import ImportHelper
from bpy.props import FloatProperty, StringProperty
from bpy.types import Operator, Context
from .h3m_reader import H3MReader


class H3MImporter(Operator, ImportHelper):
    """Load a Bob the Builder Wii H3M model."""
    bl_idname = "import_scene.btb_h3m_model"
    bl_label = "Import H3M"

    filename_ext = ".h3m"

    filter_glob: StringProperty(
        default="*.h3m",
        options={'HIDDEN'},
        maxlen=255,
    )

    min_bone_length: FloatProperty(
        name="Min Bone Length",
        description="Smallest bone length allowed.",
        default=0.01,
    )

    def execute(self, context: Context):
        with open(self.filepath, "rb") as f:
            reader = H3MReader(self.min_bone_length)
            reader.load_h3m(f.read())

        reader.import_h3m(context)

        return {'FINISHED'}


def menu_func_import(self, context):
    self.layout.operator(
        H3MImporter.bl_idname,
        text="H3M Mesh (.H3M)"
    )


def register():
    bpy.utils.register_class(H3MImporter)
    bpy.types.TOPBAR_MT_file_import.append(menu_func_import)


def unregister():
    bpy.utils.unregister_class(H3MImporter)
    bpy.types.TOPBAR_MT_file_import.remove(menu_func_import)


if __name__ == "__main__":
    register()
