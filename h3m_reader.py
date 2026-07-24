import bpy
import struct

from bpy.types import Context
from mathutils import Matrix
from io import BytesIO
from typing import NamedTuple
from .binary_reader import BinaryReader
from .lzss3 import decompress_bytes


class H3MBone(NamedTuple):
    parent_id: int
    name: str
    transform: Matrix


class H3MReader(BinaryReader):
    def __init__(self, min_bone_length: float) -> None:
        self.min_bone_length = min_bone_length
        self.bones: list[H3MBone] = []

        self.colors: list[tuple[float, float, float, float]] = []
        self.uvs: list[tuple[float, float]] = []
        self.positions: list[tuple[float, float, float]] = []
        self.normals: list[tuple[float, float, float]] = []
        self.triangles: list[tuple[int, int, int]] = []

        self.color_indices: list[int] = []
        self.uv_indices: list[int] = []
        self.position_indices: list[int] = []
        self.normal_indices: list[int] = []

    def read_text(self) -> str:
        text_len = self.read_uint16()
        text = self.bs.read(text_len - 1).decode()
        # Skip null end byte
        self.bs.read(1)

        return text

    def load_h3m(self, compressed_data: bytes) -> None:
        # Decompress LZ1 data
        data = decompress_bytes(compressed_data[4:])
        self.data_size = len(data)
        self.bs = BytesIO(data)

        # Read header
        version = self.read_uint16()
        texture_count = self.read_uint16()
        bone_count = self.read_uint16()
        self.read_uint16()
        self.read_uint16()
        self.read_uint16()

        # Read textures
        for _ in range(texture_count):
            struct.unpack(">15f", self.bs.read(60))
            self.read_uint16()
            tex_name = self.read_text()
            if not tex_name:
                # Skip internal texture
                self.read_uint16()
                tex_size = self.read_uint16()
                self.bs.seek(tex_size, 1)

        self.read_uint16()
        self.read_uint16()

        # Read bones
        for _ in range(bone_count):
            parent_id = self.read_uint16()
            bone_name = self.read_text()
            self.read_uint16()
            self.read_uint16()
            bone_rot = self.read_rotation()
            bone_pos = self.read_vec3f()
            bone_scale = self.read_vec3f()
            bone_transform = Matrix.LocRotScale(bone_pos, bone_rot, bone_scale)

            self.bones.append(H3MBone(
                parent_id,
                bone_name,
                bone_transform,
            ))

        # Read vertex attribute buffers
        position_count = self.read_uint16()
        self.positions = [self.read_vec3f() for _ in range(position_count)]
        normal_count = self.read_uint16()
        self.normals = [self.read_vec3f() for _ in range(normal_count)]
        color_count = self.read_uint16()
        self.colors = [self.read_rgba() for _ in range(color_count)]
        unk_attr_count = self.read_uint16()
        unk_attrs = [self.read_vec2f() for _ in range(unk_attr_count)]
        uv_count = self.read_uint16()
        self.uvs = [self.read_vec2f() for _ in range(uv_count)]

        # Skip unknown values for now
        self.bs.seek(24, 1)

        # Read corner indices
        position_indices: list[int] = []
        prim_count = self.read_uint16()
        if color_count > 0:
            for _ in range(prim_count):
                self.color_indices.append(self.read_uint16())
                self.uv_indices.append(self.read_uint16())
                position_indices.append(self.read_uint16())
                self.normal_indices.append(self.read_uint16())
        else:
            for _ in range(prim_count):
                self.normal_indices.append(self.read_uint16())
                self.uv_indices.append(self.read_uint16())
                position_indices.append(self.read_uint16())

        # Group position indices into triangles
        for i in range(0, len(position_indices), 3):
            a, b, c = position_indices[i:i+3]
            self.triangles.append((a, b, c))

    def import_h3m(self, context: Context) -> None:
        # Create armature object
        armature = bpy.data.armatures.new("Armature")
        armature_obj = bpy.data.objects.new("Armature", armature)
        context.collection.objects.link(armature_obj)
        #armature_obj.rotation_euler = (math.radians(90.0), 0.0, 0.0)

        context.view_layer.objects.active = armature_obj
        bpy.ops.object.mode_set(mode="EDIT")

        # Create bones
        for h3m_bone in self.bones:
            bone = armature.edit_bones.new(h3m_bone.name)
            bone.tail = (0, 0.01, 0)
            bone.matrix = h3m_bone.transform

        # Update bone hierarchy and lengths
        for i, h3m_bone in enumerate(self.bones):
            if h3m_bone.parent_id >= 0 and False:
                bone = armature.edit_bones[i]
                bone.parent = armature.edit_bones[h3m_bone.parent_id]

                parent_distance = (bone.head - bone.parent.head).length
                bone.length = max(parent_distance, self.min_bone_length)

        bpy.ops.object.mode_set(mode="OBJECT")

        # Create mesh
        mesh = bpy.data.meshes.new("Mesh")
        mesh.from_pydata(self.positions, [], self.triangles)

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

        # Parent to armature
        mesh_obj = bpy.data.objects.new("Mesh", mesh)
        context.collection.objects.link(mesh_obj)
        mesh_obj.parent = armature_obj

        # Add armature modifier
        modifier = mesh_obj.modifiers.new("Armature", 'ARMATURE')
        modifier.object = armature_obj

    # def import_mesh_z(self, context: Context, file_path: Path) -> None:
    #     with open(file_path, "rb") as f:
    #         reader = MeshZReader()
    #         mesh_z = reader.read_mesh_z(f.read())

    #     for submesh in mesh_z.submeshes:
    #         mesh = bpy.data.meshes.new(str(mesh_z.crc))
    #         mesh.from_pydata(submesh.positions, [], submesh.triangles)

    #         # Import UVs
    #         uv_layer = mesh.uv_layers.new(name=f"UV0")
    #         for loop in mesh.loops:
    #             uv = submesh.uvs[loop.vertex_index]
    #             uv_layer.data[loop.index].uv = (uv[0], 1.0 - uv[1])

    #         # Import normals
    #         mesh.normals_split_custom_set_from_vertices(submesh.normals)

    #         mesh.validate()
    #         mesh.update()

    #         mesh_obj = bpy.data.objects.new(str(mesh_z.crc), mesh)
    #         mesh_obj.matrix_basis = submesh.transform
    #         context.collection.objects.link(mesh_obj)

    #         if not self.armature_obj or not self.skel_z:
    #             return

    #         mesh_obj.parent = self.armature_obj
    #         modifier = mesh_obj.modifiers.new("Armature", 'ARMATURE')
    #         modifier.object = self.armature_obj

    #         # Create and populate vertex groups
    #         vertex_groups = [
    #             mesh_obj.vertex_groups.new(name=str(bone_crc))
    #             for bone_crc in submesh.bone_crcs
    #         ]

    #         for i, weight in enumerate(submesh.weights):
    #             for j, vertex_group in enumerate(vertex_groups):
    #                 vertex_group.add([i], weight[j], 'ADD')
