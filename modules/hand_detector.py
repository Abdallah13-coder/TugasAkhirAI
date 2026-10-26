import os
import time

import cv2
import mediapipe as mp

from mediapipe.tasks import python
from mediapipe.tasks.python import vision

from modules.gestures import GestureRecognizer
from modules.smoothing import LandmarkSmoother

DEFAULT_MODEL = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "assets",
    "hand_landmarker.task",
)

# Hubungan antar landmark untuk menggambar kerangka tangan
CONNECTIONS = [
    (0, 1), (1, 2), (2, 3), (3, 4),
    (0, 5), (5, 6), (6, 7), (7, 8),
    (0, 9), (9, 10), (10, 11), (11, 12),
    (0, 13), (13, 14), (14, 15), (15, 16),
    (0, 17), (17, 18), (18, 19), (19, 20),
    (5, 9), (9, 13), (13, 17),
]


class HandDetector:

    def __init__(
        self,
        model_path=DEFAULT_MODEL,
        num_hands=1,
        min_hand_detection_confidence=0.5,
        min_hand_presence_confidence=0.5,
        min_tracking_confidence=0.5,
        smooth=True,
        smooth_min_cutoff=1.5,
        smooth_beta=6.0
    ):

        if not os.path.exists(model_path):
            raise FileNotFoundError(
                f"File model tidak ditemukan: {model_path}\n"
                "Pastikan assets/hand_landmarker.task ada."
            )

        base_options = python.BaseOptions(
            model_asset_path=model_path
        )

        # Mode VIDEO: hasil frame sebelumnya dipakai untuk melacak tangan,
        # jadi lebih cepat dan lebih stabil daripada mode gambar.
        options = vision.HandLandmarkerOptions(
            base_options=base_options,
            running_mode=vision.RunningMode.VIDEO,
            num_hands=num_hands,
            min_hand_detection_confidence=min_hand_detection_confidence,
            min_hand_presence_confidence=min_hand_presence_confidence,
            min_tracking_confidence=min_tracking_confidence
        )

        self.detector = vision.HandLandmarker.create_from_options(
            options
        )

        self.results = None
        self.hand = None  # landmark tangan pertama (sudah dihaluskan)
        self.smooth = smooth
        self.smoother = LandmarkSmoother(smooth_min_cutoff, smooth_beta)
        self.recognizer = GestureRecognizer()
        self._last_ts_ms = -1

        print("MediaPipe Hand Landmarker berhasil dimuat")

    def findHands(self, img, draw=True):

        imgRGB = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)

        mp_image = mp.Image(
            image_format=mp.ImageFormat.SRGB,
            data=imgRGB
        )

        # Timestamp harus selalu naik di mode VIDEO
        now = time.monotonic()
        ts_ms = int(now * 1000)
        if ts_ms <= self._last_ts_ms:
            ts_ms = self._last_ts_ms + 1
        self._last_ts_ms = ts_ms

        self.results = self.detector.detect_for_video(mp_image, ts_ms)

        if self.results.hand_landmarks:
            raw = self.results.hand_landmarks[0]
            self.hand = (
                self.smoother.smooth(raw, now) if self.smooth else raw
            )
        else:
            self.hand = None
            self.smoother.reset()  # mulai bersih saat tangan muncul lagi
            self.recognizer.reset()

        if draw and self.hand is not None:

            h, w, _ = img.shape
            white = (255, 255, 255)

            points = [
                (int(lm.x * w), int(lm.y * h))
                for lm in self.hand
            ]

            for start, end in CONNECTIONS:
                cv2.line(img, points[start], points[end], white, 3)

            for point in points:
                cv2.circle(img, point, 7, white, cv2.FILLED)

        return img

    def getGesture(self):
        """Mengembalikan nama gerakan (lihat GESTURE_PATTERNS) atau None.

        Panggil sekali per frame, setelah findHands().
        """
        if self.hand is None:
            return None

        return self.recognizer.update(self.hand)
