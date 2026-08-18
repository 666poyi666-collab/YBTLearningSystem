# -*- coding: utf-8 -*-
"""
第4/5章（课程目录 4.1/4.2/4.3/4.4）课程转写生成器。

把 Downloads/课程合集 下 4.1~4.4 四个目录的 mp4 依次转写为
data/course_transcripts/<视频文件名stem>.json，格式与第一章 3.1.x 转写完全一致：

    {
      "file": "<stem>.wav",
      "duration_s": <float>,
      "full_text": <str>,
      "sentences": [{"start": <ms>, "end": <ms>, "text": <str>}, ...],
      "source_video_file": <mp4 绝对路径>,
      "source_video_sha256": <mp4 sha256>,
      "provenance": "transcript source video is byte-identical to the Downloads/课程合集 video by SHA-256"
    }

用法（python -B）：
    python scripts/transcribe_courses_ch45.py                 # 全部 4 个目录
    python scripts/transcribe_courses_ch45.py 4.3             # 只转 4.3
    python scripts/transcribe_courses_ch45.py --resume        # 跳过已存在的输出
    python scripts/transcribe_courses_ch45.py --status        # 只输出完成/缺口清单

依赖：ffmpeg（PATH）、faster-whisper（本机已装，large-v3 已缓存）。
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

# ctranslate2 (GPU) 需要 cublas64_12.dll；torch 附带 nvidia/cublas pip 包，
# 把其 bin 目录加入 DLL 搜索路径，否则 RuntimeError: cublas64_12.dll not found。
_CUBLAS_CANDIDATES = [
    Path(sys.prefix) / "Lib" / "site-packages" / "nvidia" / "cublas" / "bin",
    Path(sys.prefix) / "site-packages" / "nvidia" / "cublas" / "bin",
    Path(r"C:\Users\poyi\AppData\Roaming\Python\Python312\site-packages\nvidia\cublas\bin"),
]
for _d in _CUBLAS_CANDIDATES:
    if _d.is_dir() and (_d / "cublas64_12.dll").exists():
        # ctranslate2 的 DLL 解析只认进程 PATH（LoadLibrary 搜索路径），
        # add_dll_directory 对它无效；必须把 cublas bin 目录放入 PATH。
        os.environ["PATH"] = str(_d) + os.pathsep + os.environ.get("PATH", "")
        try:
            os.add_dll_directory(str(_d))
        except AttributeError:
            pass
        break

ROOT = Path(__file__).resolve().parents[1]
COURSE_ROOT = Path(r"C:\Users\poyi\Downloads\课程合集")
TRANSCRIPT_ROOT = ROOT / "data" / "course_transcripts"

DIRS = ["4.1 一元函数的导数及其应用", "4.2 一元函数的导数及其应用的综合提升", "4.3 数列", "4.4 数列的综合提升"]

PROVENANCE = "transcript source video is byte-identical to the Downloads/课程合集 video by SHA-256"
MODEL_SIZE = "large-v3"
COMPUTE_TYPE = "int8"


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def list_videos(only_dir: str | None = None) -> list[Path]:
    videos = []
    for d in DIRS:
        if only_dir and not d.startswith(only_dir):
            continue
        p = COURSE_ROOT / d
        if not p.is_dir():
            print(f"[warn] 课程目录不存在: {p}", file=sys.stderr)
            continue
        videos.extend(sorted(p.glob("*.mp4")))
    return videos


def extract_wav(video: Path) -> tuple[Path, float]:
    """提取 16k 单声道 wav 到临时目录；返回 (wav_path, duration_s)。"""
    tmp = Path(tempfile.gettempdir()) / f"ybt_ch45_{video.stem}.wav"
    subprocess.run(
        ["ffmpeg", "-y", "-i", str(video), "-ac", "1", "-ar", "16000", "-f", "wav", str(tmp)],
        check=True, capture_output=True,
    )
    import wave
    with wave.open(str(tmp), "rb") as w:
        frames = w.getnframes()
        rate = w.getframerate()
        duration_s = frames / rate
    return tmp, duration_s


def transcribe(model, video: Path) -> dict:
    wav, duration_s = extract_wav(video)
    try:
        segments, _info = model.transcribe(str(wav), language="zh", beam_size=5, vad_filter=True)
        sentences = []
        full_parts = []
        for seg in segments:
            sentences.append({
                "start": int(round(seg.start * 1000)),
                "end": int(round(seg.end * 1000)),
                "text": seg.text.strip(),
            })
            full_parts.append(seg.text.strip())
        return {
            "file": f"{video.stem}.wav",
            "duration_s": duration_s,
            "full_text": "".join(full_parts),
            "sentences": sentences,
            "source_video_file": str(video),
            "source_video_sha256": sha256_file(video),
            "provenance": PROVENANCE,
        }
    finally:
        wav.unlink(missing_ok=True)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("only_dir", nargs="?", default=None, help="如 4.3，只处理该目录")
    ap.add_argument("--resume", action="store_true", help="跳过已存在的输出")
    ap.add_argument("--status", action="store_true", help="只输出完成/缺口清单")
    args = ap.parse_args()

    videos = list_videos(args.only_dir)
    TRANSCRIPT_ROOT.mkdir(parents=True, exist_ok=True)

    if args.status:
        done = 0
        for v in videos:
            out = TRANSCRIPT_ROOT / f"{v.stem}.json"
            ok = out.exists() and out.stat().st_size > 0
            print(("DONE " if ok else "GAP  ") + v.name)
            done += ok
        print(f"summary: {done}/{len(videos)} done")
        return 0

    from faster_whisper import WhisperModel

    model = WhisperModel(MODEL_SIZE, device="cuda", compute_type=COMPUTE_TYPE)
    print(f"[model] {MODEL_SIZE} {COMPUTE_TYPE} loaded", flush=True)

    failures: list[str] = []

    for v in videos:
        out = TRANSCRIPT_ROOT / f"{v.stem}.json"
        if args.resume and out.exists() and out.stat().st_size > 0:
            print(f"[skip] {v.name}")
            continue
        print(f"[start] {v.name}", flush=True)
        try:
            data = transcribe(model, v)
            with open(out, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            print(f"[done]  {v.name}  chars={len(data['full_text'])}  sentences={len(data['sentences'])}", flush=True)
        except Exception as exc:
            print(f"[FAIL]  {v.name}: {exc}", flush=True)
            failures.append(v.name)
            continue
    if failures:
        print(f"failures ({len(failures)}): {failures}", flush=True)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
