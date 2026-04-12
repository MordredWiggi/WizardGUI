"""
sounds/__init__.py – Sound utilities for Wizard GUI.

Provides a cross-platform function to play the Windows XP shutdown sound.
The WAV file is generated on first use using Python's standard library only.
"""
from __future__ import annotations

import math
import struct
import subprocess
import sys
import wave
from pathlib import Path
from typing import Optional


_SOUNDS_DIR = Path(__file__).parent
_XP_SHUTDOWN_WAV = _SOUNDS_DIR / "xp_shutdown.wav"

# Keep a module-level reference to the QSoundEffect so it isn't garbage-collected
# before playback completes (QSoundEffect.play() is non-blocking).
_sound_effect = None


def _generate_xp_shutdown_wav(path: Path) -> None:
    """Generate an approximation of the Windows XP shutdown sound as a WAV file."""
    sample_rate = 44100

    # Notes: (frequency_hz, duration_s, amplitude)
    # Approximation of the classic XP shutdown melody
    notes = [
        (659.25, 0.10, 0.75),   # E5
        (554.37, 0.10, 0.70),   # C#5 / Db5
        (493.88, 0.12, 0.65),   # B4
        (392.00, 0.10, 0.65),   # G4
        (329.63, 0.10, 0.70),   # E4
        (261.63, 0.25, 0.75),   # C4 (held)
    ]

    all_samples: list[int] = []
    for freq, duration, amplitude in notes:
        n = int(sample_rate * duration)
        for i in range(n):
            t = i / sample_rate
            # Smooth envelope: fast attack, linear decay
            attack = min(1.0, t / 0.008)
            decay = max(0.0, 1.0 - t / duration)
            env = attack * decay
            val = amplitude * env * math.sin(2.0 * math.pi * freq * t)
            all_samples.append(int(val * 32767))

    with wave.open(str(path), "w") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(sample_rate)
        wav.writeframes(struct.pack(f"<{len(all_samples)}h", *all_samples))


def ensure_xp_shutdown_wav() -> Optional[Path]:
    """Return the path to the XP shutdown WAV, generating it if necessary."""
    if not _XP_SHUTDOWN_WAV.exists():
        try:
            _generate_xp_shutdown_wav(_XP_SHUTDOWN_WAV)
        except Exception:
            return None
    return _XP_SHUTDOWN_WAV


def play_xp_shutdown() -> None:
    """Play the Windows XP shutdown sound (non-blocking, best-effort)."""
    path = ensure_xp_shutdown_wav()
    if path is None:
        return

    # 1. Try PyQt6.QtMultimedia (available when the full Qt multimedia module is installed)
    try:
        from PyQt6.QtMultimedia import QSoundEffect  # type: ignore
        from PyQt6.QtCore import QUrl
        global _sound_effect
        _sound_effect = QSoundEffect()
        _sound_effect.setSource(QUrl.fromLocalFile(str(path)))
        _sound_effect.setVolume(0.85)
        _sound_effect.play()
        return
    except Exception:
        pass

    # 2. Platform-specific fallback
    try:
        if sys.platform == "win32":
            import winsound  # type: ignore
            winsound.PlaySound(str(path), winsound.SND_FILENAME | winsound.SND_ASYNC)
        elif sys.platform == "darwin":
            subprocess.Popen(["afplay", str(path)], stderr=subprocess.DEVNULL)
        else:
            subprocess.Popen(
                ["aplay", "-q", str(path)],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
    except Exception:
        pass  # Silent fallback – no audio available
