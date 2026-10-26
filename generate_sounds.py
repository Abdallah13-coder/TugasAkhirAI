"""Membuat file suara untuk tiap gerakan memakai edge-tts (suara wanita Indonesia).

Jalankan sekali (butuh internet):
    python generate_sounds.py

Ubah teks di dict SOUNDS di bawah sesuai keinginanmu, lalu jalankan ulang.
"""

import asyncio
import os

import edge_tts

VOICE = "id-ID-GadisNeural"  # suara wanita. Suara pria: id-ID-ArdiNeural

# nama file -> teks yang diucapkan
SOUNDS = {
    "halo.mp3": "Halo, perkenalkan",
    "maaf.mp3": "Maaf",
    "tolong.mp3": "Tolong saya",
    "terima_kasih.mp3": "Terima kasih",
    "ya.mp3": "Ya",
    "tidak.mp3": "Tidak",
    "saya.mp3": "Saya",
    "kamu.mp3": "Kamu",
    "makan.mp3": "Saya mau makan",
    "minum.mp3": "Saya mau minum",
    "janji.mp3": "Saya janji",
    "sakit.mp3": "Saya sakit",
}

ASSETS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets")


async def main():
    os.makedirs(ASSETS, exist_ok=True)

    for filename, text in SOUNDS.items():
        path = os.path.join(ASSETS, filename)
        await edge_tts.Communicate(text, VOICE).save(path)
        print(f"Dibuat: assets/{filename}  ->  \"{text}\"")


if __name__ == "__main__":
    asyncio.run(main())
