from __future__ import annotations
import bpy
from io import BytesIO
import struct

from bpy.types import Context
from mathutils import Quaternion, Matrix

from .binary_reader import BinaryReader
from .lzss3 import decompress_bytes


class H3MObject:
    def __init__(self) -> None:
        self.name: str
        self.flags_0: int
        self.flags_1: int
        self.location: tuple[float, float, float]
        self.rotation: Quaternion
        self.scale: tuple[float, float, float]

    def load_data(self, reader: H3MReader) -> None:
        # Read shared object fields
        self.name = reader.read_text()
        self.flags_0 = reader.read_uint16()
        self.flags_1 = reader.read_uint16()
        self.location = reader.read_vec3f()
        self.rotation = reader.read_rotation()
        self.scale = reader.read_vec3f()


class H3MDummyObject(H3MObject):
    def __init__(self) -> None:
        super().__init__()

    def load_data(self, reader: H3MReader) -> None:
        super().load_data(reader)


class H3MBoneObject(H3MObject):
    def __init__(self) -> None:
        super().__init__()

    def load_data(self, reader: H3MReader) -> None:
        super().load_data(reader)


class H3MMeshObject(H3MObject):
    def __init__(self) -> None:
        super().__init__()

        self.positions: list[tuple[float, float, float]] = []
        self.normals: list[tuple[float, float, float]] = []
        self.colors: list[tuple[float, float, float, float]] = []
        self.unk_attrs_0: list[tuple[float, float]] = []
        self.uvs: list[tuple[float, float]] = []
        self.unk_attrs_1: list[tuple[float, float]] = []
        self.triangles: list[tuple[int, int, int]] = []

        self.color_indices: list[int] = []
        self.uv_indices: list[int] = []
        self.position_indices: list[int] = []
        self.normal_indices: list[int] = []

    def load_data(self, reader: H3MReader):
        super().load_data(reader)

        # Read vertex buffers
        position_count = reader.read_uint16()
        self.positions = [reader.read_vec3f() for _ in range(position_count)]
        normal_count = reader.read_uint16()
        self.normals = [reader.read_vec3f() for _ in range(normal_count)]
        color_count = reader.read_uint16()
        self.colors = [reader.read_rgba() for _ in range(color_count)]
        unk_attr_count_0 = reader.read_uint16()
        self.unk_attrs_0 = [reader.read_vec2f() for _ in range(unk_attr_count_0)]
        uv_count = reader.read_uint16()
        self.uvs = [reader.read_vec2f() for _ in range(uv_count)]
        unk_attr_count_1 = reader.read_uint16()
        self.unk_attrs_1 = [reader.read_vec2f() for _ in range(unk_attr_count_1)]

        # Skip unknown values for now
        reader.bs.seek(22, 1)

        # Read corner indices
        position_indices: list[int] = []
        prim_count = reader.read_uint16()
        if color_count > 0:
            for _ in range(prim_count):
                self.color_indices.append(reader.read_uint16())
                self.uv_indices.append(reader.read_uint16())
                self.position_indices.append(reader.read_uint16())
                self.normal_indices.append(reader.read_uint16())
        else:
            for _ in range(prim_count):
                self.normal_indices.append(reader.read_uint16())
                self.uv_indices.append(reader.read_uint16())
                position_indices.append(reader.read_uint16())

        # Group position indices into triangles
        for i in range(0, len(position_indices), 3):
            a, b, c = position_indices[i:i+3]
            self.triangles.append((a, b, c))


class H3MSkinMeshObject(H3MMeshObject):
    def __init__(self) -> None:
        super().__init__()

    def load_data(self, reader: H3MReader):
        super().load_data(reader)


