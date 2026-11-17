# Build Your Own Database — DBDB dengan Python

Database kunci/nilai persisten yang dibangun ulang dari nol mengikuti bab **"DBDB: Dog Bed Database"** karya **Taavi Burns** dalam buku *500 Lines or Less* (Architecture of Open Source Applications) — entri kategori **Database** di repo [codecrafters-io/build-your-own-x](https://github.com/codecrafters-io/build-your-own-x).

Panduan: http://aosabook.org/en/500L/dbdb-dog-bed-database.html

## Cara pakai

```python
import dbdb

db = dbdb.connect('tokoku.db')
db['anjing'] = 'kasur empuk'
db['kucing'] = 'menara garuk'
db.commit()              # tidak ada yang permanen sebelum ini

print(db['anjing'])      # kasur empuk
print(len(db))           # 2
del db['kucing']
db.commit()
db.close()
```

```console
$ python3 -m dbdb.tool tokoku.db set warna biru
$ python3 -m dbdb.tool tokoku.db get warna
biru
```

Kode keluar CLI mengikuti bab panduan: `0` OK, `1` argumen salah, `2` kata kerja tak dikenal, `3` kunci tidak ada.

## Cara kerja

Tiga lapisan, satu gagasan besar: **berkas tidak pernah ditimpa**.

| Berkas | Isi |
|---|---|
| `dbdb/physical.py` | `Storage` — catatan ditempel di ujung berkas (awalan panjang 8 byte); 8 byte pertama (superblock) memegang alamat akar dan hanya berubah lewat `commit_root_address`, yang meng-fsync data *sebelum* memindahkan alamat akar |
| `dbdb/logical.py` | `ValueRef` — rujukan malas (nilai di memori *atau* alamat di disk); `LogicalBase` — tata cara get/set/delete/commit |
| `dbdb/binary_tree.py` | Pohon biner immutable: sisip/hapus menyalin hanya jalur yang disentuh; akar lama = snapshot abadi |
| `dbdb/interface.py` | `DBDB` ala `dict` + `connect()` yang tak pernah memotong berkas lama |
| `dbdb/tool.py` | CLI `get`/`set`/`delete`, satu perintah = satu transaksi |

Karena commit hanyalah "tulis simpul-simpul baru, lalu pindahkan satu alamat 8 byte yang sejajar sektor", commit bersifat atomik dan durable; pembaca tidak pernah mengunci dan tidak pernah melihat keadaan separuh jadi (paling buruk: generasi sebelumnya yang utuh). Penulis yang mati di tengah jalan meninggalkan kunci yang terlepas sendiri dan pekerjaan yang tak pernah ter-commit — hilang tanpa jejak, persis seperti seharusnya.

## Uji

Satu berkas uji per irisan pembangunan, semuanya hijau:

```console
$ python3 uji_irisan1.py   # append-only dibuktikan dari byte mentah berkas
$ python3 uji_irisan2.py   # diferensial 600 operasi vs dict + snapshot akar lama
$ python3 uji_irisan3.py   # API dict + CLI antar-proses dan kode keluarnya
$ python3 uji_irisan4.py   # penulis dibunuh -9; pembaca di tengah 60 commit
```

`CATATAN.md` berisi satu halaman catatan belajar per irisan — termasuk temuan terbesar seri ini: penyangga baca Python menyajikan alamat akar yang basi antar-proses, ditangkap oleh baterai konkurensi dan diperbaiki dengan `os.pread`.

## Penyimpangan dari bab panduan (terbuka)

- Kunci berkas memakai `fcntl.flock` dari pustaka standar sebagai pengganti paket pihak ketiga `portalocker` — semantik yang sama di Linux, termasuk terlepas otomatis saat proses pemegangnya mati.
- Semua bacaan `Storage` lewat `os.pread` (lihat di atas); bab aslinya membaca lewat objek berkas biasa.
- Pohonnya sengaja **tidak seimbang**, persis seperti babnya — sisipan terurut merosotkannya menjadi daftar berantai. Database sungguhan memakai B-tree; di sini kesederhanaan adalah tujuannya. Berkas juga hanya tumbuh: tidak ada vacuum.

## Kredit

Rancangan dan struktur bab oleh Taavi Burns, *500 Lines or Less* (CC BY 4.0). Ini adalah pembangunan ulang untuk belajar dengan pengujian diferensial dan baterai durabilitas/konkurensi sendiri; bukan salinan kode babnya.
