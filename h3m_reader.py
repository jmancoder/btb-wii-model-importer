from __future__ import annotations
import bpy
from io import BufferedReader

from bpy.types import Context, Object
from mathutils import Matrix, Quaternion

from .lzss3 import decompress_bytes
from .binary_reader import BinaryReader


class H3MPrimitiveGroup:
    def __init__(self, prim_type: int, prim_count: int, prim_flags: int) -> None:
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

    def load_data(self, bs: BinaryReader) -> None:
        for _ in range(self.prim_count):
            if self.prim_flags & 1:
                self.position_indices.append(bs.read_uint16())
            if self.prim_flags & 2:
                self.normal_indices.append(bs.read_uint16())
            if self.prim_flags & 4:
                self.color_indices.append(bs.read_uint16())
            if self.prim_flags & 8:
                self.indices_3.append(bs.read_uint16())
            if self.prim_flags & 16:
                self.uv_indices.append(bs.read_uint16())
            if self.prim_flags & 32:
                self.indices_5.append(bs.read_uint16())
            if self.prim_flags & 64:
                self.indices_6.append(bs.read_uint16())
            if self.prim_flags & 128:
                self.indices_7.append(bs.read_uint16())
            if self.prim_flags & 256:
                self.indices_8.append(bs.read_uint16())
            if self.prim_flags & 512:
                self.indices_9.append(bs.read_uint16())
            if self.prim_flags & 1024:
                self.indices_10.append(bs.read_uint16())
            if self.prim_flags & 2048:
                self.indices_11.append(bs.read_uint16())


class H3MBone:
    def __init__(self) -> None:
        self.object_id: int
        self.transform: Matrix

    def load_data(self, bs: BinaryReader) -> None:
        self.object_id = bs.read_int16()
        self.transform = Matrix.LocRotScale(
            bs.read_vec3f(), Quaternion(bs.read_vec4f()), bs.read_vec3f()
        )


class H3MObject:
    def __init__(self) -> None:
        self.name: str
        self.flag_0: int
        self.flag_1: int
        self.transform: Matrix
        self.parent_id: int = -1

    def load_data(self, bs: BinaryReader) -> None:
        # Read shared object fields
        self.name = bs.read_string()
        self.flag_0 = bs.read_uint16()
        self.flag_1 = bs.read_uint16()
        self.transform = Matrix.LocRotScale(
            bs.read_vec3f(), Quaternion(bs.read_vec4f()), bs.read_vec3f()
        )


class H3MDummyObject(H3MObject):
    def __init__(self) -> None:
        super().__init__()

    def load_data(self, bs: BinaryReader) -> None:
        super().load_data(bs)


class H3MBoneObject(H3MObject):
    def __init__(self) -> None:
        super().__init__()

    def load_data(self, bs: BinaryReader) -> None:
        super().load_data(bs)


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

    def load_data(self, bs: BinaryReader):
        super().load_data(bs)

        # Read vertex attribute buffers
        self.positions = [bs.read_vec3f() for _ in range(bs.read_uint16())]
        self.normals = [bs.read_vec3f() for _ in range(bs.read_uint16())]
        self.colors = [bs.read_vec4B() for _ in range(bs.read_uint16())]
        self.attrs_3 = [bs.read_float() for _ in range(bs.read_uint16())]
        self.uvs = [bs.read_vec2f() for _ in range(bs.read_uint16())]
        self.attrs_5 = [bs.read_vec2f() for _ in range(bs.read_uint16())]
        self.attrs_6 = [bs.read_vec2f() for _ in range(bs.read_uint16())]
        self.attrs_7 = [bs.read_vec2f() for _ in range(bs.read_uint16())]
        self.attrs_8 = [bs.read_vec2f() for _ in range(bs.read_uint16())]
        self.attrs_9 = [bs.read_vec2f() for _ in range(bs.read_uint16())]
        self.attrs_10 = [bs.read_vec2f() for _ in range(bs.read_uint16())]
        self.attrs_11 = [bs.read_vec2f() for _ in range(bs.read_uint16())]

        # Read nodes and primitive groups
        node_count = bs.read_uint16()
        for _ in range(node_count):
            node_id = bs.read_uint16()
            prim_group_count = bs.read_uint16()
            for _ in range(prim_group_count):
                prim_type = bs.read_uint16()
                prim_count = bs.read_uint32()
                prim_flags = bs.read_uint32()
                prim_group = H3MPrimitiveGroup(prim_type, prim_count, prim_flags)
                prim_group.load_data(bs)
                self.prim_groups.append(prim_group)

        self.main_prim_group = self.prim_groups[-1]

        unk_0 = bs.read_uint16()
        unk_1 = bs.read_uint16()


class H3MSkinMeshObject(H3MMeshObject):
    def __init__(self) -> None:
        super().__init__()

        self.skin_transform: Matrix
        self.bones: list[H3MBone] = []
        self.bone_indices: list[float] = []
        self.bone_weights: list[float] = []

    def load_data(self, bs: BinaryReader):
        super().load_data(bs)

        # Read main primitive group
        unk_0 = bs.read_int16()
        tail_prim_count = bs.read_uint16()
        tail_prim_group = H3MPrimitiveGroup(
            self.main_prim_group.prim_type,
            tail_prim_count,
            self.main_prim_group.prim_flags,
        )
        tail_prim_group.load_data(bs)
        self.prim_groups.append(tail_prim_group)
        self.main_prim_group = tail_prim_group

        # Read skin data
        self.skin_transform = Matrix.LocRotScale(
            bs.read_vec3f(), Quaternion(bs.read_vec4f()), bs.read_vec3f()
        )

        bone_count = bs.read_uint16()
        for _ in range(bone_count):
            bone = H3MBone()
            bone.load_data(bs)
            self.bones.append(bone)

        skin_attr_count = bs.read_uint16()
        for _ in range(skin_attr_count):
            bs.read_int16()
            self.bone_weights.append(bs.read_float())
            self.bone_indices.append(bs.read_int32())


