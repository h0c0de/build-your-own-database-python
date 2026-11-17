# uji_irisan4.py — Baterai penutup: durabilitas & konkurensi.
# Tiga janji bab ini diuji dengan cara paling tidak ramah yang
# bisa kami lakukan: penulis dibunuh -9 di tengah pekerjaan,
# pembaca tanpa kunci membaca di tengah hujan commit, dan
# pembaca yang memegang akar lama dibiarkan membaca sementara
# dunia berubah di sekelilingnya.

import os
import signal
import subprocess
import sys
import tempfile
import time

PROYEK = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, PROYEK)
import dbdb
from dbdb.physical import Storage
from dbdb.binary_tree import BinaryTree, BinaryNodeRef

gagal = []


def cek(nama, kondisi, detail=''):
    print(('PASS' if kondisi else 'FAIL'), nama, detail)
    if not kondisi:
        gagal.append(nama)


def tulis_helper(d, nama, isi):
    p = os.path.join(d, nama)
    with open(p, 'w') as f:
        f.write(isi)
    return p


def jalankan(script, *args, timeout=60):
    env = dict(os.environ, PYTHONPATH=PROYEK)
    return subprocess.run([sys.executable, script, *args],
                          capture_output=True, text=True, env=env, timeout=timeout)


with tempfile.TemporaryDirectory() as d:
    # ---------- 1. Penulis dibunuh -9 di tengah pekerjaan ----------
    path = os.path.join(d, 'bunuh.db')
    korban = tulis_helper(d, 'korban.py', '''
import sys, time
sys.path.insert(0, sys.argv[2])
import dbdb
db = dbdb.connect(sys.argv[1])
db['jangkar'] = 'aman'
db.commit()
for i in range(50):
    db[f'sampah{i}'] = 'belum-commit'
print('SIAP', flush=True)
time.sleep(60)
''')
    proc = subprocess.Popen([sys.executable, korban, path, PROYEK],
                            stdout=subprocess.PIPE, text=True)
    baris = proc.stdout.readline()
    assert 'SIAP' in baris, baris
    proc.send_signal(signal.SIGKILL)
    proc.wait()
    pemeriksa = tulis_helper(d, 'pemeriksa.py', '''
import sys
sys.path.insert(0, sys.argv[2])
import dbdb
db = dbdb.connect(sys.argv[1])
ok_jan = db['jangkar'] == 'aman' if 'jangkar' in db else False
sampah = sum(1 for i in range(50) if f'sampah{i}' in db)
db['sesudah'] = 'kunci-bebas'
db.commit()
print(f'jangkar={ok_jan} sampah={sampah} tulis_baru={db["sesudah"]}')
''')
    r = jalankan(pemeriksa, path, PROYEK, timeout=30)
    cek('kill -9: commit terakhir utuh, kerja belum-commit hilang, kunci bebas lagi',
        'jangkar=True sampah=0 tulis_baru=kunci-bebas' in r.stdout,
        r.stdout.strip() or r.stderr.strip()[-200:])

    # ---------- 2. Pembaca tanpa kunci di tengah hujan commit ----------
    path2 = os.path.join(d, 'hujan.db')
    db = dbdb.connect(path2)
    db['penghitung'] = '0'
    db['pasangan'] = '0'
    db.commit()
    db.close()
    penulis = tulis_helper(d, 'penulis.py', '''
import sys, time
sys.path.insert(0, sys.argv[2])
import dbdb
db = dbdb.connect(sys.argv[1])
for i in range(1, 60):
    db['penghitung'] = str(i)
    db['pasangan'] = str(i)
    db.commit()
    time.sleep(0.005)
''')
    pw = subprocess.Popen([sys.executable, penulis, path2, PROYEK])
    st = Storage(open(path2, 'r+b'))
    tree = BinaryTree(st)
    generasi_terlihat = set()
    konsisten = True
    batas = time.time() + 60
    while time.time() < batas:
        tree._refresh_tree_ref()
        akar = tree._follow(tree._tree_ref)
        a = tree._get(akar, 'penghitung')
        b = tree._get(akar, 'pasangan')
        if a != b:
            konsisten = False
            break
        generasi_terlihat.add(a)
        if a == '59':
            break
    pw.wait(timeout=30)
    st.close()
    cek('pembaca tanpa kunci: tak pernah melihat pasangan yang sobek',
        konsisten and '59' in generasi_terlihat,
        f'{len(generasi_terlihat)} generasi teramati, semua konsisten')

    # ---------- 3. Akar lama yang dipegang = bacaan basi yang sah ----------
    path3 = os.path.join(d, 'basi.db')
    db = dbdb.connect(path3)
    db['versi'] = 'gen-0'
    db.commit()
    akar_gen0 = db._storage.get_root_address()
    db.close()
    pengubah = tulis_helper(d, 'pengubah.py', '''
import sys
sys.path.insert(0, sys.argv[2])
import dbdb
db = dbdb.connect(sys.argv[1])
for i in range(1, 6):
    db['versi'] = f'gen-{i}'
    db.commit()
''')
    r = jalankan(pengubah, path3, PROYEK)
    st3 = Storage(open(path3, 'r+b'))
    tree3 = BinaryTree(st3)
    lama = tree3._get(tree3._follow(BinaryNodeRef(address=akar_gen0)), 'versi')
    tree3._refresh_tree_ref()
    kini = tree3._get(tree3._follow(tree3._tree_ref), 'versi')
    st3.close()
    cek('akar lama tetap membaca gen-0 selagi akar kini di gen-5',
        lama == 'gen-0' and kini == 'gen-5', f'lama={lama} kini={kini}')

    # ---------- 4. Harga append-only: berkas hanya tumbuh ----------
    path4 = os.path.join(d, 'tumbuh.db')
    db = dbdb.connect(path4)
    ukuran = []
    for i in range(50):
        db['satu'] = f'v{i}'
        db.commit()
        ukuran.append(os.path.getsize(path4))
    cek('50 commit pada 1 kunci: berkas tumbuh monoton, isi tetap 1 kunci',
        ukuran == sorted(ukuran) and len(set(ukuran)) == 50 and len(db) == 1,
        f'{ukuran[0]} -> {ukuran[-1]} byte (tanpa vacuum, sesuai desain bab)')
    db.close()

print()
if gagal:
    print('GAGAL:', ', '.join(gagal))
    sys.exit(1)
print('SEMUA PASS — Irisan 4 terbukti: commit selamat dari kill -9, pembaca tak pernah sobek.')
