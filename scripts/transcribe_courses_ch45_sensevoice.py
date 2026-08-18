#!/usr/bin/env python3
"""Transcribe chapter 4/5 course videos with the cached SenseVoice model.

The output contract matches the existing chapter 1-3 transcript JSON files.
Files are written atomically and are reusable only when the current video hash
matches the hash recorded in the transcript.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
import tempfile
import time
import wave
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
COURSE_ROOT = Path(r"C:\Users\poyi\Downloads\课程合集")
TRANSCRIPT_ROOT = ROOT / "data" / "course_transcripts"
COURSE_DIRS = (
    "4.1 一元函数的导数及其应用",
    "4.2 一元函数的导数及其应用的综合提升",
    "4.3 数列",
    "4.4 数列的综合提升",
)
MODEL_ID = "iic/SenseVoiceSmall"
VAD_MODEL_ID = "iic/speech_fsmn_vad_zh-cn-16k-common-pytorch"
PROVENANCE = (
    "transcript source video is byte-identical to the "
    "Downloads/课程合集 video by SHA-256"
)
TAG_RE = re.compile(r"<\|[^|]+\|>")


def clean_text(value: Any) -> str:
    return TAG_RE.sub("", str(value or "")).strip()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def list_videos(prefix: str | None) -> list[Path]:
    videos: list[Path] = []
    for dirname in COURSE_DIRS:
        if prefix and not dirname.startswith(prefix):
            continue
        directory = COURSE_ROOT / dirname
        if not directory.is_dir():
            raise FileNotFoundError(f"course directory missing: {directory}")
        videos.extend(sorted(directory.glob("*.mp4"), key=lambda path: path.name))
    return videos


def valid_existing(path: Path, video_hash: str) -> bool:
    if not path.is_file() or path.stat().st_size == 0:
        return False
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return False
    return (
        payload.get("source_video_sha256") == video_hash
        and len(str(payload.get("full_text") or "")) >= 100
        and len(payload.get("sentences") or []) > 0
    )


def extract_wav(video: Path, output: Path) -> float:
    subprocess.run(
        [
            "ffmpeg",
            "-nostdin",
            "-loglevel",
            "error",
            "-y",
            "-i",
            str(video),
            "-vn",
            "-ac",
            "1",
            "-ar",
            "16000",
            "-f",
            "wav",
            str(output),
        ],
        check=True,
    )
    with wave.open(str(output), "rb") as handle:
        return handle.getnframes() / handle.getframerate()


def normalize_sentences(raw_sentences: Any) -> list[dict[str, Any]]:
    sentences: list[dict[str, Any]] = []
    for sentence in raw_sentences or []:
        if not isinstance(sentence, dict):
            continue
        text = clean_text(sentence.get("text"))
        if not text:
            continue
        sentences.append(
            {
                "start": int(sentence.get("start") or 0),
                "end": int(sentence.get("end") or 0),
                "text": text,
            }
        )
    return sentences


def transcribe_video(model: Any, video: Path, video_hash: str) -> dict[str, Any]:
    with tempfile.TemporaryDirectory(prefix="ybt-sensevoice-") as temp_dir:
        wav_path = Path(temp_dir) / "audio.wav"
        duration_s = extract_wav(video, wav_path)
        started = time.perf_counter()
        result = model.generate(
            input=str(wav_path),
            language="auto",
            use_itn=True,
            batch_size_s=60,
            sentence_timestamp=True,
        )
        elapsed_s = time.perf_counter() - started

    row = result[0] if isinstance(result, list) and result else result
    if not isinstance(row, dict):
        raise RuntimeError("SenseVoice returned no structured result")
    full_text = clean_text(row.get("text"))
    sentences = normalize_sentences(row.get("sentence_info"))
    if len(full_text) < 100:
        raise RuntimeError(f"transcript too short: {len(full_text)} characters")
    if not sentences:
        raise RuntimeError("transcript has no timestamped sentences")

    return {
        "file": f"{video.stem}.wav",
        "duration_s": duration_s,
        "full_text": full_text,
        "sentences": sentences,
        "source_video_file": str(video),
        "source_video_sha256": video_hash,
        "provenance": PROVENANCE,
        "asr_model": MODEL_ID,
        "asr_device": "cuda:0",
        "asr_elapsed_s": round(elapsed_s, 3),
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }


def write_json_atomic(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    temporary.replace(path)


def print_status(videos: list[Path]) -> int:
    rows = []
    for video in videos:
        output = TRANSCRIPT_ROOT / f"{video.stem}.json"
        state = "present" if output.is_file() and output.stat().st_size > 0 else "missing"
        rows.append({"video": video.name, "output": str(output), "state": state})
    summary = {
        "total": len(rows),
        "present": sum(row["state"] == "present" for row in rows),
        "missing": [row["video"] for row in rows if row["state"] == "missing"],
    }
    print(json.dumps({"summary": summary, "rows": rows}, ensure_ascii=False, indent=2))
    return 0 if not summary["missing"] else 1


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("prefix", nargs="?", help="course directory prefix, for example 4.3")
    parser.add_argument("--status", action="store_true")
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--limit", type=int, default=0)
    args = parser.parse_args()

    videos = list_videos(args.prefix)
    if args.limit:
        videos = videos[: args.limit]
    if args.status:
        return print_status(videos)
    if not videos:
        print("no videos selected", file=sys.stderr)
        return 2

    from funasr import AutoModel

    print(f"[model] loading {MODEL_ID} on cuda:0", flush=True)
    model = AutoModel(
        model=MODEL_ID,
        trust_remote_code=True,
        vad_model=VAD_MODEL_ID,
        vad_kwargs={"max_single_segment_time": 30000},
        device="cuda:0",
        disable_update=True,
    )
    print(f"[model] loaded; selected={len(videos)}", flush=True)

    failures: list[dict[str, str]] = []
    completed = 0
    skipped = 0
    for index, video in enumerate(videos, start=1):
        output = TRANSCRIPT_ROOT / f"{video.stem}.json"
        print(f"[{index}/{len(videos)}] hashing {video.name}", flush=True)
        video_hash = sha256_file(video)
        if not args.force and valid_existing(output, video_hash):
            skipped += 1
            print(f"[{index}/{len(videos)}] skip current {video.name}", flush=True)
            continue
        try:
            payload = transcribe_video(model, video, video_hash)
            write_json_atomic(output, payload)
            completed += 1
            speed = payload["duration_s"] / max(payload["asr_elapsed_s"], 0.001)
            print(
                f"[{index}/{len(videos)}] done {video.name} "
                f"chars={len(payload['full_text'])} sentences={len(payload['sentences'])} "
                f"speed={speed:.1f}x",
                flush=True,
            )
        except Exception as exc:  # Keep the batch resumable after one bad video.
            failures.append({"video": video.name, "error": str(exc)})
            print(f"[{index}/{len(videos)}] FAIL {video.name}: {exc}", flush=True)

    print(
        json.dumps(
            {
                "selected": len(videos),
                "completed": completed,
                "skipped": skipped,
                "failures": failures,
            },
            ensure_ascii=False,
        ),
        flush=True,
    )
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
