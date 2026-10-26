"""Logika pengenalan gerakan tangan.

File ini sengaja tidak bergantung pada MediaPipe, jadi mudah diuji.
Setiap "hand" adalah list 21 landmark dengan atribut .x dan .y
(nilai ternormalisasi 0..1, titik (0, 0) ada di pojok kiri atas).

Indeks landmark MediaPipe:
    0 pergelangan tangan
    1-4 jempol (CMC, MCP, IP, TIP)
    5-8 telunjuk (MCP, PIP, DIP, TIP)
    9-12 jari tengah
    13-16 jari manis
    17-20 kelingking

CATATAN: gerakan di bawah ini adalah gerakan KARANGAN sendiri (custom),
bukan bahasa isyarat resmi seperti BISINDO atau SIBI.

Supaya tidak gampang "berkedip" antar gerakan:
  * Jempol TIDAK ikut menentukan gerakan (jempol bebas), kecuali untuk
    Ya/Tidak (arah jempol), Makan (ujung jari berkumpul), dan Minum vs
    Janji (jempol keluar atau rapat). Jempol adalah titik paling goyah di
    MediaPipe, jadi ukurannya memakai jarak yang tegas dan batas ganda.
  * Status tiap jari memakai batas ganda (hysteresis): jari baru dianggap
    lurus kalau JELAS lurus, dan baru dianggap tertekuk kalau JELAS
    tertekuk. Di zona abu-abu, statusnya tetap seperti frame sebelumnya.

Urutan pengecekan di GestureRecognizer.update():
    1. "makan"  : semua ujung jari dikumpulkan (pose mencubit)
    2. kepalan  : jempol ke atas = "ya", ke bawah = "tidak", selain itu "tolong"
    3. kelingking saja : jempol keluar = "minum", jempol rapat = "janji"
    4. pola empat jari (GESTURE_PATTERNS)
"""

import math

# --- Status jari: rasio jarak ujung jari / sendi tengah ke pergelangan ---
# Jari lurus biasanya > 1.25, tertekuk penuh < 0.9.
# Rasio >= FINGER_ON  -> jari dianggap lurus
# Rasio <= FINGER_OFF -> jari dianggap tertekuk
# Di antara keduanya status tidak berubah.
FINGER_ON = 1.10
FINGER_OFF = 0.95

# --- Ya / Tidak: seberapa tegak jempol (dibanding ukuran tangan) ---
# Naikkan kalau kepalan (Tolong) sering salah terbaca Ya/Tidak; turunkan
# kalau jempol atas/bawah sulit terbaca.
THUMB_VERT_ON = 0.5
THUMB_VERT_OFF = 0.3

# --- Minum vs Janji: seberapa jauh jempol dari telapak ---
# Diukur: jarak ujung jempol ke pangkal kelingking / ukuran tangan.
# Contoh terukur: jempol keluar (seperti 🤙) = 1.41, jempol dekat telapak
# = 0.66. Jempol dianggap keluar kalau >= THUMB_OUT_ON, dan baru dianggap
# rapat kalau <= THUMB_OUT_OFF.
# Minum sering terbaca Janji -> turunkan THUMB_OUT_ON.
# Janji sering terbaca Minum -> naikkan THUMB_OUT_ON.
THUMB_OUT_ON = 1.05
THUMB_OUT_OFF = 0.85

# --- Makan: semua ujung jari dikumpulkan ---
# spread = jarak terjauh antar ujung jari / ukuran tangan (makin kecil makin rapat)
# reach  = rata-rata jarak ujung jari ke pergelangan / ukuran tangan
#          (membedakan dari kepalan, yang ujung jarinya dekat ke telapak)
PINCH_MAX_SPREAD = 0.5       # mulai terbaca makan kalau spread <= ini
PINCH_MIN_REACH = 1.15       # ...dan reach >= ini
PINCH_RELEASE_SPREAD = 0.65  # baru lepas dari makan kalau spread > ini
PINCH_RELEASE_REACH = 1.0    # ...atau reach < ini

# Urutan pola: (telunjuk, tengah, manis, kelingking). 1 = lurus, 0 = tertekuk.
# Jempol bebas. Setiap pola harus unik.
# Untuk menambah gerakan baru, cukup tambah satu baris di sini
# (lalu daftarkan di GESTURES pada main.py).
GESTURE_PATTERNS = {
    "halo":         (1, 1, 1, 1),  # empat jari lurus (telapak terbuka)
    "maaf":         (0, 1, 1, 1),  # tengah + manis + kelingking
    "tolong":       (0, 0, 0, 0),  # kepalan (jempol atas/bawah = ya/tidak)
    "terima_kasih": (1, 1, 0, 0),  # peace
    "saya":         (1, 0, 0, 0),  # telunjuk saja
    "kamu":         (1, 1, 1, 0),  # telunjuk + tengah + manis
    "janji":        (0, 0, 0, 1),  # kelingking saja, jempol rapat
                                   # (jempol keluar = "minum", lihat PINKY_ONLY)
    "sakit":        (1, 0, 0, 1),  # telunjuk + kelingking
}

FIST = (0, 0, 0, 0)
PINKY_ONLY = (0, 0, 0, 1)

_PATTERN_TO_NAME = {pattern: name for name, pattern in GESTURE_PATTERNS.items()}

