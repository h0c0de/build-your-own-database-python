# uji_irisan3.py — Bukti Irisan 3: antarmuka dict + tool CLI.
# CLI diuji sebagai proses sungguhan (python3 -m dbdb.tool) supaya
# kode keluarnya terbukti di batas proses, bukan di dalam proses.

import os
import subprocess
import sys
import tempfile

PROYEK = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, PROYEK)
import dbdb
from dbdb.tool import OK, BAD_ARGS, BAD_VERB, BAD_KEY

gagal = []


def cek(nama, kondisi, detail=''):
    print(('PASS' if kondisi else 'FAIL'), nama, detail)
    if not kondisi:
        gagal.append(nama)


def cli(*args):
    env = dict(os.environ, PYTHONPATH=PROYEK)
    return subprocess.run([sys.executable, '-m', 'dbdb.tool', *args],
                          capture_output=True, text=True, env=env, cwd=PROYEK)


with tempfile.TemporaryDirectory() as d:
    path = os.path.join(d, 'api.db')

    # --- API dict ---
    with dbdb.connect(path) as db:
        db['halo'] = 'dunia'
        db['anjing'] = 'kasur'
        db.commit()
        cek('API: get/set/in/len seperti dict',
            db['halo'] == 'dunia' and 'anjing' in db and 'x' not in db and len(db) == 2)
        del db['anjing']
        db.commit()
        cek('API: del bekerja', 'anjing' not in db and len(db) == 1)
        for aksi in (lambda: db['tak-ada'], lambda: db.__delitem__('tak-ada')):
            try:
                aksi()
                salah = False
            except KeyError:
                salah = True
            if not salah:
                break
        cek('API: kunci hilang -> KeyError', salah)
        try:
            db[1] = 'x'
            tipe_ok = False
        except TypeError:
            tipe_ok = True
        cek('API: kunci non-str ditolak TypeError', tipe_ok)
    try:
        db['halo']
        tutup_ok = False
    except ValueError:
        tutup_ok = True
    cek('API: pakai sesudah close -> ValueError', tutup_ok)

    # --- connect tidak pernah menimpa ---
    sebelum = open(path, 'rb').read()
    db2 = dbdb.connect(path)
    db2['halo']  # baca saja
    db2.close()
    cek('connect + baca tidak mengubah satu byte pun berkas',
        open(path, 'rb').read() == sebelum)
    db3 = dbdb.connect(path)
    cek('buka ulang: isi bertahan', db3['halo'] == 'dunia' and len(db3) == 1)
    db3.close()

    # --- CLI antar-proses ---
    cpath = os.path.join(d, 'cli.db')
    r = cli(cpath, 'set', 'warna', 'biru')
    cek('CLI set -> OK', r.returncode == OK, f'rc={r.returncode}')
    r = cli(cpath, 'get', 'warna')
    cek('CLI get di proses baru membaca nilai commit proses lain',
        r.returncode == OK and r.stdout == 'biru\n', f'rc={r.returncode} out={r.stdout!r}')
    r = cli(cpath, 'get', 'tak-ada')
    cek('CLI get kunci hilang -> BAD_KEY', r.returncode == BAD_KEY, f'rc={r.returncode}')
    r = cli(cpath, 'delete', 'warna')
    r2 = cli(cpath, 'get', 'warna')
    cek('CLI delete lalu get -> BAD_KEY', r.returncode == OK and r2.returncode == BAD_KEY)
    r = cli(cpath, 'lompat', 'warna')
    cek('CLI kata kerja asing -> BAD_VERB', r.returncode == BAD_VERB, f'rc={r.returncode}')
    r = cli(cpath)
    cek('CLI argumen kurang -> BAD_ARGS', r.returncode == BAD_ARGS, f'rc={r.returncode}')
    r = cli(cpath, 'set', 'hanya-kunci')
    cek('CLI set tanpa nilai -> BAD_ARGS', r.returncode == BAD_ARGS, f'rc={r.returncode}')

print()
if gagal:
    print('GAGAL:', ', '.join(gagal))
    sys.exit(1)
print('SEMUA PASS — Irisan 3 terbukti: dict di disk + CLI antar-proses berkode keluar bab.')
