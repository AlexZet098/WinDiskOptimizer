from __future__ import annotations

import importlib.util
import platform
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, List


@dataclass
class DiskInfo:
    mount_point: Path
    total: int
    used: int
    free: int

    @property
    def usage_percent(self) -> float:
        if self.total == 0:
            return 0.0
        return (self.used / self.total) * 100


def format_size(num_bytes: int) -> str:
    step_unit = 1024.0
    units = ["Б", "КБ", "МБ", "ГБ", "ТБ", "ПБ"]
    size = float(num_bytes)
    for unit in units:
        if size < step_unit:
            return f"{size:.1f} {unit}"
        size /= step_unit
    return f"{size:.1f} ЕБ"


def detect_mount_points() -> List[Path]:
    mounts: List[Path] = []

    if importlib.util.find_spec("psutil") is not None:
        import psutil

        for part in psutil.disk_partitions(all=False):
            mount_path = Path(part.mountpoint)
            if mount_path.exists() and mount_path.is_dir():
                mounts.append(mount_path)

    if not mounts:
        system = platform.system().lower()
        if system == "windows":
            for letter in "CDEFGHIJKLMNOPQRSTUVWXYZ":
                candidate = Path(f"{letter}:/")
                if candidate.exists():
                    mounts.append(candidate)
        else:
            mounts.append(Path("/"))
            mounts.extend(path for path in (Path("/mnt"), Path("/media")) if path.exists())

    normalized = []
    for mount in mounts:
        try:
            normalized.append(mount.resolve())
        except OSError:
            normalized.append(mount)
    return normalized


def collect_disk_info(mount_point: Path) -> DiskInfo:
    usage = shutil.disk_usage(str(mount_point))
    return DiskInfo(
        mount_point=mount_point,
        total=usage.total,
        used=usage.used,
        free=usage.free,
    )


def ensure_paths(selected: Iterable[str] | None) -> List[Path]:
    if not selected:
        return []
    paths = []
    for raw_path in selected:
        path = Path(raw_path).expanduser()
        if path.exists():
            paths.append(path)
    return paths