def read_h3m(f: BufferedReader) -> list[H3MObject]:
    # Decompress as LZ11 data when signature is present
    bs = BinaryReader(f.read(), big_endian=True)
    if bs.read(4).decode("ascii", errors="ignore") == "H3DZ":
        bs = BinaryReader(decompress_bytes(bs.read()), big_endian=True)
    if bs.getbuffer().nbytes == 0:
        raise ValueError(f"Decompressed data is empty")

    # Read header
    version = bs.read_uint16()
    if version != 200:
        raise ValueError(f"Unknown file version {version}")
    material_count = bs.read_uint16()
    object_count = bs.read_uint16()
    anim_count = bs.read_uint16()
    bs.read_float()
    bs.read_float()

    # Read materials
    for _ in range(material_count):
        bs.read_vec3f()
        bs.read_vec3f()
        bs.read_vec3f()
        bs.read_vec3f()
        bs.read_float()
        bs.read_float()
        texture_count = bs.read_uint16()

        # Read textures
        for _ in range(texture_count):
            tex_name = bs.read_string()
            if not tex_name:
                # Skip internal texture
                tex_size = bs.read_uint32()
                bs.seek(tex_size, 1)
            bs.read_uint16()
        bs.read_uint16()

    # Read objects
    objects: list[H3MObject] = []
    for _ in range(object_count):
        obj_type = bs.read_uint16()
        match obj_type:
            case 1:
                obj = H3MMeshObject()
                obj.load_data(bs)
                objects.append(obj)
            case 2:
                obj = H3MSkinMeshObject()
                obj.load_data(bs)
                objects.append(obj)
            case 3:
                obj = H3MBoneObject()
                obj.load_data(bs)
                objects.append(obj)
            case 5:
                obj = H3MDummyObject()
                obj.load_data(bs)
                objects.append(obj)
            case _:
                raise ValueError(f"Unknown object type: {obj_type}")

    # Store object parent IDs
    for obj in objects:
        obj.parent_id = bs.read_int16()
    return objects


def import_h3m(
    context: Context, objects: list[H3MObject], name: str, default_bone_len: float
) -> None:
    blender_objects: list[Object] = []
    for obj in objects:
        if isinstance(obj, H3MMeshObject):
            is_skinned = type(obj) is H3MSkinMeshObject
            if is_skinned:
                # Create armature object
                armature = bpy.data.armatures.new(obj.name)
                armature_obj = bpy.data.objects.new(obj.name, armature)
                context.collection.objects.link(armature_obj)
                if obj.parent_id > -1:
                    armature_obj.parent = blender_objects[obj.parent_id]
                blender_objects.append(armature_obj)
                armature_obj.matrix_local = obj.transform
                if obj.parent_id < 0:
                    armature_obj.matrix_world *= 0.01

                context.view_layer.objects.active = armature_obj
                bpy.ops.object.mode_set(mode="EDIT")

                # Create bones
                for i, bone_info in enumerate(obj.bones):
                    bone_obj = blender_objects[bone_info.object_id]
                    bone = armature.edit_bones.new(bone_obj.name)
                    bone.tail = (0.0, default_bone_len * 100.0, 0.0)
                    bone.matrix = bone_info.transform

                # Make bone hierarchy match bone object hierarchy
                for i, bone_info in enumerate(obj.bones):
                    bone_obj = blender_objects[bone_info.object_id]
                    parent_bone_obj = bone_obj.parent
                    if parent_bone_obj:
                        bone = armature.edit_bones[i]
                        bone.parent = armature.edit_bones.get(parent_bone_obj.name)

                bpy.ops.object.mode_set(mode="OBJECT")

            # Group position indices into triangles
            triangles: list[tuple[int, int, int]] = []
            for i in range(0, len(obj.main_prim_group.position_indices), 3):
                a, b, c = obj.main_prim_group.position_indices[i : i + 3]
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

            # Create mesh object
            mesh_obj = bpy.data.objects.new(obj.name, mesh)
            context.collection.objects.link(mesh_obj)
            if obj.parent_id > -1:
                mesh_obj.parent = blender_objects[obj.parent_id]
            blender_objects.append(mesh_obj)
            mesh_obj.matrix_local = obj.transform
            if obj.parent_id < 0:
                mesh_obj.matrix_world *= 0.01

            if is_skinned:
                # Parent to armature and add armature modifier
                mesh_obj.parent = armature_obj
                modifier = mesh_obj.modifiers.new("Armature", "ARMATURE")
                modifier.object = armature_obj

        else:
            # Create empty objects for non-mesh types
            dummy_obj = bpy.data.objects.new(obj.name, None)
            dummy_obj.empty_display_size = 0.1
            context.collection.objects.link(dummy_obj)
            if obj.parent_id > -1:
                dummy_obj.parent = blender_objects[obj.parent_id]
            blender_objects.append(dummy_obj)
            dummy_obj.matrix_local = obj.transform
            if obj.parent_id < 0:
                dummy_obj.matrix_world *= 0.01
