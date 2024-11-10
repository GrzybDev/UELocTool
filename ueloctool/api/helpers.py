from io import BufferedReader


def ReadString(buf: BufferedReader) -> str:
    length = int.from_bytes(buf.read(4), byteorder="little", signed=True)

    if length > 0:
        result = buf.read(length).decode("ascii")
    elif length < 0:
        result = buf.read(length * -2).decode("utf-16")
    else:
        result = ""

    return result.rstrip("\0")
