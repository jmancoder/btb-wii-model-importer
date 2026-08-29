from __future__ import annotations
import bpy
from io import BufferedReader

from bpy.types import Context, Object
from mathutils import Matrix, Quaternion
import numpy as np
import numpy.typing as npt

from .lzss3 import decompress_bytes
from .binary_reader import BinaryReader


class H3MPrimitiveGroup:
    def __init__(
        self, prim_type: int, prim_count: int, prim_flags: int, is_extra: bool = False
    ) -> None:
        self.prim_type = prim_type
        self.prim_count = prim_count
        self.prim_flags = prim_flags
        self.is_extra = is_extra

        self.indices: npt.NDArray

    def load_data(self, bs: BinaryReader) -> None:
        dtype_fields = []
        if self.prim_flags & 1:
            dtype_fields.append(("position", ">u2", 1))
        if self.is_extra:
            dtype_fields.append(("extra", ">u2", 1))
        if self.prim_flags & 2:
            dtype_fields.append(("normal", ">u2", 1))
        if self.prim_flags & 4:
            dtype_fields.append(("color", ">u2", 1))
        if self.prim_flags & 8:
            dtype_fields.append(("index_3", ">u2", 1))
        if self.prim_flags & 16:
            dtype_fields.append(("uv", ">u2", 1))
        if self.prim_flags & 32:
            dtype_fields.append(("index_5", ">u2", 1))
        if self.prim_flags & 64:
            dtype_fields.append(("index_6", ">u2", 1))
        if self.prim_flags & 128:
            dtype_fields.append(("index_7", ">u2", 1))
        if self.prim_flags & 256:
            dtype_fields.append(("index_8", ">u2", 1))
        if self.prim_flags & 512:
            dtype_fields.append(("index_9", ">u2", 1))
        if self.prim_flags & 1024:
            dtype_fields.append(("index_10", ">u2", 1))
        if self.prim_flags & 2048:
            dtype_fields.append(("index_11", ">u2", 1))

        prim_dtype = np.dtype(dtype_fields)
        self.indices = np.frombuffer(
            bs.getbuffer(), prim_dtype, self.prim_count, bs.tell()
        )
        bs.seek(self.indices.nbytes, 1)


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

        self.positions: npt.NDArray
        self.normals: npt.NDArray
        self.colors: npt.NDArray
        self.attrs_3: npt.NDArray
        self.uvs: npt.NDArray
        self.attrs_5: npt.NDArray
        self.attrs_6: npt.NDArray
        self.attrs_7: npt.NDArray
        self.attrs_8: npt.NDArray
        self.attrs_9: npt.NDArray
        self.attrs_10: npt.NDArray
        self.attrs_11: npt.NDArray
        self.prim_groups: list[H3MPrimitiveGroup] = []

    def load_data(self, bs: BinaryReader):
        super().load_data(bs)

        # Read vertex attribute buffers
        self.positions = np.frombuffer(
            bs.getbuffer(), ">f4", bs.read_uint16() * 3, bs.tell()
        ).reshape(-1, 3)
        bs.seek(self.positions.nbytes, 1)

        self.normals = np.frombuffer(
            bs.getbuffer(), ">f4", bs.read_uint16() * 3, bs.tell()
        ).reshape(-1, 3)
        bs.seek(self.normals.nbytes, 1)

        self.colors = np.frombuffer(
            bs.getbuffer(), ">u1", bs.read_uint16() * 4, bs.tell()
        ).reshape(-1, 4)
        bs.seek(self.colors.nbytes, 1)

        self.attrs_3 = np.frombuffer(bs.getbuffer(), ">f4", bs.read_uint16(), bs.tell())
        bs.seek(self.attrs_3.nbytes, 1)

        self.uvs = np.frombuffer(
            bs.getbuffer(), ">f4", bs.read_uint16() * 2, bs.tell()
        ).reshape(-1, 2)
        bs.seek(self.uvs.nbytes, 1)

        self.attrs_5 = np.frombuffer(
            bs.getbuffer(), ">f4", bs.read_uint16() * 2, bs.tell()
        ).reshape(-1, 2)
        bs.seek(self.attrs_5.nbytes, 1)

        self.attrs_6 = np.frombuffer(
            bs.getbuffer(), ">f4", bs.read_uint16() * 2, bs.tell()
        ).reshape(-1, 2)
        bs.seek(self.attrs_6.nbytes, 1)

        self.attrs_7 = np.frombuffer(
            bs.getbuffer(), ">f4", bs.read_uint16() * 2, bs.tell()
        ).reshape(-1, 2)
        bs.seek(self.attrs_7.nbytes, 1)

        self.attrs_8 = np.frombuffer(
            bs.getbuffer(), ">f4", bs.read_uint16() * 2, bs.tell()
        ).reshape(-1, 2)
        bs.seek(self.attrs_8.nbytes, 1)

        self.attrs_9 = np.frombuffer(
            bs.getbuffer(), ">f4", bs.read_uint16() * 2, bs.tell()
        ).reshape(-1, 2)
        bs.seek(self.attrs_9.nbytes, 1)

        self.attrs_10 = np.frombuffer(
            bs.getbuffer(), ">f4", bs.read_uint16() * 2, bs.tell()
        ).reshape(-1, 2)
        bs.seek(self.attrs_10.nbytes, 1)

        self.attrs_11 = np.frombuffer(
            bs.getbuffer(), ">f4", bs.read_uint16() * 2, bs.tell()
        ).reshape(-1, 2)
        bs.seek(self.attrs_11.nbytes, 1)

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

        unk_0 = bs.read_uint16()
        unk_1 = bs.read_uint16()


