import struct

from io import BytesIO
from mathutils import Matrix, Quaternion, Color

class BinaryReader:
    def __init__(self) -> None:
        self.bs: BytesIO
        self.data_size: int = 0

    def read_uint8(self) -> int:
        return int.from_bytes(self.bs.read(1), signed=False)
    
    def read_int8(self) -> int:
        return int.from_bytes(self.bs.read(1), signed=True)

    def read_uint16(self) -> int:
        return int.from_bytes(self.bs.read(2), signed=False)

    def read_int16(self) -> int:
        return int.from_bytes(self.bs.read(2), signed=True)

    def read_uint32(self) -> int:
        return int.from_bytes(self.bs.read(4), signed=False)

    def read_int32(self) -> int:
        return int.from_bytes(self.bs.read(4), signed=True)

    def read_vec2f(self) -> tuple[float, float]:
        return struct.unpack(f">2f", self.bs.read(8))

    def read_vec3f(self) -> tuple[float, float, float]:
        return struct.unpack(f">3f", self.bs.read(12))

    def read_rgba(self) -> tuple[float, float, float, float]:
        r, g, b, a = struct.unpack(f">4B", self.bs.read(4))
        return (r / 255, g / 255, b / 255, a / 255)

    def read_rotation(self) -> Quaternion:
        return Quaternion(struct.unpack(">4f", self.bs.read(16)))

    def read_matrix(self):
        floats = struct.unpack(">16f", self.bs.read(64))
        return Matrix((
            floats[0:4],
            floats[4:8],
            floats[8:12],
            floats[12:16],
        )).transposed()