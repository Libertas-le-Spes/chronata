def walk(data: bytes):
    for tag, body in children(data):
        yield tag, body
        if tag & 0x20 or tag == 0x04:
            yield from walk(body)


def children(data: bytes) -> list[tuple[int, bytes]]:
    found, offset = [], 0
    try:
        while offset < len(data):
            tag, body, offset = read(data, offset)
            found.append((tag, body))
    except ValueError:
        return []
    return found


def read(data: bytes, offset: int) -> tuple[int, bytes, int]:
    if offset + 2 > len(data):
        raise ValueError("truncated")
    tag, length, offset = data[offset], data[offset + 1], offset + 2
    if length & 0x80:
        length, offset = _long_length(data, offset, length & 0x7F)
    if offset + length > len(data):
        raise ValueError("truncated")
    return tag, data[offset:offset + length], offset + length


def _long_length(data: bytes, offset: int, count: int) -> tuple[int, int]:
    if not 0 < count <= 4 or offset + count > len(data):
        raise ValueError("bad length")
    return int.from_bytes(data[offset:offset + count], "big"), offset + count


def integer(value: int) -> bytes:
    return value.to_bytes(value.bit_length() // 8 + 1, "big")


def tlv(tag: int, body: bytes) -> bytes:
    if len(body) < 0x80:
        return bytes([tag, len(body)]) + body
    size = len(body).to_bytes((len(body).bit_length() + 7) // 8, "big")
    return bytes([tag, 0x80 | len(size)]) + size + body
