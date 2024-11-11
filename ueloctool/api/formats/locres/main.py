from binascii import crc32
from io import BufferedReader
from pathlib import Path

from cityhash import CityHash64

from ueloctool.api.enumerators.data_format import DataFormat
from ueloctool.api.enumerators.missing_string import MissingStringBehaviour
from ueloctool.api.formats.locres.namespace import Namespace
from ueloctool.api.formats.locres.string import String, StringEntry
from ueloctool.api.formats.locres.version import LocresVersion
from ueloctool.api.handler import Handler
from ueloctool.api.helpers import ReadString, WriteString
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

    def export(self, output_file: Path, mode: DataFormat):
        data = []

        for namespace in self.__namespaces:
            for string in namespace.strings:
                key = (
                    f"{namespace.name}::{string.key}" if namespace.name else string.key
                )
                data.append((key, string.value))

        super().export(data, output_file, mode)

    def apply_language_data(
        self, data: dict[str, str], missing_strings_behaviour: MissingStringBehaviour
    ):
        # Find all strings that need to be updated

        new_namespaces: list[Namespace] = []

        for namespace in self.__namespaces:
            for string in namespace.strings:
                key = (
                    f"{namespace.name}::{string.key}" if namespace.name else string.key
                )

                if key not in data:
                    match missing_strings_behaviour:
                        case MissingStringBehaviour.KeyAndOriginal:
                            value = f"({string.key}) {string.value}"
                        case MissingStringBehaviour.Key:
                            value = string.key
                        case MissingStringBehaviour.Original:
                            value = string.value
                        case MissingStringBehaviour.Empty:
                            value = ""
                        case MissingStringBehaviour.Remove:
                            continue
                        case MissingStringBehaviour.Error:
                            raise Exception(f"Missing localized string for {key}")
                else:
                    value = data[key]

                new_namespace = next(
                    (ns for ns in new_namespaces if ns.name == namespace.name),
                    None,
                )

                if not new_namespace:
                    new_namespace = Namespace(namespace.name)
                    new_namespaces.append(new_namespace)

                new_namespace.strings.append(
                    String(
                        key=string.key,
                        key_hash=string.key_hash,
                        value=value,
                        value_hash=string.value_hash,
                    )
                )

        self.__namespaces = new_namespaces

    def __calc_hash(self, namespace_name: str) -> int:
        if self.__file_version.value == LocresVersion.OPTIMIZED_CITYHASH64_UTF16.value:
            return CityHash64(namespace_name)
        elif self.__file_version.value >= LocresVersion.OPTIMIZED.value:
            return crc32(namespace_name)
        else:
            return 0

    def save(self, output_file: Path):
        with open(output_file, "wb") as new_file:
            if self.__file_version.value != LocresVersion.LEGACY.value:
                self.__save_compact(new_file)
            else:
                self.__save_legacy(new_file)

    def __save_compact(self, file):
        file.write(MAGIC_LOCRES)
        file.write(self.__file_version.value.to_bytes(1))

        header_offset = file.tell()
        file.write(int(0).to_bytes(8))  # Placeholder for header offset

        if self.__file_version.value >= LocresVersion.OPTIMIZED.value:
            keys_count = sum(len(namespace.strings) for namespace in self.__namespaces)
            file.write(keys_count.to_bytes(4, byteorder="little"))

        namespaces_count = len(self.__namespaces)
        file.write(namespaces_count.to_bytes(4, byteorder="little"))

        entries: list[StringEntry] = []

        for namespace in self.__namespaces:
            if self.__file_version.value >= LocresVersion.OPTIMIZED.value:
                if namespace.hash == 0:
                    file.write(
                        self.__calc_hash(namespace.name).to_bytes(
                            4, byteorder="little"
                        ),
                    )
                else:
                    file.write(namespace.hash.to_bytes(4, byteorder="little"))

            WriteString(file, namespace.name)
            file.write(len(namespace.strings).to_bytes(4, byteorder="little"))

            for string in namespace.strings:
                if self.__file_version.value >= LocresVersion.OPTIMIZED.value:
                    if string.key_hash:
                        file.write(string.key_hash.to_bytes(4, byteorder="little"))
                    else:
                        file.write(
                            self.__calc_hash(string.key).to_bytes(4, byteorder="little")
                        )

                WriteString(file, string.key)

                if string.value_hash:
                    file.write(string.value_hash.to_bytes(4, byteorder="little"))
                else:
                    file.write(crc32(string.value).to_bytes(4, byteorder="little"))

                # Save only unique strings
                string_idx = next(
                    (idx for idx, s in enumerate(entries) if s.text == string.value),
                    None,
                )

                if string_idx is None:
                    entry = StringEntry(string.value)
                    entries.append(entry)
                    string_idx = entries.index(entry)
                else:
                    entries[string_idx].references += 1

                file.write(string_idx.to_bytes(4, byteorder="little"))

        strings_offset = file.tell()
        file.write(len(entries).to_bytes(4, byteorder="little"))

        if self.__file_version.value >= LocresVersion.OPTIMIZED.value:
            for entry in entries:
                WriteString(file, entry.text)
                file.write(entry.references.to_bytes(4, byteorder="little"))
        else:
            for entry in entries:
                WriteString(file, entry.text)

        file.seek(header_offset)
        file.write(strings_offset.to_bytes(8, byteorder="little"))

    def __save_legacy(self, file):
        file.write(len(self.__namespaces).to_bytes(4, byteorder="little"))

        for namespace in self.__namespaces:
            WriteString(file, namespace.name)
            file.write(len(namespace.strings).to_bytes(4, byteorder="little"))

            for string in namespace.strings:
                WriteString(file, string.key)

                if string.value_hash:
                    file.write(string.value_hash.to_bytes(4, byteorder="little"))
                else:
                    file.write(crc32(string.value).to_bytes(4, byteorder="little"))

                WriteString(file, string.value)
