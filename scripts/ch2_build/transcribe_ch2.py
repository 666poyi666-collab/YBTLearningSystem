# -*- coding: utf-8 -*-
"""第 2 章（课程目录 3.2 直线与圆的方程）视频转写批处理。

职责：对 Downloads/课程合集/3.2 直线与圆的方程/*.mp4
  1. 计算源视频 SHA-256（转写绑定用，与 catalog.scan_transcripts 契约一致）；
  2. ffmpeg 提取 16kHz 单声道 wav；
  3. faster-whisper large-v3 (CUDA int8_float16) 转写中文；
  4. 输出 data/course_transcripts/<视频stem>.json（只含转写与绑定字段，不含答案）。

用法:
  python scripts/ch2_build/transcribe_ch2.py [--limit N] [--only <stem子串>]

只写第 2 章转写产物；不触碰原始视频、OCR、答案侧车与第 1 章文件。
"""
from __future__ import annotations

import argparse
import glob
import hashlib
import json
import os
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

# ctranslate2(CUDA12) 需要 cublas64_12.dll；torch 自带的是 CUDA13 命名，必须显式注入
# nvidia-cublas-cu12 安装目录，否则 transcribe 阶段报 Library cublas64_12.dll not found。
_CUBLAS_CANDIDATES = glob.glob(
    r"C:\Users\poyi\AppData\Roaming\Python\Python312\site-packages\nvidia\cublas\bin"
)
if _CUBLAS_CANDIDATES:
    os.environ["PATH"] = _CUBLAS_CANDIDATES[0] + os.pathsep + os.environ.get("PATH", "")

ROOT = Path(r"C:\开发\小工具\一本通学习系统_v7")
COURSE_ROOT = Path(r"C:\Users\poyi\Downloads\课程合集\3.2 直线与圆的方程")
WAV_DIR = ROOT / "tmp" / "ch2_wav"
TRANSCRIPT_DIR = ROOT / "data" / "course_transcripts"
LOG = ROOT / "tmp" / "ch2_transcribe.log"

MODEL = "large-v3"
COMPUTE_TYPE = "int8_float16"
LANGUAGE = "zh"


def log(msg: str) -> None:
    line = f"[{datetime.now().isoformat(timespec='seconds')}] {msg}"
    print(line, flush=True)
    with LOG.open("a", encoding="utf-8") as fh:
        fh.write(line + "\n")


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for block in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def extract_wav(mp4: Path) -> Path:
    wav = WAV_DIR / (mp4.stem + ".wav")
    if not wav.is_file() or wav.stat().st_size == 0:
        subprocess.run(
            ["ffmpeg", "-y", "-i", str(mp4), "-ac", "1", "-ar", "16000", "-vn", str(wav)],
            check=True, capture_output=True, timeout=1800,
        )
    return wav


def transcribe_one(model, mp4: Path, with_sha: bool) -> dict:
    log(f"start {mp4.name}")
    t0 = time.time()
    source_sha = sha256(mp4) if with_sha else None
    wav = extract_wav(mp4)
    duration_s = round(wav.stat().st_size / (16000 * 2), 1)  # wav 文件字节数/采样率
    try:
        segments, info = model.transcribe(
            str(wav), language=LANGUAGE, vad_filter=True, beam_size=5,
        )
        full_text = "".join(seg.text for seg in segments)
    except Exception as exc:  # noqa: BLE001
        log(f"FAIL {mp4.name}: {exc}")
        raise
    elapsed = time.time() - t0
    log(f"done {mp4.name} audio={duration_s}s asr={elapsed:.0f}s "
        f"x{elapsed / max(duration_s, 1):.1f} chars={len(full_text)}")
    record = {
        "file": wav.name,
        "duration_s": info.duration if info and getattr(info, "duration", None) else duration_s,
        "full_text": full_text,
        "asr_tool": "faster-whisper",
        "model": MODEL,
        "language": LANGUAGE,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "source_video_file": str(mp4),
    }
    if source_sha:
        record["source_video_sha256"] = source_sha
    out = TRANSCRIPT_DIR / (mp4.stem + ".json")
    out.write_text(json.dumps(record, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    log(f"saved {out.name}")
    return record


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=0, help="只处理前 N 个（测试用）")
    parser.add_argument("--only", default="", help="只处理文件名含该子串的视频")
    args = parser.parse_args()

    files = sorted(
        p for p in COURSE_ROOT.glob("*.mp4")
        if (not args.only or args.only in p.name) and not (TRANSCRIPT_DIR / (p.stem + ".json")).is_file()
    )
    if args.limit:
        files = files[: args.limit]
    if not files:
        log("no pending videos")
        return 0

    log(f"batch start: {len(files)} videos, model={MODEL} compute={COMPUTE_TYPE}")
    from faster_whisper import WhisperModel

    model = WhisperModel(MODEL, device="cuda", compute_type=COMPUTE_TYPE)
    for index, mp4 in enumerate(files, start=1):
        try:
            transcribe_one(model, mp4, with_sha=True)
        except Exception as exc:  # noqa: BLE001
            log(f"BATCH_FAIL at {mp4.name}: {exc}")
            return 2
    log("batch complete")
    return 0


if __name__ == "__main__":
    sys.exit(main())