if len(_PATTERN_TO_NAME) != len(GESTURE_PATTERNS):
    raise ValueError("Ada pola gerakan ganda di GESTURE_PATTERNS.")

# (nama, indeks ujung, indeks sendi tengah)
FINGERS = (
    ("index", 8, 6),
    ("middle", 12, 10),
    ("ring", 16, 14),
    ("pinky", 20, 18),
)

FINGERTIPS = (4, 8, 12, 16, 20)


def _dist(a, b):
    return math.hypot(a.x - b.x, a.y - b.y)


def _hand_size(hand):
    """Ukuran tangan: pergelangan -> pangkal jari tengah."""
    return max(_dist(hand[0], hand[9]), 1e-6)


def finger_ratios(hand):
    """Rasio (jarak ujung ke pergelangan) / (jarak sendi tengah ke pergelangan).

    Memakai jarak ke pergelangan, bukan posisi Y, sehingga tetap akurat
    walau tangan miring atau terbalik. > 1 berarti lurus, < 1 tertekuk.
    """
    wrist = hand[0]
    return [
        _dist(hand[tip], wrist) / max(_dist(hand[pip], wrist), 1e-6)
        for _, tip, pip in FINGERS
    ]


def pinch_metrics(hand):
    """Mengembalikan (spread, reach), keduanya dibagi ukuran tangan."""
    size = _hand_size(hand)
    tips = [hand[i] for i in FINGERTIPS]

    spread = max(
        _dist(a, b)
        for i, a in enumerate(tips)
        for b in tips[i + 1:]
    )
    reach = sum(_dist(t, hand[0]) for t in tips) / len(tips)

    return spread / size, reach / size


def thumb_openness(hand):
    """Jarak ujung jempol ke pangkal kelingking, dibanding ukuran tangan.

    Besar (>1) kalau jempol keluar, kecil (<0.8) kalau dekat telapak.
    """
    return _dist(hand[4], hand[17]) / _hand_size(hand)


def thumb_vertical(hand):
    """Mengembalikan (atas, bawah): seberapa tegak jempol, dibanding ukuran tangan.

    Salah satunya 0 (atau keduanya) kalau jempol menyamping. Arah dihitung
    terhadap layar kamera, jadi tangan jangan diputar.
    """
    dx = hand[4].x - hand[2].x
    dy = hand[4].y - hand[2].y  # y membesar ke bawah

    if abs(dy) < abs(dx):
        return 0.0, 0.0

    size = _hand_size(hand)
    return max(-dy, 0.0) / size, max(dy, 0.0) / size


class _Latch:
    """Saklar dengan batas ganda: nyala kalau nilai >= on, mati kalau <= off."""

    def __init__(self, on, off):
        self.on = on
        self.off = off
        self.state = None

    def reset(self):
        self.state = None

    def update(self, value):
        if self.state is None:
            # Frame pertama: putuskan dari titik tengah kedua batas
            self.state = value >= (self.on + self.off) / 2
        elif self.state and value <= self.off:
            self.state = False
        elif not self.state and value >= self.on:
            self.state = True
        return self.state


class GestureRecognizer:
    """Pengenal gerakan yang mengingat status frame sebelumnya.

    Panggil update() sekali per frame, dan reset() saat tangan menghilang.
    """

    def __init__(self):
        self._fingers = [_Latch(FINGER_ON, FINGER_OFF) for _ in FINGERS]
        self._thumb_up = _Latch(THUMB_VERT_ON, THUMB_VERT_OFF)
        self._thumb_down = _Latch(THUMB_VERT_ON, THUMB_VERT_OFF)
        self._thumb_out = _Latch(THUMB_OUT_ON, THUMB_OUT_OFF)
        self._pinch = False

    def reset(self):
        for latch in self._fingers:
            latch.reset()
        self._thumb_up.reset()
        self._thumb_down.reset()
        self._thumb_out.reset()
        self._pinch = False

    def _update_pinch(self, hand):
        spread, reach = pinch_metrics(hand)

        if self._pinch:
            self._pinch = not (
                spread > PINCH_RELEASE_SPREAD or reach < PINCH_RELEASE_REACH
            )
        else:
            self._pinch = (
                spread <= PINCH_MAX_SPREAD and reach >= PINCH_MIN_REACH
            )
        return self._pinch

    def update(self, hand):
        """Mengembalikan nama gerakan (kunci GESTURES di main.py) atau None."""
        # Semua saklar selalu diperbarui tiap frame, supaya statusnya
        # tetap sinambung walau gerakan sedang berganti.
        states = tuple(
            int(latch.update(ratio))
            for latch, ratio in zip(self._fingers, finger_ratios(hand))
        )
        up, down = thumb_vertical(hand)
        thumb_up = self._thumb_up.update(up)
        thumb_down = self._thumb_down.update(down)
        thumb_out = self._thumb_out.update(thumb_openness(hand))
        pinch = self._update_pinch(hand)

        if pinch:
            return "makan"

        if states == FIST:
            if thumb_up:
                return "ya"
            if thumb_down:
                return "tidak"

        if states == PINKY_ONLY and thumb_out:
            return "minum"

        return _PATTERN_TO_NAME.get(states)


def classify(hand):
    """Versi tanpa ingatan (satu frame saja). Berguna untuk pengujian."""
    return GestureRecognizer().update(hand)
