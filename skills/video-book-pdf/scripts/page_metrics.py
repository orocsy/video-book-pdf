"""Stable-view proposals; thresholds require recording-specific review."""
from __future__ import annotations

import argparse
import csv
import json
import re
import subprocess
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

DIFF_WIDTH = 320  # frames are compared small: enough to see a page turn, cheap to compute
SHARP_WIDTH = 1000  # sharpness is measured larger, where small text blur still shows


def _gray(path: Path, width: int) -> np.ndarray:
    with Image.open(path) as im:
        im = im.convert("L")
        height = max(1, round(im.height * width / im.width))
        return np.asarray(im.resize((width, height), Image.Resampling.BILINEAR), dtype=np.float32)


def sharpness(path: Path) -> float:
    """Variance of the Laplacian: higher is sharper. Comparable only within one recording."""
    g = _gray(path, SHARP_WIDTH)
    lap = -4 * g[1:-1, 1:-1] + g[:-2, 1:-1] + g[2:, 1:-1] + g[1:-1, :-2] + g[1:-1, 2:]
    return float(lap.var())


def difference(a: np.ndarray, b: np.ndarray) -> float:
    """Ink-normalized difference so white margins do not hide small text changes."""
    if a.shape != b.shape:
        return 255.0
    delta = np.abs(a-b)
    ink = (a < 220) | (b < 220)
    return float(delta[ink].mean()) if ink.any() else float(delta.mean())


def frames(directory: Path) -> list[Path]:
    found = sorted(p for p in directory.iterdir() if p.suffix.lower() in {".png", ".jpg", ".jpeg"})
    if not found:
        raise ValueError(f"no frames in {directory}")
    return found


SHOWINFO_LINE = re.compile(r"\bn:\s*(\d+)\b.*?\bpts_time:\s*([0-9.]+)")


def parse_showinfo(log: Path) -> list[float]:
    """Source `pts_time` of each sampled frame, in output order, from ffmpeg's showinfo log."""
    times: dict[int, float] = {}
    for line in log.read_text(encoding="utf-8", errors="replace").splitlines():
        if "showinfo" not in line:
            continue
        m = SHOWINFO_LINE.search(line)
        if m:
            times[int(m.group(1))] = float(m.group(2))
    if not times or sorted(times) != list(range(len(times))):
        sys.exit(f"{log}: showinfo frame numbers are missing or not contiguous")
    return [times[n] for n in range(len(times))]


def load_pts(path: Path | None, count: int) -> list[float] | None:
    if path is None:
        return None
    with path.open(encoding="utf-8", newline="") as f:
        pts = [float(row["pts_time"]) for row in csv.DictReader(f)]
    if len(pts) != count:
        sys.exit(f"{path} has {len(pts)} timestamps but the frames directory has {count} frames")
    return pts


def measure(directory: Path, fps: float, pts: Path | None = None) -> list[dict]:
    found = frames(directory)
    times = load_pts(pts, len(found))
    rows, previous = [], None
    for k, path in enumerate(found):
        small = _gray(path, DIFF_WIDTH)
        rows.append({
            "frame": path.name,
            "t": round(times[k] if times else k / fps, 3),
            "diff": round(difference(small, previous), 3) if previous is not None else None,
            "sharpness": round(sharpness(path), 1),
            "_small": small,
            "_path": path,
        })
        previous = small
    return rows


def segment(
    rows: list[dict], fps: float, change: float, same: float, min_seconds: float, min_sharp_ratio: float
) -> list[dict]:
    # A run of frames that each differ little from the one before is one stable view of a page.
    runs, current = [], []
    for row in rows:
        if current and (row["diff"] is None or row["diff"] > change):
            runs.append(current)
            current = []
        current.append(row)
    if current:
        runs.append(current)
    # Duration from the frames' own timestamps, plus one sampling interval for the last frame.
    stable = [r for r in runs if r[-1]["t"] - r[0]["t"] + 1 / fps >= min_seconds]

    # Motion blur during a page turn can also hold still for a moment. Keep only runs whose sharpest
    # frame is close to what a still page looks like in this recording.
    if stable:
        typical = float(np.median([max(r["sharpness"] for r in run) for run in stable]))
        stable = [run for run in stable if max(r["sharpness"] for r in run) >= typical * min_sharp_ratio]

    # The same page shown twice in a row (a pause, a small scroll back) becomes one candidate.
    pages: list[list[dict]] = []
    for run in stable:
        best = max(run, key=lambda r: r["sharpness"])
        if pages:
            last_best = max(pages[-1], key=lambda r: r["sharpness"])
            if difference(best["_small"], last_best["_small"]) <= same:
                pages[-1].extend(run)
                continue
        pages.append(list(run))

    out = []
    for n, rows_of_page in enumerate(pages, start=1):
        best = max(rows_of_page, key=lambda r: r["sharpness"])
        out.append({
            "candidate": n,
            "start": rows_of_page[0]["t"],
            "end": round(rows_of_page[-1]["t"] + 1 / fps, 3),
            "frames": len(rows_of_page),
            "best_frame": str(best["_path"]),
            "best_t": best["t"],
            "sharpness": best["sharpness"],
        })
    return out