class H3MSkinMeshObject(H3MMeshObject):
    def __init__(self) -> None:
        super().__init__()

        self.skin_transform: Matrix
        self.extra_prim_group: H3MPrimitiveGroup
        self.bones: list[H3MBone] = []
        self.bone_indices: list[float] = []
        self.bone_weights: list[float] = []

    def load_data(self, bs: BinaryReader):
        super().load_data(bs)

        # Read extra primitive group
        unk_0 = bs.read_int16()
        extra_prim_count = bs.read_uint16()
        last_prim_group = self.prim_groups[-1]
        self.extra_prim_group = H3MPrimitiveGroup(
            last_prim_group.prim_type, extra_prim_count, 3, True
        )
        self.extra_prim_group.load_data(bs)

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

            # Combine primitive group indices
            if is_skinned:
                triangles = obj.extra_prim_group.indices["position"].reshape(-1, 3)
                normal_indices = obj.extra_prim_group.indices["normal"]
                uv_indices = np.array([])
            else:
                triangles = np.concatenate(
                    [prim_group.indices["position"] for prim_group in obj.prim_groups]
                ).reshape(-1, 3)
                normal_indices = np.concatenate(
                    [prim_group.indices["normal"] for prim_group in obj.prim_groups]
                )
                uv_indices = np.concatenate(
                    [prim_group.indices["uv"] for prim_group in obj.prim_groups]
                )

            # Create mesh
            mesh = bpy.data.meshes.new(obj.name)
            mesh.from_pydata(obj.positions, [], triangles)
            mesh.validate()
            mesh.update()

            # Import normals
            loop_normals: list[tuple[float, float, float]] = []
            for i, normal_idx in enumerate(normal_indices):
                if normal_idx >= len(obj.normals):
                    print(f"Warning: Normal index {i} exceeded buffer length")
                    break
                x, y, z = obj.normals[int(normal_idx)]
                loop_normals.append((-x, -y, -z))
            else:
                if len(loop_normals) == len(mesh.loops):
                    mesh.normals_split_custom_set(loop_normals)
                else:
                    print("Warning: Normal count does not match loop count")

            # Import flipped UVs
            uv_layer = mesh.uv_layers.new()
            for i, uv_idx in enumerate(uv_indices):
                if uv_idx >= len(obj.uvs):
                    print(f"Warning: UV index {uv_idx}, {i} exceeded buffer length")
                    break
                uv = obj.uvs[int(uv_idx)]
                uv_layer.data[i].uv = (uv[0], 1.0 - uv[1])

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
