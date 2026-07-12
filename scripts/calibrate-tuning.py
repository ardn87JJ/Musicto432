#!/usr/bin/env python3
import argparse
import asyncio
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from app.config import Settings  # noqa: E402
from app.services.media import ALLOWED_EXTENSIONS, probe_audio  # noqa: E402
from app.services.tuning_analyzer import analyze_tuning  # noqa: E402


async def analyze_reference(path: Path, expected: int, settings: Settings) -> dict[str, object]:
    info = await probe_audio(path, settings)
    result = await analyze_tuning(path, info, settings, lambda _: None)
    return {
        "file": str(path),
        "expected_hz": expected,
        "estimated_hz": result.estimated_reference_hz,
        "absolute_error_hz": round(abs(result.estimated_reference_hz - expected), 3),
        "classification": result.classification,
        "confidence": result.confidence,
        "diagnostic": result.diagnostic,
        "passed": result.classification == str(expected),
    }


async def main() -> int:
    parser = argparse.ArgumentParser(
        description="Calibre l’analyse MusicTo432 avec des morceaux connus à 432 et 440 Hz."
    )
    parser.add_argument("references", type=Path, help="Dossier contenant 432/ et 440/")
    parser.add_argument("--json", type=Path, help="Chemin facultatif du rapport JSON")
    args = parser.parse_args()
    references = args.references.expanduser().resolve()
    inputs: list[tuple[Path, int]] = []
    for expected in (432, 440):
        folder = references / str(expected)
        if folder.is_dir():
            inputs.extend(
                (path, expected)
                for path in sorted(folder.iterdir())
                if path.is_file() and path.suffix.lower() in ALLOWED_EXTENSIONS
            )
    counts = {expected: sum(1 for _, value in inputs if value == expected) for expected in (432, 440)}
    if any(counts[value] < 2 for value in counts):
        parser.error("fournissez au moins deux morceaux dans 432/ et deux dans 440/")
    settings = Settings(temp_root=Path("/tmp/musicto432-calibration"))
    results = []
    for path, expected in inputs:
        print(f"Analyse {expected} Hz : {path.name}…", flush=True)
        try:
            results.append(await analyze_reference(path, expected, settings))
        except Exception as exc:
            results.append({"file": str(path), "expected_hz": expected, "passed": False, "error": str(exc)})
    successful = [item for item in results if "estimated_hz" in item]
    report = {
        "files": results,
        "summary": {
            "total": len(results),
            "classified_correctly": sum(bool(item.get("passed")) for item in results),
            "mean_absolute_error_hz": round(
                sum(float(item["absolute_error_hz"]) for item in successful) / max(len(successful), 1),
                3,
            ),
            "mean_confidence": round(
                sum(int(item["confidence"]) for item in successful) / max(len(successful), 1),
                1,
            ),
        },
    }
    rendered = json.dumps(report, ensure_ascii=False, indent=2)
    if args.json:
        args.json.write_text(rendered + "\n", encoding="utf-8")
        print(f"Rapport enregistré : {args.json}")
    print(json.dumps(report["summary"], ensure_ascii=False, indent=2))
    return 0 if report["summary"]["classified_correctly"] == len(results) else 1


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
