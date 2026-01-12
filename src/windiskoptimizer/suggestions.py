from __future__ import annotations

import datetime as dt
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, List

from .profiles import OptimizationProfile
from .scanner import ItemUsage


@dataclass
class Suggestion:
    path: Path
    reason: str
    reclaimable: int
    risk: str


COMMON_CACHE_LOCATIONS = [
    Path.home() / ".cache",
    Path("/tmp"),
    Path.home() / "AppData" / "Local" / "Temp",
]


EXTENSIONS_FOR_PURGE = [".tmp", ".log", ".bak", ".old"]


def _is_expired(file_path: Path, days: int = 30) -> bool:
    try:
        mtime = dt.datetime.fromtimestamp(file_path.stat().st_mtime)
    except (FileNotFoundError, PermissionError, OSError):
        return False
    return (dt.datetime.now() - mtime).days >= days


def from_large_files(items: Iterable[ItemUsage], profile: OptimizationProfile) -> List[Suggestion]:
    suggestions: List[Suggestion] = []
    for item in items:
        risk = "низкий" if profile.large_file_threshold >= item.size else "средний"
        suggestions.append(
            Suggestion(
                path=item.path,
                reason="Крупный файл превышает порог профиля",
                reclaimable=item.size,
                risk=risk,
            )
        )
    return suggestions


def from_temp_locations(profile: OptimizationProfile) -> List[Suggestion]:
    suggestions: List[Suggestion] = []
    for location in COMMON_CACHE_LOCATIONS:
        if not location.exists():
            continue
        try:
            total_size = sum(file.stat().st_size for file in location.rglob("*") if file.is_file())
        except (PermissionError, FileNotFoundError, OSError):
            continue
        if total_size == 0:
            continue
        suggestions.append(
            Suggestion(
                path=location,
                reason="Временные или кэш файлы",
                reclaimable=total_size,
                risk="низкий" if profile.name != "Агрессивно" else "средний",
            )
        )
    return suggestions


def from_extension_cleanup(targets: Iterable[Path], profile: OptimizationProfile) -> List[Suggestion]:
    suggestions: List[Suggestion] = []
    for target in targets:
        if not target.exists():
            continue
        for ext in EXTENSIONS_FOR_PURGE:
            for file_path in target.rglob(f"*{ext}"):
                try:
                    size = file_path.stat().st_size
                except (PermissionError, FileNotFoundError, OSError):
                    continue
                if not _is_expired(file_path, days=7):
                    continue
                suggestions.append(
                    Suggestion(
                        path=file_path,
                        reason=f"Файл с расширением {ext} выглядит устаревшим",
                        reclaimable=size,
                        risk="низкий",
                    )
                )
    return suggestions[: profile.suggestion_limit]


def build_suggestions(
    large_files: Iterable[ItemUsage],
    scan_targets: Iterable[Path],
    profile: OptimizationProfile,
) -> List[Suggestion]:
    result: List[Suggestion] = []
    result.extend(from_temp_locations(profile))
    result.extend(from_extension_cleanup(scan_targets, profile))
    result.extend(from_large_files(large_files, profile))
    result.sort(key=lambda sug: sug.reclaimable, reverse=True)
    return result[: profile.suggestion_limit]
