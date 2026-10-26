import os
import time

import cv2
import pygame

from modules.gestures import (
    finger_ratios,
    pinch_metrics,
    thumb_openness,
    thumb_vertical,
)
from modules.hand_detector import HandDetector
from modules.stabilizer import LabelVoter

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ASSETS = os.path.join(BASE_DIR, "assets")

# Tabel gerakan -> (label di layar, file suara)
# Untuk menambah gerakan baru, cukup tambah satu baris di sini
# (dan satu aturan deteksi di modules/gestures.py).
GESTURES = {
    "halo": ("HALO", "halo.mp3"),
    "maaf": ("MAAF", "maaf.mp3"),
    "tolong": ("TOLONG", "tolong.mp3"),
    "terima_kasih": ("TERIMA KASIH", "terima_kasih.mp3"),
    "ya": ("YA", "ya.mp3"),
    "tidak": ("TIDAK", "tidak.mp3"),
    "saya": ("SAYA", "saya.mp3"),
    "kamu": ("KAMU", "kamu.mp3"),
    "makan": ("MAKAN", "makan.mp3"),
    "minum": ("MINUM", "minum.mp3"),
    "janji": ("JANJI", "janji.mp3"),
    "sakit": ("SAKIT", "sakit.mp3"),
}

# Pemungutan suara: sebuah gerakan baru dianggap sah kalau menang di
# VOTE_MIN dari VOTE_WINDOW frame terakhir (sekitar 0,25 detik di 30 FPS).
# Satu-dua frame yang salah baca tidak lagi memicu suara yang salah.
# Naikkan VOTE_MIN (maksimal VOTE_WINDOW) kalau masih terlalu sensitif.
VOTE_WINDOW = 10
VOTE_MIN = 7

# Pengaturan kamera
CAMERA_INDEX = 0
FRAME_WIDTH = 640
FRAME_HEIGHT = 480
SHOW_FPS = True
SHOW_DEBUG = False  # tekan D saat program jalan untuk menampilkan/menyembunyikan

window_name = "Hand Tracking AI"


def open_camera():
    """Membuka kamera dengan pengaturan yang ringan dan rendah latensi."""
    cap = None

    # Di Windows, backend DirectShow biasanya lebih cepat dibuka
    if os.name == "nt":
        cap = cv2.VideoCapture(CAMERA_INDEX, cv2.CAP_DSHOW)

    if cap is None or not cap.isOpened():
        cap = cv2.VideoCapture(CAMERA_INDEX)

    if not cap.isOpened():
        return None

    # MJPG membuat banyak webcam bisa mencapai 30 FPS
    cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*"MJPG"))
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, FRAME_WIDTH)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, FRAME_HEIGHT)
    cap.set(cv2.CAP_PROP_FPS, 30)
    # Buffer kecil supaya tidak ada gambar lama yang menumpuk (delay)
    cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)

    return cap


def draw_debug(frame, hand, gesture):
    """Menampilkan angka mentah yang dipakai untuk mengenali gerakan.

    Berguna untuk menyetel angka di modules/gestures.py. Rasio jari:
    > 1.10 dianggap lurus, < 0.95 dianggap tertekuk.
    """
    lines = [f"mentah: {gesture}"]

    if hand is not None:
        ratios = finger_ratios(hand)
        up, down = thumb_vertical(hand)
        spread, reach = pinch_metrics(hand)
        letters = ["T", "M", "R", "K"]  # telunjuk, tengah, manis, kelingking
        lines += [
            "jari  " + "  ".join(f"{l} {r:.2f}" for l, r in zip(letters, ratios)),
            f"jempol keluar {thumb_openness(hand):.2f}",
            f"jempol atas {up:.2f}  bawah {down:.2f}",
            f"makan spread {spread:.2f}  reach {reach:.2f}",
        ]

    for i, text in enumerate(lines):
        y = 125 + i * 24
        cv2.putText(frame, text, (50, y), cv2.FONT_HERSHEY_SIMPLEX,
                    0.6, (0, 0, 0), 4)
        cv2.putText(frame, text, (50, y), cv2.FONT_HERSHEY_SIMPLEX,
                    0.6, (255, 255, 255), 1)


def load_sounds():
    sounds = {}
    for name, (_, filename) in GESTURES.items():
        path = os.path.join(ASSETS, filename)
        if os.path.exists(path):
            sounds[name] = pygame.mixer.Sound(path)
        else:
            print(f"Peringatan: {filename} tidak ditemukan di assets/. "
                  f"Jalankan: python generate_sounds.py")
    return sounds


def main():
    cap = open_camera()

    if cap is None:
        print("Kamera tidak dapat dibuka!")
        return

    print("Kamera berhasil dibuka.")
    print("Tekan Q, ESC, atau klik tombol X untuk keluar. Tekan D untuk angka debug.")

    pygame.mixer.init()
    sounds = load_sounds()
    # Semua suara lewat SATU channel: memutar suara baru otomatis
    # menghentikan suara lama, jadi tidak pernah bertumpuk.
    channel = pygame.mixer.Channel(0)
    detector = HandDetector()
    voter = LabelVoter(VOTE_WINDOW, VOTE_MIN)

    cv2.namedWindow(window_name)

    active = None          # gerakan yang sudah dikonfirmasi
    show_debug = SHOW_DEBUG

    fps = 0.0
    last_time = time.monotonic()

    while True:

        success, frame = cap.read()

        if not success:
            print("Gagal membaca frame.")
            break

        # Cerminkan gambar supaya terasa seperti bercermin
        frame = cv2.flip(frame, 1)

        frame = detector.findHands(frame)
        gesture = detector.getGesture()

        # Konfirmasi gerakan lewat pemungutan suara beberapa frame terakhir
        confirmed = voter.update(gesture)

        if confirmed != active:
            active = confirmed
            if active in sounds:
                channel.play(sounds[active])  # menggantikan suara yang sedang jalan

        # Tampilkan label gerakan yang aktif
        if active in GESTURES:
            cv2.putText(
                frame,
                GESTURES[active][0],
                (50, 80),
                cv2.FONT_HERSHEY_SIMPLEX,
                1.6,
                (255, 255, 255),
                3
            )

        if show_debug:
            draw_debug(frame, detector.hand, gesture)

        # Hitung dan tampilkan FPS (dihaluskan)
        now = time.monotonic()
        dt = now - last_time
        last_time = now
        if dt > 0:
            fps = 0.9 * fps + 0.1 * (1.0 / dt) if fps else 1.0 / dt

        if SHOW_FPS:
            cv2.putText(
                frame,
                f"FPS {fps:.0f}",
                (10, frame.shape[0] - 15),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.7,
                (255, 255, 255),
                2
            )

        cv2.imshow(window_name, frame)

        key = cv2.waitKey(1) & 0xFF

        if key == ord("q"):
            print("Keluar dengan tombol Q.")
            break

        if key == ord("d"):
            show_debug = not show_debug

        if key == 27:
            print("Keluar dengan tombol ESC.")
            break

        # Cek apakah tombol X ditekan
        try:
            if cv2.getWindowProperty(
                window_name,
                cv2.WND_PROP_VISIBLE
            ) < 1:
                print("Window ditutup.")
                break
        except Exception:
            pass

    cap.release()
    cv2.destroyAllWindows()
    pygame.mixer.quit()

    print("Program selesai.")


if __name__ == "__main__":
    main()
