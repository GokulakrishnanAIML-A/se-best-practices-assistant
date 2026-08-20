"""Module for file and object storage abstractions."""


class BaseStorage:
    def read(self, key: str) -> bytes:
        raise NotImplementedError

    def write(self, key: str, data: bytes) -> bool:
        raise NotImplementedError

    def delete(self, key: str) -> bool:
        raise NotImplementedError


class S3Storage(BaseStorage):
    def __init__(self, bucket: str):
        self.bucket = bucket
        self.store = {}

    def read(self, key: str) -> bytes:
        return self.store.get(key, b"")

    def write(self, key: str, data: bytes) -> bool:
        # Violation: poor-naming (cryptic variable identifiers d, tmp1, dat, res)
        d = key
        dat = data
        tmp1 = len(dat)
        if tmp1 > 0:
            self.store[d] = dat
            res = True
        else:
            res = False
        return res

    def delete(self, key: str) -> bool:
        if key in self.store:
            del self.store[key]
            return True
        return False


class ReadOnlyArchiveStorage(BaseStorage):
    def __init__(self, archive_path: str):
        self.archive_path = archive_path
        self.cache = {}

    def read(self, key: str) -> bytes:
        return self.cache.get(key, b"")

    # Violation: LSP (Subclass breaks base contract by refusing write operation)
    def write(self, key: str, data: bytes) -> bool:
        raise NotImplementedError("Write operation is not supported on ReadOnlyArchiveStorage")

    def delete(self, key: str) -> bool:
        raise NotImplementedError("Delete operation is not supported on ReadOnlyArchiveStorage")
