from __future__ import annotations
import bpy
from io import BytesIO

from bpy.types import Context, Object
from mathutils import Matrix

from .lzss3 import decompress_bytes
from .binary_reader import BinaryReader


class H3MPrimitiveGroup:
    def __init__(self, prim_type: int, prim_count: int,
                 prim_flags: int) -> None:
        self.prim_type = prim_type
        self.prim_count = prim_count
        self.prim_flags = prim_flags
        
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

    def load_data(self, reader: H3MReader) -> None:
        for _ in range(self.prim_count):
            if self.prim_flags & 1:
                self.position_indices.append(reader.read_uint16())
            if self.prim_flags & 2:
                self.normal_indices.append(reader.read_uint16())
            if self.prim_flags & 4:
                self.color_indices.append(reader.read_uint16())
            if self.prim_flags & 8:
                self.indices_3.append(reader.read_uint16())
            if self.prim_flags & 16:
                self.uv_indices.append(reader.read_uint16())
            if self.prim_flags & 32:
                self.indices_5.append(reader.read_uint16())
            if self.prim_flags & 64:
                self.indices_6.append(reader.read_uint16())
            if self.prim_flags & 128:
                self.indices_7.append(reader.read_uint16())
            if self.prim_flags & 256:
                self.indices_8.append(reader.read_uint16())
            if self.prim_flags & 512:
                self.indices_9.append(reader.read_uint16())
            if self.prim_flags & 1024:
                self.indices_10.append(reader.read_uint16())
            if self.prim_flags & 2048:
                self.indices_11.append(reader.read_uint16())


class H3MBone:
    def __init__(self) -> None:
        self.parent_id: int
        self.transform: Matrix

    def load_data(self, reader: H3MReader) -> None:
        self.parent_id = reader.read_int16()
        self.transform = Matrix.LocRotScale(
            reader.read_vec3f(),
            reader.read_quaternion(),
            reader.read_vec3f()
        )

class H3MObject:
    def __init__(self) -> None:
        self.name: str
        self.flag_0: int
        self.flag_1: int
        self.transform: Matrix

    def load_data(self, reader: H3MReader) -> None:
        # Read shared object fields
        self.name = reader.read_text()
        self.flag_0 = reader.read_uint16()
        self.flag_1 = reader.read_uint16()
        self.transform = Matrix.LocRotScale(
            reader.read_vec3f(),
            reader.read_quaternion(),
            reader.read_vec3f()
        )


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

        self.main_prim_group: H3MPrimitiveGroup
        self.prim_groups: list[H3MPrimitiveGroup] = []

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

        # Read nodes and primitive groups
        node_count = reader.read_uint16()
        for _ in range(node_count):
            node_id = reader.read_uint16()
            prim_group_count = reader.read_uint16()
            for _ in range(prim_group_count):
                prim_type = reader.read_uint16()
                prim_count = reader.read_uint32()
                prim_flags = reader.read_uint32()
                prim_group = H3MPrimitiveGroup(prim_type,
                                               prim_count, prim_flags)
                prim_group.load_data(reader)
                self.prim_groups.append(prim_group)

        self.main_prim_group = self.prim_groups[-1]

        unk_0 = reader.read_uint16()
        unk_1 = reader.read_uint16()


class H3MSkinMeshObject(H3MMeshObject):
    def __init__(self) -> None:
        super().__init__()

        self.skin_transform: Matrix
        self.bones: list[H3MBone] = []
        self.bone_indices: list[float] = []
        self.bone_weights: list[float] = []

    def load_data(self, reader: H3MReader):
        super().load_data(reader)

        # Read main primitive group
        unk_0 = reader.read_int16()
        tail_prim_count = reader.read_uint16()
        tail_prim_group = H3MPrimitiveGroup(
            self.main_prim_group.prim_type,
            tail_prim_count,
            self.main_prim_group.prim_flags
        )
        tail_prim_group.load_data(reader)
        self.prim_groups.append(tail_prim_group)
        self.main_prim_group = tail_prim_group

        # Read skin data
        self.skin_transform = Matrix.LocRotScale(
            reader.read_vec3f(),
            reader.read_quaternion(),
            reader.read_vec3f()
        )

        bone_count = reader.read_uint16()
        for _ in range(bone_count):
            bone = H3MBone()
            bone.load_data(reader)
            self.bones.append(bone)

        skin_attr_count = reader.read_uint16()
        unks_0 = []
        for _ in range(skin_attr_count):
            unks_0.append(reader.read_int16())
            self.bone_weights.append(reader.read_float())
            self.bone_indices.append(reader.read_int32())
        print("Min, max:", min(unks_0), max(unks_0))

