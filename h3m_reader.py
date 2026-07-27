from __future__ import annotations
import bpy
from io import BytesIO
import math

from bpy.types import Context
from mathutils import Quaternion, Matrix

from .lzss3 import decompress_bytes
from .binary_reader import BinaryReader


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
        self.attrs_3: list[float] = []
        self.uvs: list[tuple[float, float]] = []
        self.attrs_5: list[tuple[float, float]] = []
        self.attrs_6: list[tuple[float, float]] = []
        self.attrs_7: list[tuple[float, float]] = []
        self.attrs_8: list[tuple[float, float]] = []
        self.attrs_9: list[tuple[float, float]] = []
        self.attrs_10: list[tuple[float, float]] = []
        self.attrs_11: list[tuple[float, float]] = []

        self.position_indices: list[int] = []
        self.normal_indices: list[int] = []
        self.color_indices: list[int] = []
        self.indices_3: list[int] = []
        self.uv_indices: list[int] = []
        self.indices_5: list[int] = []
        self.indices_6: list[int] = []
        self.indices_7: list[int] = []
        self.indices_8: list[int] = []
        self.indices_9: list[int] = []
        self.indices_10: list[int] = []
        self.indices_11: list[int] = []

        self.triangles: list[tuple[int, int, int]] = []

    def load_data(self, reader: H3MReader):
        super().load_data(reader)

        # Read vertex attribute buffers
        self.positions = [
            reader.read_vec3f()
            for _ in range(reader.read_uint16())
        ]
        self.normals = [
            reader.read_vec3f()
            for _ in range(reader.read_uint16())
        ]
        self.colors = [
            reader.read_rgba()
            for _ in range(reader.read_uint16())
        ]
        self.attrs_3 = [
            reader.read_float()
            for _ in range(reader.read_uint16())
        ]
        self.uvs = [
            reader.read_vec2f()
            for _ in range(reader.read_uint16())
        ]
        self.attrs_5 = [
            reader.read_vec2f()
            for _ in range(reader.read_uint16())
        ]
        self.attrs_6 = [
            reader.read_vec2f()
            for _ in range(reader.read_uint16())
        ]
        self.attrs_7 = [
            reader.read_vec2f()
            for _ in range(reader.read_uint16())
        ]
        self.attrs_8 = [
            reader.read_vec2f()
            for _ in range(reader.read_uint16())
        ]
        self.attrs_9 = [
            reader.read_vec2f()
            for _ in range(reader.read_uint16())
        ]
        self.attrs_10 = [
            reader.read_vec2f()
            for _ in range(reader.read_uint16())
        ]
        self.attrs_11 = [
            reader.read_vec2f()
            for _ in range(reader.read_uint16())
        ]

        # Read primitives
        node_count = reader.read_uint16()
        unk_0 = reader.read_uint16()
        prim_group_count = reader.read_uint16()
        print(node_count, unk_0, prim_group_count)

        prim_type = reader.read_uint16()
        prim_count = reader.read_uint32()
        prim_flags = reader.read_uint32()
        print(prim_type, prim_count, prim_flags)

        # vert_attr_count = 0
        # for i in range(12):
        #     if prim_flags & (1 << i):
        #         vert_attr_count += 1

        for _ in range(prim_count):
            if prim_flags & 1:
                self.position_indices.append(reader.read_uint16())
            if prim_flags & 2:
                self.normal_indices.append(reader.read_uint16())
            if prim_flags & 4:
                self.color_indices.append(reader.read_uint16())
            if prim_flags & 8:
                self.indices_3.append(reader.read_uint16())
            if prim_flags & 16:
                self.uv_indices.append(reader.read_uint16())
            if prim_flags & 32:
                self.indices_5.append(reader.read_uint16())
            if prim_flags & 64:
                self.indices_6.append(reader.read_uint16())
            if prim_flags & 128:
                self.indices_7.append(reader.read_uint16())
            if prim_flags & 256:
                self.indices_8.append(reader.read_uint16())
            if prim_flags & 512:
                self.indices_9.append(reader.read_uint16())
            if prim_flags & 1024:
                self.indices_10.append(reader.read_uint16())
            if prim_flags & 2048:
                self.indices_11.append(reader.read_uint16())

        # Group position indices into triangles
        for i in range(0, len(self.position_indices), 3):
            a, b, c = self.position_indices[i:i+3]
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

    def load_h3m(self, z_data: bytes, name: str) -> None:
        # Decompress as LZ11 data when signature is present
        if z_data[:4].decode("ascii", errors="ignore") == "H3DZ":
            data = decompress_bytes(z_data[4:])
        else:
            data = z_data
        self.data_size = len(data)
        if self.data_size == 0:
            raise ValueError(
                f"Decompressed data is empty")
        self.bs = BytesIO(data)

        # Read header
        version = self.read_uint16()
        if version != 200:
            raise ValueError(
                f"Unknown file version {version}")
        material_count = self.read_uint16()
        object_count = self.read_uint16()
        anim_count = self.read_uint16()
        self.read_float()
        self.read_float()

        # Read materials
        for _ in range(material_count):
            self.read_vec3f()
            self.read_vec3f()
            self.read_vec3f()
            self.read_vec3f()
            self.read_float()
            self.read_float()
            texture_count = self.read_uint16()

            # Read textures
            for _ in range(texture_count):
                tex_name = self.read_text()
                if not tex_name:
                    # Skip internal texture
                    tex_size = self.read_uint32()
                    self.bs.seek(tex_size, 1)
                self.read_uint16()

            self.read_uint16()

        # Read objects
        for _ in range(object_count):
            obj_type = self.read_uint16()
            match obj_type:
                case 1:
                    obj = H3MMeshObject()
                    obj.load_data(self)
                    self.objects.append(obj)
                    # Remove tihis break when Mesh objects are fully parsed
                    break
                case 2:
                    obj = H3MSkinMeshObject()
                    obj.load_data(self)
                    self.objects.append(obj)
                    # Remove this break when SkinMesh objects are fully parsed
                    break
                case 3:
                    obj = H3MBoneObject()
                    obj.load_data(self)
                    self.objects.append(obj)
                case 5:
                    obj = H3MDummyObject()
                    obj.load_data(self)
                    self.objects.append(obj)
                case _:
                    raise ValueError(f"Unknown object type: {obj_type}")

        # Print basic properties of each object
        for obj in self.objects:
            print(obj.name, type(obj).__name__, obj.flags_0, obj.flags_1)
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
                uv_layer = mesh.uv_layers.new(name=f"UV0")
                for i, uv_idx in enumerate(obj.uv_indices):
                    if uv_idx > len(obj.uvs):
                        print(f"Warning: UV index {i} exceeded buffer length")
                        break
                    uv = obj.uvs[uv_idx]
                    uv_layer.data[i].uv = (uv[0], 1.0 - uv[1])

                # Import normals
                # This causes an exception access violation on skinned meshes
                if not is_skinned:
                    loop_normals: list[tuple[float, float, float]] = []
                    for i, normal_idx in enumerate(obj.normal_indices):
                        if normal_idx > len(obj.normals):
                            print(f"Warning: Normal index {i} exceeded buffer length")
                            break
                        x, y, z = obj.normals[normal_idx]
                        loop_normals.append((-x, -y, -z))
                    else:
                        if len(loop_normals) == len(mesh.loops):
                            mesh.normals_split_custom_set(loop_normals)
                        else:
                            print("Warning: Normal count does not match loop count")

                mesh.validate()
                mesh.update()

                mesh_obj = bpy.data.objects.new("Mesh", mesh)
                context.collection.objects.link(mesh_obj)

                if is_skinned:
                    # Parent to armature and add armature modifier
                    mesh_obj.parent = armature_obj
                    modifier = mesh_obj.modifiers.new("Armature", 'ARMATURE')
                    modifier.object = armature_obj

                    # Correct armature scale and rotation
                    armature_obj.rotation_euler = (math.radians(90.0), 0.0, 0.0)
                    armature_obj.scale = (0.01, 0.01, 0.01)
                else:
                    # Correct mesh scale and rotation
                    mesh_obj.rotation_euler = (math.radians(90.0), 0.0, 0.0)
                    mesh_obj.scale = (0.01, 0.01, 0.01)
