import asyncio
import math
from pathlib import Path

import numpy as np

from app.config import Settings
from app.models import TuningResult
from app.services.media import AudioInfo

SAMPLE_RATE = 22050
WINDOW_SIZE = 8192
HOP_SIZE = 4096
MIN_FREQUENCY = 55.0
MAX_FREQUENCY = 4000.0
REFERENCE_432_OFFSET = 1200 * math.log2(432 / 440)


class TuningAnalysisError(RuntimeError):
    pass


def _circular_distance(first: float, second: float) -> float:
    return abs((first - second + 50) % 100 - 50)


def _segment_starts(duration: float, segment_seconds: int) -> list[float]:
    if duration <= segment_seconds * 1.5:
        return [0.0]
    latest = max(0.0, duration - segment_seconds)
    return sorted({round(latest * position, 3) for position in (0.12, 0.45, 0.78)})


async def _extract_segment(path: Path, start: float, duration: int) -> np.ndarray:
    process = await asyncio.create_subprocess_exec(
        "ffmpeg",
        "-hide_banner",
        "-loglevel",
        "error",
        "-nostdin",
        "-ss",
        str(start),
        "-i",
        str(path),
        "-t",
        str(duration),
        "-vn",
        "-ac",
        "1",
        "-ar",
        str(SAMPLE_RATE),
        "-f",
        "f32le",
        "pipe:1",
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    stdout, stderr = await process.communicate()
    if process.returncode != 0 or not stdout:
        detail = stderr.decode(errors="replace").strip()
        raise TuningAnalysisError(f"Impossible d’extraire le signal à analyser. {detail[:180]}")
    return np.frombuffer(stdout, dtype="<f4").copy()


def _estimate_tuning(samples: np.ndarray) -> tuple[float, int, int]:
    if samples.size < WINDOW_SIZE:
        samples = np.pad(samples, (0, WINDOW_SIZE - samples.size))
    window = np.hanning(WINDOW_SIZE).astype(np.float32)
    frequencies = np.fft.rfftfreq(WINDOW_SIZE, 1 / SAMPLE_RATE)
    allowed = (frequencies >= MIN_FREQUENCY) & (frequencies <= MAX_FREQUENCY)
    allowed_indices = np.flatnonzero(allowed)
    histogram = np.zeros(201, dtype=np.float64)
    accepted_peaks = 0

    for start in range(0, samples.size - WINDOW_SIZE + 1, HOP_SIZE):
        frame = samples[start : start + WINDOW_SIZE]
        if float(np.sqrt(np.mean(frame * frame))) < 0.003:
            continue
        spectrum = np.abs(np.fft.rfft(frame * window))
        region = spectrum[allowed]
        if region.size < 3:
            continue
        threshold = max(float(np.percentile(region, 90)), float(region.max()) * 0.025)
        local = region[1:-1]
        peaks = np.flatnonzero(
            (local > region[:-2]) & (local >= region[2:]) & (local >= threshold)
        ) + 1
        if peaks.size == 0:
            continue
        strongest = peaks[np.argsort(region[peaks])[-18:]]
        for relative_index in strongest:
            index = int(allowed_indices[relative_index])
            alpha, beta, gamma = spectrum[index - 1 : index + 2]
            denominator = alpha - 2 * beta + gamma
            correction = 0.5 * (alpha - gamma) / denominator if denominator else 0.0
            frequency = (index + float(np.clip(correction, -0.5, 0.5))) * SAMPLE_RATE / WINDOW_SIZE
            midi = 69 + 12 * math.log2(frequency / 440)
            residual = (midi - round(midi)) * 100
            weight = float(beta) / math.sqrt(max(frequency, 1.0))
            bin_index = int(round((residual + 50) * 2)) % 200
            histogram[bin_index] += weight
            accepted_peaks += 1

    if accepted_peaks < 12 or histogram.sum() <= 0:
        raise TuningAnalysisError(
            "Le morceau ne contient pas assez de notes stables pour estimer son accordage."
        )
    kernel_x = np.arange(-12, 13)
    kernel = np.exp(-0.5 * (kernel_x / 4) ** 2)
    extended = np.concatenate([histogram[-24:-1], histogram, histogram[1:24]])
    smoothed = np.convolve(extended, kernel, mode="same")[23:-23]
    peak_index = int(np.argmax(smoothed))
    offset = peak_index / 2 - 50
    peak_share = float(smoothed[peak_index] / max(smoothed.sum(), 1e-9))
    confidence = round(np.clip((peak_share - 0.006) / 0.035 * 100, 5, 99))
    return offset, confidence, accepted_peaks


async def analyze_tuning(
    path: Path,
    info: AudioInfo,
    settings: Settings,
    progress_callback,
) -> TuningResult:
    starts = _segment_starts(info.duration, settings.analysis_segment_seconds)
    segments: list[np.ndarray] = []
    for index, start in enumerate(starts):
        segments.append(await _extract_segment(path, start, settings.analysis_segment_seconds))
        progress_callback(15 + round((index + 1) / len(starts) * 45))
    samples = np.concatenate(segments)
    offset, confidence, _ = await asyncio.to_thread(_estimate_tuning, samples)
    estimated = 440 * 2 ** (offset / 1200)
    distance_440 = _circular_distance(offset, 0)
    distance_432 = _circular_distance(offset, REFERENCE_432_OFFSET)
    if confidence < 25:
        classification = "uncertain"
        explanation = "L’accordage n’a pas pu être déterminé avec suffisamment de confiance."
    elif distance_432 <= 7 and distance_432 < distance_440:
        classification = "432"
        explanation = "Le morceau semble accordé autour de La = 432 Hz."
    elif distance_440 <= 7 and distance_440 <= distance_432:
        classification = "440"
        explanation = "Le morceau semble accordé autour de La = 440 Hz."
    else:
        classification = "other"
        explanation = f"Le morceau semble utiliser une référence proche de {estimated:.1f} Hz."
    progress_callback(100)
    return TuningResult(
        estimated_reference_hz=round(estimated, 2),
        offset_from_440_cents=round(offset, 2),
        offset_from_432_cents=round(offset - REFERENCE_432_OFFSET, 2),
        classification=classification,
        confidence=confidence,
        analyzed_seconds=round(samples.size / SAMPLE_RATE, 1),
        explanation=explanation,
    )
