from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List

from .profiles import OptimizationProfile


@dataclass
class ItemUsage:
    path: Path
    size: int
    is_dir: bool


@dataclass
class DirectoryReport:
    root: Path
    total_size: int
    files: int
    directories: int
    children: List[ItemUsage]


def _iter_dir(path: Path) -> Iterable[os.DirEntry]:
    with os.scandir(path) as it:
        for entry in it:
            yield entry


def _safe_size(entry: os.DirEntry, follow_symlinks: bool) -> int:
    try:
        return entry.stat(follow_symlinks=follow_symlinks).st_size
    except (FileNotFoundError, PermissionError, OSError):
        return 0


def summarize_directory(path: Path, profile: OptimizationProfile) -> DirectoryReport:
    total_size = 0
    file_count = 0
    dir_count = 0
    children: List[ItemUsage] = []

    for entry in _iter_dir(path):
        if entry.is_symlink() and not profile.follow_symlinks:
            continue
        if entry.is_dir(follow_symlinks=profile.follow_symlinks):
            dir_count += 1
            dir_size = directory_size(Path(entry.path), profile.max_depth - 1, profile.follow_symlinks)
            total_size += dir_size
            children.append(ItemUsage(path=Path(entry.path), size=dir_size, is_dir=True))
        else:
            file_count += 1
            size = _safe_size(entry, profile.follow_symlinks)
            total_size += size
            children.append(ItemUsage(path=Path(entry.path), size=size, is_dir=False))

    children.sort(key=lambda item: item.size, reverse=True)
    return DirectoryReport(
        root=path,
        total_size=total_size,
        files=file_count,
        directories=dir_count,
        children=children,
    )


def directory_size(path: Path, depth: int, follow_symlinks: bool) -> int:
    if depth < 0:
        return 0

    size = 0
    try:
        for entry in _iter_dir(path):
            if entry.is_symlink() and not follow_symlinks:
                continue
            if entry.is_dir(follow_symlinks=follow_symlinks):
                size += directory_size(Path(entry.path), depth - 1, follow_symlinks)
            else:
                size += _safe_size(entry, follow_symlinks)
    except (PermissionError, FileNotFoundError, OSError):
        return 0
    return size


def find_large_files(path: Path, profile: OptimizationProfile, limit: int) -> List[ItemUsage]:
    large_files: List[ItemUsage] = []

    for root, dirs, files in os.walk(path):
        depth = Path(root).relative_to(path).parts
        if len(depth) > profile.max_depth:
            dirs[:] = []
            continue

        for name in files:
            file_path = Path(root, name)
            try:
                stat = file_path.stat()
            except (FileNotFoundError, PermissionError, OSError):
                continue
            if stat.st_size >= profile.large_file_threshold:
                large_files.append(ItemUsage(path=file_path, size=stat.st_size, is_dir=False))

    large_files.sort(key=lambda item: item.size, reverse=True)
    return large_files[:limit]


def analyze_targets(targets: List[Path], profile: OptimizationProfile) -> Dict[Path, DirectoryReport]:
    reports: Dict[Path, DirectoryReport] = {}
    for target in targets:
        if not target.exists():
            continue
        if target.is_file():
            stat = target.stat()
            reports[target] = DirectoryReport(
                root=target,
                total_size=stat.st_size,
                files=1,
                directories=0,
                children=[ItemUsage(path=target, size=stat.st_size, is_dir=False)],
            )
            continue
        try:
            reports[target] = summarize_directory(target, profile)
        except (PermissionError, FileNotFoundError, OSError):
            continue
    return reports
