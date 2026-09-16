import os
import struct
import portalocker


class Storage:
    SUPERBLOCK_SIZE = 8
    SUPERBLOCK_FORMAT = "!Q"

    def __init__(self, f):
        self._f = f
        self._locked = False
        self._ensure_superblock()

    @property
    def closed(self):
        return self._f.closed

    @property
    def locked(self):
        return self._locked

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
            self._f.seek(0)
            portalocker.lock(self._f, portalocker.LOCK_EX)
            self._locked = True

    def unlock(self):
        if self._locked:
            self._f.flush()
            self._f.seek(0)
            portalocker.unlock(self._f)
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
        return address

    def read(self, address: int) -> bytes:
        self._f.seek(address)
        length = self._read_integer()
        data = self._f.read(length)
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
        self.unlock()
        self._f.close()