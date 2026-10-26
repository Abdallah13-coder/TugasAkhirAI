# Hand Tracking AI

Mendeteksi gerakan tangan lewat kamera dan memutar suara untuk tiap gerakan.

> Gerakan di bawah ini **karangan sendiri** (custom), bukan bahasa isyarat
> resmi seperti BISINDO atau SIBI.

| Kata | Cara | Suara |
|---|---|---|
| Halo | Empat jari lurus (telapak terbuka) | "Halo, perkenalkan" |
| Maaf | Tengah + manis + kelingking lurus, telunjuk ditekuk | "Maaf" |
| Tolong | Kepalan | "Tolong saya" |
| Terima kasih | Peace: telunjuk + tengah | "Terima kasih" |
| Ya | Kepalan, jempol lurus ke atas | "Ya" |
| Tidak | Kepalan, jempol lurus ke bawah | "Tidak" |
| Saya | Telunjuk saja | "Saya" |
| Kamu | Telunjuk + tengah + manis | "Kamu" |
| Makan | Semua ujung jari dikumpulkan jadi satu (seperti menyuap makanan) | "Saya mau makan" |
| Minum | Jempol keluar + kelingking (seperti 🤙) | "Saya mau minum" |
| Janji | Kelingking saja, jempol rapat dekat telapak | "Saya janji" |
| Sakit | Telunjuk + kelingking | "Saya sakit" |

Tips:
- **Jempol bebas** di semua gerakan, kecuali Ya/Tidak (arah jempol), Makan,
  dan **Minum vs Janji** (jempol keluar atau rapat). Jempol adalah titik paling
  goyah di MediaPipe, jadi ukurannya memakai jarak yang tegas dan batas ganda.
- **Minum vs Janji:** keduanya kelingking naik. Beda di jempol: buka lebar ke
  samping untuk Minum, rapatkan ke telapak untuk Janji.
- **Ya dan Tidak** dibedakan oleh arah jempol di layar kamera, jadi jangan
  memutar tangan. Jempol yang menyamping atau miring dianggap Tolong.
- **Makan:** ujung kelima jari harus benar-benar berdekatan dan jari agak
  melengkung ke depan, bukan dirapatkan ke telapak (itu jadi kepalan).
- Telapak menghadap kamera, jangan miring ke samping, supaya kelingking tidak
  tertutup jari manis. Cahaya terang dan latar polos membantu.
- Tahan gerakan sekitar 0,25 detik sampai labelnya muncul. Saat berpindah
  gerakan, suara lama otomatis berhenti dan diganti suara baru (tidak
  bertumpuk).

## Instalasi

Disarankan memakai virtual environment.

Windows (PowerShell):
```
python -m venv venv
venv\Scripts\activate
pip install -r requirement.txt
python generate_sounds.py
python main.py
```

Linux / Mac:
```
python3 -m venv venv
source venv/bin/activate
pip install -r requirement.txt
python generate_sounds.py
python main.py
```

`generate_sounds.py` membuat file suara memakai suara wanita Indonesia
(`id-ID-GadisNeural`) dan butuh koneksi internet. Ubah teks ucapan di dalam
file itu, lalu jalankan ulang untuk mengganti suaranya.

Tekan `Q`, `ESC`, atau tombol X untuk keluar, dan `D` untuk angka debug.

## Pengaturan kehalusan dan kecepatan

Gerakan titik tangan dihaluskan dengan One Euro Filter. Atur di
`HandDetector(...)` pada `modules/hand_detector.py`:

| Parameter | Fungsi |
|---|---|
| `smooth_min_cutoff` (bawaan 1.5) | Makin kecil, makin halus saat tangan diam, tapi bisa terasa tertinggal |
| `smooth_beta` (bawaan 6.0) | Makin besar, makin responsif saat tangan bergerak cepat |
| `smooth=False` | Mematikan penghalusan sepenuhnya |

Pengaturan kamera (resolusi, FPS tampil) ada di bagian atas `main.py`.
Kalau FPS rendah, coba turunkan `FRAME_WIDTH` dan `FRAME_HEIGHT`.

## Kestabilan pembacaan

- **Batas ganda tiap jari:** jari baru dianggap lurus kalau jelas lurus dan
  baru dianggap tertekuk kalau jelas tertekuk, jadi jari yang goyah tidak
  bolak-balik berganti status.
- **Pemungutan suara antar frame** (`modules/stabilizer.py`): sebuah gerakan
  baru sah kalau menang di `VOTE_MIN` dari `VOTE_WINDOW` frame terakhir
  (pengaturan di `main.py`). Satu-dua frame salah baca diabaikan.
- **Satu channel suara:** semua suara diputar lewat satu channel, jadi suara
  baru otomatis menggantikan suara lama.

## Melihat angka di layar (debug)

Tekan **D** saat program berjalan untuk menampilkan angka mentah: rasio tiap
jari (T = telunjuk, M = tengah, R = manis, K = kelingking; di atas 1.10 dianggap
lurus, di bawah 0.95 dianggap tertekuk), seberapa keluar jempol, arah jempol,
dan angka gerakan Makan. Tekan D lagi untuk menyembunyikan. Angka ini
membantu menentukan angka mana di `modules/gestures.py` yang perlu disetel.

## Menambah gerakan baru

Untuk gerakan berpola jari biasa:

1. Tambahkan satu pola jari (harus unik) di `GESTURE_PATTERNS` pada
   `modules/gestures.py`. Format: (telunjuk, tengah, manis, kelingking),
   1 = lurus, 0 = tertekuk. Jempol bebas.
2. Tambahkan satu baris di tabel `GESTURES` pada `main.py` dan satu teks di
   `generate_sounds.py`, lalu jalankan ulang `python generate_sounds.py`.

Gerakan khusus (Ya/Tidak berdasarkan arah jempol, Minum berdasarkan jempol
keluar, dan Makan berdasarkan ujung jari berkumpul) punya aturan sendiri di
`GestureRecognizer.update()`.

## Menyetel kalau gerakan sulit terbaca

Angka di bagian atas `modules/gestures.py` dan `main.py`:

| Masalah | Yang diubah |
|---|---|
| Satu jari sering salah terbaca lurus/tertekuk | `FINGER_ON` (naikkan) / `FINGER_OFF` (turunkan) di `gestures.py` |
| Tolong (kepalan) sering terbaca Ya/Tidak | `THUMB_VERT_ON` (naikkan) |
| Ya / Tidak sulit terbaca | `THUMB_VERT_ON` (turunkan) |
| Minum terbaca Janji | `THUMB_OUT_ON` (turunkan) |
| Janji terbaca Minum | `THUMB_OUT_ON` (naikkan) |
| Makan sulit terbaca | `PINCH_MIN_REACH` (turunkan) atau `PINCH_MAX_SPREAD` (naikkan) |
| Makan malah terbaca saat kepalan | `PINCH_MIN_REACH` (naikkan) |
| Masih sering salah bunyi | `VOTE_MIN` di `main.py` (naikkan, maksimal `VOTE_WINDOW`) |
| Suara terasa telat | `VOTE_MIN` (turunkan) |

## Struktur

```
main.py                   program utama
generate_sounds.py        pembuat file suara (TTS)
modules/gestures.py       logika pengenalan gerakan (pola jari, ya/tidak, makan)
modules/smoothing.py      penghalus landmark (One Euro Filter)
modules/hand_detector.py  pembungkus MediaPipe
modules/stabilizer.py     pemungutan suara antar frame
assets/                   model (hand_landmarker.task) dan file suara
```
