"""Penghalus landmark tangan memakai One Euro Filter.

Ide filternya: saat tangan hampir diam, getaran kecil diredam kuat
(gambar stabil). Saat tangan bergerak cepat, peredaman dikurangi otomatis
(tidak ada efek "tertinggal").

Dua parameter utama:
    min_cutoff  makin kecil -> makin halus saat diam, tapi bisa terasa lambat
    beta        makin besar -> makin responsif saat tangan bergerak cepat
"""

import math
from types import SimpleNamespace

NUM_LANDMARKS = 21


def _alpha(cutoff, dt):
    tau = 1.0 / (2.0 * math.pi * cutoff)
    return 1.0 / (1.0 + tau / dt)


class OneEuroFilter:

    def __init__(self, min_cutoff=1.5, beta=6.0, d_cutoff=1.0):
        self.min_cutoff = min_cutoff
        self.beta = beta
        self.d_cutoff = d_cutoff
        self.reset()

    def reset(self):
        self.x_prev = None
        self.dx_prev = 0.0
        self.t_prev = None

    def __call__(self, x, t):
        if self.x_prev is None:
            self.x_prev = x
            self.t_prev = t
            return x

        dt = max(t - self.t_prev, 1e-6)

        # Kecepatan gerak, dihaluskan
        dx = (x - self.x_prev) / dt
        a_d = _alpha(self.d_cutoff, dt)
        dx_hat = a_d * dx + (1.0 - a_d) * self.dx_prev

        # Makin cepat bergerak, makin tinggi cutoff (makin sedikit diredam)
        cutoff = self.min_cutoff + self.beta * abs(dx_hat)
        a = _alpha(cutoff, dt)
        x_hat = a * x + (1.0 - a) * self.x_prev

        self.x_prev = x_hat
        self.dx_prev = dx_hat
        self.t_prev = t
        return x_hat


class LandmarkSmoother:
    """Menghaluskan 21 landmark (x, y) satu tangan."""

    def __init__(self, min_cutoff=1.5, beta=6.0):
        self.filters = [
            (OneEuroFilter(min_cutoff, beta), OneEuroFilter(min_cutoff, beta))
            for _ in range(NUM_LANDMARKS)
        ]

    def reset(self):
        for fx, fy in self.filters:
            fx.reset()
            fy.reset()

    def smooth(self, hand, t):
        """hand: list landmark dengan .x dan .y. Mengembalikan list baru."""
        return [
            SimpleNamespace(x=fx(lm.x, t), y=fy(lm.y, t))
            for lm, (fx, fy) in zip(hand, self.filters)
        ]
