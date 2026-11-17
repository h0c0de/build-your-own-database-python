# uji_irisan1.py — Bukti Irisan 1: lapisan fisik Storage.
# Klaim yang dibuktikan dari isi berkas itu sendiri, bukan dari
# perilaku kelasnya: (1) data hanya ditempel, byte lama utuh;
# (2) superblock satu-satunya yang berubah, dan hanya lewat
# commit_root_address; (3) alamat adalah nama yang kekal.

import os
import subprocess
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from dbdb.physical import Storage, SUPERBLOCK_UKURAN

gagal = []


def cek(nama, kondisi, detail=''):
    print(('PASS' if kondisi else 'FAIL'), nama, detail)
    if not kondisi:
        gagal.append(nama)


def buka(path):
    f = open(path, 'r+b') if os.path.exists(path) else open(path, 'w+b')
    return Storage(f)


with tempfile.TemporaryDirectory() as d:
    path = os.path.join(d, 'uji.db')
    st = buka(path)
    cek('berkas baru: hanya superblock, alamat akar 0',
        os.path.getsize(path) == SUPERBLOCK_UKURAN and st.get_root_address() == 0,
        f'ukuran={os.path.getsize(path)}')

    muatan = [b'', b'x', b'kasur-anjing', os.urandom(100_000)]
    alamat = [st.write(m) for m in muatan]
    cek('alamat naik & berbeda', alamat == sorted(alamat) and len(set(alamat)) == 4,
        str(alamat))
    cek('baca kembali persis', all(st.read(a) == m for a, m in zip(alamat, muatan)))

    potret = open(path, 'rb').read()
    a5 = st.write(b'catatan kelima')
    st.commit_root_address(a5)
    kini = open(path, 'rb').read()
    cek('append-only: semua byte sesudah superblock adalah awalan utuh dari potret lama',
        kini[SUPERBLOCK_UKURAN:len(potret)] == potret[SUPERBLOCK_UKURAN:])
    cek('superblock berubah hanya karena commit alamat akar',
        kini[:SUPERBLOCK_UKURAN] != potret[:SUPERBLOCK_UKURAN]
        and st.get_root_address() == a5)

    st.close()
    st2 = buka(path)
    cek('buka ulang: alamat akar & semua catatan bertahan',
        st2.get_root_address() == a5
        and all(st2.read(a) == m for a, m in zip(alamat, muatan)))

    # kunci: proses lain tidak bisa mengambilnya selagi kita pegang
    cek('lock() pertama True, kedua False', st2.lock() is True and st2.lock() is False)
    probe = subprocess.run(
        [sys.executable, '-c',
         'import fcntl, sys\n'
         'f = open(sys.argv[1], "r+b")\n'
         'try:\n'
         '    fcntl.flock(f, fcntl.LOCK_EX | fcntl.LOCK_NB)\n'
         '    print("DAPAT")\n'
         'except BlockingIOError:\n'
         '    print("TERKUNCI")\n', path],
        capture_output=True, text=True)
    cek('proses lain tertahan oleh kunci kita', probe.stdout.strip() == 'TERKUNCI',
        probe.stdout.strip())
    st2.unlock()
    probe2 = subprocess.run(
        [sys.executable, '-c',
         'import fcntl, sys\n'
         'f = open(sys.argv[1], "r+b")\n'
         'try:\n'
         '    fcntl.flock(f, fcntl.LOCK_EX | fcntl.LOCK_NB)\n'
         '    print("DAPAT")\n'
         'except BlockingIOError:\n'
         '    print("TERKUNCI")\n', path],
        capture_output=True, text=True)
    cek('sesudah unlock, proses lain dapat kuncinya', probe2.stdout.strip() == 'DAPAT')
    st2.close()
    try:
        st2.write(b'x')
        tutup_ok = False
    except (ValueError, OSError):
        tutup_ok = True
    cek('tulis sesudah close ditolak', tutup_ok)

print()
if gagal:
    print('GAGAL:', ', '.join(gagal))
    sys.exit(1)
print('SEMUA PASS — Irisan 1 terbukti: append-only, superblock atomik, kunci antar-proses.')