class H3MReader(BinaryReader):
    def __init__(self, min_node_length: float) -> None:
        self.min_node_length = min_node_length
        self.objects: list[H3MObject] = []

    def read_text(self) -> str:
        text_len = self.read_uint16()
        if text_len == 0:
            return ""

        # Exclude null end byte
        text = self.bs.read(text_len - 1).decode()
        self.bs.read(1)

        return text

    def load_h3m(self, z_data: bytes) -> None:
        # Decompress LZ1 data if signature is present
        if z_data[:4].decode("ascii", errors="ignore") == "H3DZ":
            data = decompress_bytes(z_data[4:])
        else:
            data = z_data
        self.data_size = len(data)
        self.bs = BytesIO(data)

        # Read header
        version = self.read_uint16()
        material_count = self.read_uint16()
        object_count = self.read_uint16()
        self.read_uint16()
        struct.unpack(">2f", self.bs.read(8))

        # Read materials
        for _ in range(material_count):
            self.read_vec3f()
            self.read_vec3f()
            self.read_vec3f()
            self.read_vec3f()
            struct.unpack(">2f", self.bs.read(8))
            texture_count = self.read_uint16()

            # Read textures
            for _ in range(texture_count):
                tex_name = self.read_text()
                if not tex_name:
                    # Skip internal texture
                    self.read_uint16()
                    tex_size = self.read_uint16()
                    self.bs.seek(tex_size, 1)
                self.read_uint32()

        # Read objects
        for _ in range(object_count):
            obj_type = self.read_uint16()
            match obj_type:
                case 1:
                    obj = H3MMeshObject()
                    obj.load_data(self)
                    self.objects.append(obj)
                case 2:
                    obj = H3MSkinMeshObject()
                    obj.load_data(self)
                    self.objects.append(obj)
                case 3:
                    obj = H3MBoneObject()
                    obj.load_data(self)
                    self.objects.append(obj)
                case 5:
                    obj = H3MDummyObject()
                    obj.load_data(self)
                    self.objects.append(obj)
                case _:
                    raise ValueError("Unknown object type:", obj_type)

        # Log object
        for obj in self.objects:
            print(obj.name, type(obj))
        print()


    def import_h3m(self, context: Context) -> None:
        bone_objects: list[H3MBoneObject] = []

        for obj in self.objects:
            if type(obj) is H3MDummyObject:
                pass

            elif type(obj) is H3MBoneObject:
                bone_objects.append(obj)

            elif isinstance(obj, H3MMeshObject):
                is_skinned = type(obj) is H3MSkinMeshObject
                if is_skinned:
                    # Create armature
                    armature = bpy.data.armatures.new("Armature")
                    armature_obj = bpy.data.objects.new("Armature", armature)
                    context.collection.objects.link(armature_obj)
                    #armature_obj.rotation_euler = (math.radians(90.0), 0.0, 0.0)

                    # Create bones
                    context.view_layer.objects.active = armature_obj
                    bpy.ops.object.mode_set(mode="EDIT")
                    for bone_obj in bone_objects:
                        bone = armature.edit_bones.new(bone_obj.name)
                        bone.tail = (0, 2.0, 0)
                        bone.matrix = Matrix.LocRotScale(
                            bone_obj.location,
                            bone_obj.rotation,
                            bone_obj.scale,
                        )
                    bpy.ops.object.mode_set(mode="OBJECT")

                # Create mesh
                mesh = bpy.data.meshes.new("Mesh")
                mesh.from_pydata(obj.positions, [], obj.triangles)

                # Import flipped UVs
                # uv_layer = mesh.uv_layers.new(name=f"UV0")
                # for i, uv_idx in enumerate(self.uv_indices):
                #     uv = self.uvs[uv_idx]
                #     uv_layer.data[i].uv = (uv[0], 1.0 - uv[1])

                # Import normals
                # loop_normals: list[tuple[float, float, float]] = []
                # for normal_idx in self.normal_indices:
                #     x, y, z = self.normals[normal_idx]
                #     loop_normals.append((-x, -y, -z))
                # mesh.normals_split_custom_set(loop_normals)

                mesh.validate()
                mesh.update()

                mesh_obj = bpy.data.objects.new("Mesh", mesh)
                context.collection.objects.link(mesh_obj)

                if is_skinned:
                    # Parent to armature and add armature modifier
                    mesh_obj.parent = armature_obj
                    modifier = mesh_obj.modifiers.new("Armature", 'ARMATURE')
                    modifier.object = armature_obj
