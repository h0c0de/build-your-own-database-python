# Catatan — Build Your Own Database (DBDB)

Satu halaman per irisan: konsep inti + temuan saat membangun.
Panduan: Taavi Burns, *DBDB: Dog Bed Database* (500 Lines or Less).

## Irisan 1 — Lapisan fisik: Storage (18 Nov 2026, terverifikasi)

**Yang dibangun:** `dbdb/physical.py` — berkas yang tidak pernah ditimpa. Setiap catatan ditempel di ujung berkas dengan awalan panjang 8 byte; alamatnya (posisi byte) menjadi namanya yang kekal. Satu-satunya byte yang boleh berubah adalah superblock — 8 byte pertama pemegang alamat akar — dan ia hanya berubah lewat `commit_root_address`, yang urutannya adalah jaminannya sendiri: kunci → flush + fsync semua data → tulis alamat akar baru → flush + fsync lagi. Kunci berkas memakai `fcntl.flock` dari stdlib sebagai pengganti `portalocker` pihak ketiga di bab aslinya; semantiknya sama di Linux, termasuk yang terpenting: kunci terlepas sendiri bila proses pemegangnya mati.

**Bukti jalan:** `uji_irisan1.py` — semua hijau, dan klaim append-only dibuktikan dari isi berkas mentahnya, bukan dari perilaku kelas: sesudah tulis tambahan + commit, seluruh byte lama sesudah superblock adalah awalan persis dari berkas baru. Alamat naik monoton, baca-kembali cocok untuk muatan kosong sampai 100 KB, alamat akar bertahan melewati buka-ulang, dan kunci terbukti antar-proses (proses anak tertahan `LOCK_NB` selagi kita memegang kunci, dan mendapatkannya sesudah kita melepas).

**Temuan:** jaminan atomik di sini tidak datang dari kode yang rumit, melainkan dari *penempatan*: alamat akar tinggal di byte 0 — selalu sejajar sektor berapa pun ukuran sektornya — sehingga penulisannya adalah penulisan satu sektor yang oleh perangkat keras dijamin atomik. Seluruh rancangan lapisan di atasnya (Irisan 2) berdiri di atas satu fakta kecil itu.

## Irisan 2 — Lapisan logis + pohon biner immutable (18 Nov 2026, terverifikasi)

**Yang dibangun:** `dbdb/logical.py` (`ValueRef` — rujukan malas yang memegang nilai di memori *atau* alamat di disk dan hanya menyeberang bila diikuti; `LogicalBase` — tata cara get/set/delete/commit yang sama untuk struktur apa pun) dan `dbdb/binary_tree.py` (pohon biner yang simpulnya tak pernah berubah: sisip dan hapus membangun simpul baru hanya di sepanjang jalur yang disentuh, subpohon lain dipakai bersama apa adanya).

**Bukti jalan:** `uji_irisan2.py` — semua hijau. Diferensial melawan `dict` Python lewat 600 operasi acak (sisip, timpa, hapus yang ada dan yang tidak ada, baca) berakhir identik. Dua bukti khas immutable: akar lama yang disimpan sebelum commit baru tetap membaca nilai generasi lama dan tidak melihat kunci baru — snapshot abadi tanpa menyalin apa pun; dan menyisipkan 1 kunci ke pohon berisi 1000 kunci hanya menumbuhkan berkas **756 byte dari 114.673** (0,66%) — tepat sebesar jalur akar-ke-daun, bukan sebesar pohonnya. Perubahan yang belum di-commit juga terbukti tak terlihat oleh koneksi lain, dan muncul sesudah commit.

**Temuan:** kemalasan `ValueRef` adalah yang membuat janji "data lebih besar dari RAM" di bab ini masuk akal: mengikuti satu kunci hanya memuat simpul-simpul di jalurnya, dan sisipan hanya menulis ulang jalur itu. Kelemahan yang diakui babnya dan kami warisi apa adanya: pohonnya tidak seimbang — kunci yang disisipkan terurut akan merosotkannya menjadi daftar berantai (uji kami mengacak urutan sisip justru karena itu); database sungguhan menjawabnya dengan B-tree.

