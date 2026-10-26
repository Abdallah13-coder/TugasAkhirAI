"""Pemungutan suara antar frame, supaya satu-dua frame salah baca
tidak langsung mengganti gerakan.
"""

from collections import Counter, deque


class LabelVoter:
    """Gerakan baru dianggap sah kalau menang di sebagian besar frame terakhir.

    window     jumlah frame terakhir yang dihitung
    min_votes  jumlah suara minimal agar suatu gerakan (atau "tidak ada
               tangan", yaitu None) dianggap sah

    Satu frame yang salah baca di tengah gerakan yang stabil tidak lagi
    mengulang hitungan dari nol, seperti pada hitungan "berturut-turut".
    """

    def __init__(self, window=10, min_votes=7):
        if not 0 < min_votes <= window:
            raise ValueError("min_votes harus di antara 1 dan window.")
        self.min_votes = min_votes
        self.history = deque(maxlen=window)
        self.current = None  # gerakan terakhir yang sah

    def reset(self):
        self.history.clear()
        self.current = None

    def update(self, label):
        """Masukkan hasil satu frame. Mengembalikan gerakan yang sah saat ini."""
        self.history.append(label)
        winner, votes = Counter(self.history).most_common(1)[0]

        if votes >= self.min_votes:
            self.current = winner
        return self.current
