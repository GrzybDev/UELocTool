from io import BufferedReader
from pathlib import Path

from ueloctool.api.enumerators.export import ExportMode
from ueloctool.api.formats.locres.namespace import Namespace
from ueloctool.api.formats.locres.string import String
from ueloctool.api.formats.locres.version import LocresVersion
from ueloctool.api.handler import Handler
from ueloctool.api.helpers import ReadString
from ueloctool.api.magic import MAGIC_LOCRES


class LocresFile(Handler):

    __file_version: LocresVersion
    __namespaces: list[Namespace] = []

    def __init__(self, file: BufferedReader, allow_legacy: bool = False):
        super().__init__(file)

        self._file_handle.seek(0)
        file_magic = self._file_handle.read(0x10)

        if file_magic == MAGIC_LOCRES:
            try:
                version_int = int.from_bytes(self._file_handle.read(1))
                self.__file_version = LocresVersion(version_int)
            except ValueError:
                raise Exception(
                    "This version of the locres file format is not supported. (Locres version: {version_int})"
                )
        else:
            if not allow_legacy:
                raise Exception("This is not a valid locres file.")

            self.__file_version = LocresVersion.LEGACY
            self._file_handle.seek(0)

    def parse(self):
        if self.__file_version.value >= LocresVersion.COMPACT.value:
            strings = self.__parse_compact()
        else:
            self.__parse_legacy()
            return

        if self.__file_version.value >= LocresVersion.OPTIMIZED.value:
            self._file_handle.seek(4, 1)  # Skip the Keys Count

        namespace_count = int.from_bytes(self._file_handle.read(4), byteorder="little")

        for _ in range(namespace_count):
            namespace_hash = None

            if self.__file_version.value >= LocresVersion.OPTIMIZED.value:
                namespace_hash = int.from_bytes(
                    self._file_handle.read(4), byteorder="little"
                )

            namespace_name = ReadString(self._file_handle)
            key_count = int.from_bytes(self._file_handle.read(4), byteorder="little")

            for _ in range(key_count):
                key_hash = None

                if self.__file_version.value >= LocresVersion.OPTIMIZED.value:
                    key_hash = int.from_bytes(
                        self._file_handle.read(4), byteorder="little"
                    )

                key = ReadString(self._file_handle)
                source_string_hash = int.from_bytes(
                    self._file_handle.read(4), byteorder="little"
                )

                if self.__file_version.value >= LocresVersion.COMPACT.value:
                    string_idx = int.from_bytes(
                        self._file_handle.read(4), byteorder="little"
                    )

                    namespace = next(
                        (ns for ns in self.__namespaces if ns.name == namespace_name),
                        None,
                    )

                    if not namespace:
                        namespace = Namespace(namespace_name, hash=namespace_hash)
                        self.__namespaces.append(namespace)

                    namespace.strings.append(
                        String(
                            key=key,
                            key_hash=key_hash,
                            value=strings[string_idx],
                            value_hash=source_string_hash,
                        )
                    )

    def __parse_compact(self):
        strings = []
        strings_offset = int.from_bytes(self._file_handle.read(8), byteorder="little")
        header_offset = self._file_handle.tell()

        if strings_offset < 0:
            raise Exception("Invalid localized strings offset.")

        self._file_handle.seek(strings_offset)
        strings_count = int.from_bytes(self._file_handle.read(4), byteorder="little")

        for _ in range(strings_count):
            strings.append(ReadString(self._file_handle))

            if self.__file_version.value >= LocresVersion.OPTIMIZED.value:
                self._file_handle.read(4)

        self._file_handle.seek(header_offset)
        return strings

    def __parse_legacy(self):
        hash_table_count = int.from_bytes(self._file_handle.read(4), byteorder="little")

        for _ in range(hash_table_count):
            namespace_name = ReadString(self._file_handle)
            strings_count = int.from_bytes(
                self._file_handle.read(4), byteorder="little"
            )

            for _ in range(strings_count):
                key_hash = ReadString(self._file_handle)
                source_string_hash = int.from_bytes(
                    self._file_handle.read(4), byteorder="little"
                )

                namespace = next(
                    (ns for ns in self.__namespaces if ns.name == namespace_name),
                    None,
                )

                if not namespace:
                    namespace = Namespace(namespace_name)
                    self.__namespaces.append(namespace)

                namespace.strings.append(
                    String(
                        key=key_hash,
                        key_hash=0,
                        value=ReadString(self._file_handle),
                        value_hash=source_string_hash,
                    )
                )

    def export(self, output_file: Path, mode: ExportMode):
        data = []

        for namespace in self.__namespaces:
            for string in namespace.strings:
                key = (
                    f"{namespace.name}::{string.key}" if namespace.name else string.key
                )
                data.append((key, string.value))

        super().export(data, output_file, mode)
