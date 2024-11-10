from enum import Enum


class LocresVersion(Enum):
    """
    Enum for the different versions of the locres file format.

    Attributes:
        LEGACY: Legacy locres file format - will be missing the magic number.
        COMPACT: Compact locres file format - strings are stored in a LUT to avoid duplication.
        OPTIMIZED: Optimized locres file format - namespaces/keys are pre-hashed (CRC32), we know the number of elements up-front, and the number of references for each string in the LUT (to allow stealing).
        OPTIMIZED_CITYHASH64_UTF16: Optimized locres file format with CityHash64 and UTF-16 encoding - namespaces/keys are pre-hashed (CityHash64, UTF-16), we know the number of elements up-front, and the number of references for each string in the LUT (to allow stealing).
    """

    LEGACY = 0
    COMPACT = 1
    OPTIMIZED = 2
    OPTIMIZED_CITYHASH64_UTF16 = 3