## Irisan 3 — Antarmuka + tool CLI (18 Nov 2026, terverifikasi)

**Yang dibangun:** `dbdb/interface.py` — `DBDB` yang bertingkah seperti `dict` Python yang kebetulan tinggal di disk (`db[k]=v`, `db[k]`, `del`, `in`, `len`), dengan satu perbedaan besar dari dict: tidak ada yang permanen sampai `commit()` dipanggil. `connect()` membuka berkas lama dengan mode `r+b` — tidak pernah memotong — dan hanya membuat berkas bila belum ada. Kunci dan nilai wajib `str` (selain itu `TypeError`). `dbdb/tool.py` menambahkan CLI-nya (`get`/`set`/`delete`, satu perintah = satu transaksi) dengan kode keluar persis bab panduan: 0 OK, 1 argumen salah, 2 kata kerja tak dikenal, 3 kunci tidak ada.

**Bukti jalan:** `uji_irisan3.py` — semua hijau, dan CLI diuji sebagai proses sungguhan lewat `python3 -m dbdb.tool`, bukan dipanggil di dalam proses: nilai yang di-commit satu proses terbaca proses lain, dan keempat kode keluar terbukti di batas proses. `connect()` + baca saja terbukti tidak mengubah satu byte pun berkas yang sudah ada (dibandingkan byte-per-byte).

**Temuan:** bagian tersulit irisan ini bukan kodenya melainkan *kontraknya* — pemisahan "terlihat olehku" dari "permanen bagi semua orang" lewat commit eksplisit adalah seluruh alasan database ini terasa seperti database dan bukan seperti dict yang diserialkan. Dict tidak punya kata untuk "belum"; di sini kata itu adalah commit, dan Irisan 4 akan menguji apa yang terjadi bila kata itu tidak pernah terucap karena prosesnya dibunuh di tengah jalan.

## Irisan 4 — Baterai durabilitas & konkurensi (18 Nov 2026, terverifikasi)

**Yang diuji:** janji-janji bab ini dengan cara paling tidak ramah. Penulis dibunuh `-9` sesudah menyiapkan 50 kunci yang belum di-commit: database terbuka persis di commit terakhirnya (`jangkar` utuh, 0 dari 50 kunci sampah terlihat), dan kunci berkasnya bebas lagi seketika — proses baru langsung bisa menulis, karena `flock` terlepas bersama kematian pemegangnya. Pembaca tanpa kunci membaca sepasang kunci yang selalu berubah bersamaan di tengah 60 commit berturut-turut: ia mengamati 55 generasi dan **tidak pernah** melihat pasangan yang sobek — setiap bacaan adalah satu snapshot utuh, karena ia berlabuh pada satu alamat akar. Akar lama yang dipegang terus membaca gen-0 selagi dunia mencapai gen-5 (bacaan basi adalah semantik yang disengaja, bukan kerusakan). Dan harganya dicatat apa adanya: 50 commit pada 1 kunci yang sama menumbuhkan berkas 95 → 4.445 byte tanpa satu byte pun direklamasi — append-only tidak punya vacuum.

**Temuan terbesar seri ini — ditangkap baterai, bukan dibaca dari kode:** versi pertama baterai ini *gagal* pada uji pembaca. Pembaca membeku di generasi pertama selamanya. Akar masalahnya bukan di rancangan DBDB melainkan di penyangga baca Python: objek berkas berpenyangga menganggap `seek` di dalam jendela yang sudah terbaca tidak memerlukan syscall, sehingga alamat akar yang ditulis *proses lain* tidak pernah terlihat — database kami benar, tetapi matanya menyajikan byte basi. Perbaikannya: semua bacaan di `Storage` kini lewat `os.pread`, yang selalu bertanya ke sistem operasi. Pelajarannya persis pelajaran build kedelapan terbalik: di sana pipa pelaporan yang rusak membuat sukses terlihat gagal; di sini lapisan penyangga yang "membantu" membuat data basi terlihat segar. Antarmuka yang kau baca adalah bagian dari kebenaran yang kau dapat.
