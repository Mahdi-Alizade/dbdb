import os
import struct
import portalocker
from dbdb.cache import LRUCache


class Storage:
    SUPERBLOCK_SIZE = 8
    SUPERBLOCK_FORMAT = "!Q"

    def __init__(self, f, cache_capacity: int = 256):
        self._f = f
        self._locked = False
        self._cache = LRUCache(capacity=cache_capacity)
        self._ensure_superblock()

    @property
    def closed(self):
        return self._f.closed

    @property
    def locked(self):
        return self._locked

    @property
    def cache(self):
        return self._cache

    def _ensure_superblock(self):
        self.lock()
        try:
            self._seek_end()
            end_address = self._f.tell()
            if end_address < self.SUPERBLOCK_SIZE:
                self._f.seek(0)
                self._f.write(b"\x00" * self.SUPERBLOCK_SIZE)
                self._f.flush()
        finally:
            self.unlock()

    def lock(self):
        if not self._locked:
            current_pos = self._f.tell()
            self._f.seek(0)
            portalocker.lock(self._f, portalocker.LOCK_EX)
            self._f.seek(current_pos)
            self._locked = True

    def unlock(self):
        if self._locked:
            self._f.flush()
            current_pos = self._f.tell()
            self._f.seek(0)
            try:
                portalocker.unlock(self._f)
            except Exception:
                pass
            finally:
                self._f.seek(current_pos)
                self._locked = False

    def _seek_end(self):
        self._f.seek(0, os.SEEK_END)

    def _seek_superblock(self):
        self._f.seek(0)

    def write(self, data: bytes) -> int:
        self._seek_end()
        address = self._f.tell()
        self._write_integer(len(data))
        self._f.write(data)
        # Store newly written chunk into cache immediately
        self._cache.set(address, data)
        return address

    def read(self, address: int) -> bytes:
        cached = self._cache.get(address)
        if cached is not None:
            return cached

        self._f.seek(address)
        length = self._read_integer()
        data = self._f.read(length)
        self._cache.set(address, data)
        return data

    def commit_root_address(self, root_address: int):
        self.lock()
        try:
            self._f.flush()
            self._seek_superblock()
            self._write_superblock_integer(root_address)
            self._f.flush()
        finally:
            self.unlock()

    def get_root_address(self) -> int:
        self._seek_superblock()
        return self._read_superblock_integer()

    def _write_integer(self, integer: int):
        self._f.write(struct.pack("!I", integer))

    def _read_integer(self) -> int:
        data = self._f.read(4)
        if not data:
            return 0
        return struct.unpack("!I", data)[0]

    def _write_superblock_integer(self, integer: int):
        self._f.write(struct.pack(self.SUPERBLOCK_FORMAT, integer))

    def _read_superblock_integer(self) -> int:
        data = self._f.read(self.SUPERBLOCK_SIZE)
        if not data:
            return 0
        return struct.unpack(self.SUPERBLOCK_FORMAT, data)[0]

    def close(self):
        if not self.closed:
            self.unlock()
            self._f.close()
            self._cache.clear()