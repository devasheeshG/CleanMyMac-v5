"""Wire a local data adapter into the native ARM64 executable only."""

import struct

from compatibility import CompatibilityError, arm64_slice


LIBRARY_PATH = '@executable_path/../Frameworks/CMM5LocalData.dylib'


def inject_adapter(data):
    start, length = arm64_slice(data)
    try:
        count, command_bytes = struct.unpack_from('<II', data, start + 16)
        begin = start + 32
        end = begin + command_bytes
        if count > 4096 or end > start + length:
            raise CompatibilityError('Invalid native load-command bounds.')
        first_section = start + length
        position = begin
        for _ in range(count):
            if position + 8 > end:
                raise CompatibilityError('Truncated native load-command table.')
            kind, size = struct.unpack_from('<II', data, position)
            if size < 8 or size % 8 or position + size > end:
                raise CompatibilityError('Invalid native load-command size.')
            if kind == 0x19:
                if size < 72:
                    raise CompatibilityError('Truncated native segment.')
                section_count = struct.unpack_from('<I', data, position + 64)[0]
                if 72 + section_count * 80 > size:
                    raise CompatibilityError('Truncated native section table.')
                for index in range(section_count):
                    offset = struct.unpack_from('<I', data, position + 72 + index * 80 + 48)[0]
                    if offset:
                        if offset >= length:
                            raise CompatibilityError('Native section lies outside its slice.')
                        first_section = min(first_section, start + offset)
            if kind == 0xc:
                if size < 24:
                    raise CompatibilityError('Truncated native library command.')
                name_offset = struct.unpack_from('<I', data, position + 8)[0]
                if not 24 <= name_offset < size:
                    raise CompatibilityError('Invalid native library name offset.')
                name = data[position + name_offset:position + size].split(b'\0', 1)[0]
                if name == LIBRARY_PATH.encode():
                    raise CompatibilityError('The local data adapter is already wired.')
            position += size
        if position != end:
            raise CompatibilityError('Native load-command byte count mismatch.')
        if first_section == start + length:
            raise CompatibilityError('No native file-backed section found.')
        name = LIBRARY_PATH.encode() + b'\0'
        size = (24 + len(name) + 7) // 8 * 8
        if end + size > first_section or any(data[end:end + size]):
            raise CompatibilityError('Insufficient zero-filled native header padding.')
        command = struct.pack('<IIIIII', 0xc, size, 24, 0, 0x10000, 0x10000) + name
        command += b'\0' * (size - len(command))
        result = bytearray(data)
        result[end:end + size] = command
        struct.pack_into('<II', result, start + 16, count + 1, command_bytes + size)
        return bytes(result)
    except struct.error as error:
        raise CompatibilityError('Truncated native load-command metadata.') from error
