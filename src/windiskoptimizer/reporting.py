from __future__ import annotations

from pathlib import Path
from typing import Iterable, List

from .scanner import DirectoryReport, ItemUsage
from .suggestions import Suggestion
from .utils import DiskInfo, format_size


def print_disk_info(disk: DiskInfo) -> None:
    print(f"Диск: {disk.mount_point}")
    print(f"  Всего: {format_size(disk.total)}")
    print(f"  Использовано: {format_size(disk.used)} ({disk.usage_percent:.1f}%)")
    print(f"  Свободно: {format_size(disk.free)}")


def print_directory_reports(reports: Iterable[DirectoryReport]) -> None:
    for report in reports:
        print(f"\nКаталог: {report.root}")
        print(f"  Размер: {format_size(report.total_size)}")
        print(f"  Файлов: {report.files}, Папок: {report.directories}")
        for child in report.children[:10]:
            marker = "[D]" if child.is_dir else "[F]"
            print(f"    {marker} {child.path} — {format_size(child.size)}")


def print_large_files(files: List[ItemUsage]) -> None:
    if not files:
        print("Крупные файлы не найдены по заданным порогам.")
        return
    print("\nКрупные файлы:")
    for item in files[:20]:
        print(f"  {item.path} — {format_size(item.size)}")


def print_suggestions(suggestions: Iterable[Suggestion]) -> None:
    print("\nПредложения по очистке:")
    for suggestion in suggestions:
        print(
            f"  {suggestion.path}\n    Причина: {suggestion.reason}\n    Можно освободить: {format_size(suggestion.reclaimable)}\n    Риск: {suggestion.risk}"
        )


def print_chart_info(paths: Iterable[Path]) -> None:
    for path in paths:
        print(f"Сохранен график: {path}")
