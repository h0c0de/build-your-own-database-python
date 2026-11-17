# physical.py — Lapisan fisik DBDB: Storage.
#
# Satu gagasan menanggung seluruh jaminan database ini: berkas
# TIDAK PERNAH ditimpa. Setiap data ditulis dengan menempel di
# ujung berkas (append-only) dan alamatnya — posisi byte-nya —
# menjadi namanya selamanya. Satu-satunya pengecualian adalah
# superblock: 8 byte pertama yang memegang alamat akar pohon.
# Karena alamat akar duduk di batas sektor dan penulisan satu
# sektor bersifat atomik menurut perangkat keras, pembaruan alamat
# akar adalah atomik: pembaca melihat akar lama ATAU akar baru,
# tak pernah campurannya. Dan karena semua data di-fsync SEBELUM
# alamat akar diperbarui, akar tak pernah menunjuk data yang
# belum tahan di disk — di situlah commit menjadi durable.
#
# Format catatan: awalan panjang 8 byte (big-endian) + muatan.

import fcntl
import os
import struct

SUPERBLOCK_UKURAN = 8
_integer = struct.Struct('>Q')


class Storage:
    def __init__(self, f):
        self._f = f
        self.locked = False
        self._pastikan_superblock()

    # --- superblock ---

    def _pastikan_superblock(self):
        self._f.seek(0, os.SEEK_END)
        if self._f.tell() < SUPERBLOCK_UKURAN:
            self._f.seek(0)
            self._write_integer(0)
            self._f.flush()
            os.fsync(self._f.fileno())

    def _seek_superblock(self):
        self._f.seek(0)

    def _write_integer(self, integer):
        self._f.write(_integer.pack(integer))

    def _read_integer(self):
        return _integer.unpack(self._f.read(_integer.size))[0]

    def get_root_address(self):
        # Dibaca dengan os.pread, BUKAN lewat objek berkas
        # berpenyangga: penyangga baca Python menganggap seek di
        # dalam jendela yang sudah terbaca tidak perlu syscall,
        # sehingga alamat akar yang ditulis PROSES LAIN bisa tak
        # terlihat selamanya (tertangkap baterai Irisan 4:
        # pembaca membeku di generasi pertama). pread selalu
        # bertanya ke sistem operasi.
        data = os.pread(self._f.fileno(), _integer.size, 0)
        if len(data) < _integer.size:
            return 0
        return _integer.unpack(data)[0]

    def commit_root_address(self, root_address):
        # Urutan adalah jaminannya: kunci, paksa semua data yang
        # sudah ditulis turun ke disk, BARU pindahkan alamat akar,
        # lalu paksa itu pun turun.
        self.lock()
        self._f.flush()
        os.fsync(self._f.fileno())
        self._seek_superblock()
        self._write_integer(root_address)
        self._f.flush()
        os.fsync(self._f.fileno())
        self.unlock()

    # --- catatan append-only ---

    def write(self, data):
        """Tempel data di ujung berkas; kembalikan alamatnya.
        Alamat = posisi awalan panjangnya; ia sah selamanya karena
        byte yang sudah tertulis tidak pernah diubah."""
        self._f.seek(0, os.SEEK_END)
        alamat = self._f.tell()
        self._write_integer(len(data))
        self._f.write(data)
        self._f.flush()
        return alamat

    def read(self, address):
        # pread juga di sini, dengan alasan yang sama seperti
        # get_root_address: tak ada keadaan posisi/penyangga yang
        # bisa menyajikan byte basi antar-proses.
        kepala = os.pread(self._f.fileno(), _integer.size, address)
        panjang = _integer.unpack(kepala)[0]
        return os.pread(self._f.fileno(), panjang, address + _integer.size)

    # --- kunci ---
    # Bab aslinya memakai portalocker; di sini fcntl.flock dari
    # stdlib — semantik yang sama di Linux: eksklusif antar-proses,
    # dan terlepas otomatis bila proses pemegangnya mati (itulah
    # yang membuat penulis yang dibunuh -9 tidak mengunci database
    # selamanya; dibuktikan di Irisan 4).

    def lock(self):
        if not self.locked:
            fcntl.flock(self._f, fcntl.LOCK_EX)
            self.locked = True
            return True
        return False

    def unlock(self):
        if self.locked:
            self._f.flush()
            fcntl.flock(self._f, fcntl.LOCK_UN)
            self.locked = False

    # --- siklus hidup ---

    @property
    def closed(self):
        return self._f.closed

    def close(self):
        self.unlock()
        self._f.close()

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.close()
        return False
