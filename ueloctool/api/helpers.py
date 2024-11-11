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


def WriteString(buf: BufferedReader, string: str) -> None:
    if string:
        string += "\0"

    is_ascii = all(ord(char) < 128 for char in string)

    if is_ascii:
        buf.write(len(string).to_bytes(4, byteorder="little", signed=True))
        buf.write(string.encode("ascii"))
    else:
        buf.write((-len(string)).to_bytes(4, byteorder="little", signed=True))
        buf.write(string.encode("utf-16-le"))