class H3MReader(BinaryReader):
    def __init__(self, unit_scale: float, min_node_length: float) -> None:
        self.unit_scale = unit_scale
        self.min_node_length = min_node_length
        self.objects: list[H3MObject] = []
        self.parent_ids: list[int] = []

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
                    raise ValueError(f"Unknown object type: {obj_type}")

        # Store object parent IDs
        self.parent_ids = [self.read_int16() for _ in range(object_count)]

    def import_h3m(self, context: Context) -> None:
        for obj in self.objects:
            if isinstance(obj, H3MMeshObject):
                is_skinned = type(obj) is H3MSkinMeshObject
                if is_skinned:
                    # Create armature
                    armature = bpy.data.armatures.new(obj.name)
                    armature_obj = bpy.data.objects.new(obj.name, armature)
                    armature_obj.matrix_world = obj.skin_transform * self.unit_scale
                    context.collection.objects.link(armature_obj)

                    # Create bones
                    context.view_layer.objects.active = armature_obj
                    bpy.ops.object.mode_set(mode="EDIT")
                    for i, bone_info in enumerate(obj.bones):
                        bone = armature.edit_bones.new(str(i))
                        bone.tail = (
                            0.0,
                            self.min_node_length / self.unit_scale,
                            0.0
                        )
                        bone.matrix = bone_info.transform
                    # Update bone hierarchy
                    # for i, bone_info in enumerate(obj.bones):
                    #     bone = armature.edit_bones[i]
                    #     bone.parent = armature.edit_bones[bone_info.parent_id]
                    bpy.ops.object.mode_set(mode="OBJECT")

                # Group position indices into triangles
                triangles: list[tuple[int, int, int]] = []
                for i in range(0, len(obj.main_prim_group.position_indices), 3):
                    a, b, c = obj.main_prim_group.position_indices[i:i+3]
                    triangles.append((a, b, c))

                # Create mesh
                mesh = bpy.data.meshes.new(obj.name)
                mesh.from_pydata(obj.positions, [], triangles)

                # Skin mesh normal and UV indices cannot be imported directly
                if not is_skinned:
                    # Import flipped UVs
                    uv_layer = mesh.uv_layers.new(name=f"UV0")
                    for i, uv_idx in enumerate(obj.main_prim_group.uv_indices):
                        if uv_idx > len(obj.uvs):
                            print(f"Warning: UV index {i} exceeded buffer length")
                            break
                        uv = obj.uvs[uv_idx]
                        uv_layer.data[i].uv = (uv[0], 1.0 - uv[1])

                    # Import normals
                    loop_normals: list[tuple[float, float, float]] = []
                    for i, normal_idx in enumerate(obj.main_prim_group.normal_indices):
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

                mesh_obj = bpy.data.objects.new(obj.name, mesh)
                context.collection.objects.link(mesh_obj)
                mesh_obj.matrix_world = obj.transform

                if is_skinned:
                    # Parent to armature and add armature modifier
                    mesh_obj.parent = armature_obj
                    modifier = mesh_obj.modifiers.new("Armature", 'ARMATURE')
                    modifier.object = armature_obj
                else:
                    mesh_obj.matrix_world *= self.unit_scale
            else:
                # Create empty objects for non-mesh types
                dummy_obj = bpy.data.objects.new(obj.name, None)
                dummy_obj.empty_display_size = 0.1 / self.unit_scale
                dummy_obj.matrix_world = obj.transform * self.unit_scale
                context.collection.objects.link(dummy_obj)
