from io import BufferedReader

from ueloctool.api.formats.locres.version import LocresVersion
from ueloctool.api.handler import Handler
from ueloctool.api.helpers import ReadString
from ueloctool.api.magic import MAGIC_LOCRES
from ueloctool.api.string import UnrealString


class LocresFile(Handler):

    __file_version: LocresVersion

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
            self.__parse_compact()
        else:
            self.__parse_legacy()

        if self.__file_version.value >= LocresVersion.OPTIMIZED.value:
            self._file_handle.seek(4, 1)  # Skip the FileHash

        namespace_count = int.from_bytes(self._file_handle.read(4), byteorder="little")

        for _ in range(namespace_count):
            if self.__file_version.value >= LocresVersion.OPTIMIZED.value:
                self._file_handle.seek(4, 1)  # Skip the Namespace Hash

            namespace = ReadString(self._file_handle)
            key_count = int.from_bytes(self._file_handle.read(4), byteorder="little")

            for _ in range(key_count):
                if self.__file_version.value >= LocresVersion.OPTIMIZED.value:
                    self._file_handle.read(4)  # Skip the Key Hash

                key = ReadString(self._file_handle)
                self._file_handle.read(4)  # Skip the SourceStringHash

                if self.__file_version.value >= LocresVersion.COMPACT.value:
                    string_idx = int.from_bytes(
                        self._file_handle.read(4), byteorder="little"
                    )

                    if len(self._entries) > string_idx:
                        self._entries[string_idx].namespace = namespace
                        self._entries[string_idx].key = key

    def __parse_compact(self):
        strings_offset = int.from_bytes(self._file_handle.read(8), byteorder="little")
        header_offset = self._file_handle.tell()

        if strings_offset < 0:
            raise Exception("Invalid localized strings offset.")

        self._file_handle.seek(strings_offset)
        strings_count = int.from_bytes(self._file_handle.read(4), byteorder="little")

        for _ in range(strings_count):
            self._entries.append(UnrealString(value=ReadString(self._file_handle)))

            if self.__file_version.value >= LocresVersion.OPTIMIZED.value:
                self._file_handle.read(4)

        self._file_handle.seek(header_offset)

    def __parse_legacy(self):
        hash_table_count = int.from_bytes(self._file_handle.read(4), byteorder="little")

        for _ in range(hash_table_count):
            namespace = ReadString(self._file_handle)
            strings_count = int.from_bytes(
                self._file_handle.read(4), byteorder="little"
            )

            for _ in range(strings_count):
                hash = ReadString(self._file_handle)
                self._file_handle.seek(4, 1)
                self._entries.append(
                    UnrealString(key=hash, value=ReadString(self._file_handle))
                )
