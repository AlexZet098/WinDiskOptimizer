from __future__ import annotations

import argparse
from pathlib import Path
from typing import List

from .charts import render_directory_breakdown, render_disk_usage_pie, render_large_files_chart
from .profiles import PROFILES, resolve_profile
from .reporting import print_chart_info, print_directory_reports, print_disk_info, print_large_files, print_suggestions
from .scanner import analyze_targets, find_large_files
from .suggestions import build_suggestions
from .utils import collect_disk_info, detect_mount_points, ensure_paths


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Оптимизация и очистка дисков")
    parser.add_argument(
        "--disks",
        nargs="*",
        help="Список точек монтирования или дисков для анализа. По умолчанию все обнаруженные.",
    )
    parser.add_argument(
        "--deep-scan",
        nargs="*",
        help="Дополнительные каталоги для глубокого анализа (поверх выбора дисков).",
    )
    parser.add_argument(
        "--profile",
        choices=list(PROFILES.keys()),
        default="safe",
        help="Профиль оптимизации: fast/safe/aggressive",
    )
    parser.add_argument(
        "--chart-dir",
        default="charts",
        help="Каталог для сохранения графиков и диаграмм.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    profile = resolve_profile(args.profile)

    available_mounts = detect_mount_points()
    selected_mounts: List[Path] = []
    if args.disks:
        selected_mounts = [Path(path) for path in args.disks if Path(path).exists()]
    else:
        selected_mounts = available_mounts

    if not selected_mounts:
        print("Диски не обнаружены. Укажите точки монтирования вручную через --disks")
        return

    print(f"Выбран профиль: {profile.name} — {profile.description}")

    deep_scan_targets = ensure_paths(args.deep_scan)
    all_chart_paths: List[Path] = []

    for mount_point in selected_mounts:
        disk_info = collect_disk_info(mount_point)
        print_disk_info(disk_info)

        scan_targets = [mount_point] + deep_scan_targets
        reports = analyze_targets(scan_targets, profile)
        print_directory_reports(reports.values())

        large_files = []
        for target in scan_targets:
            large_files.extend(find_large_files(target, profile, profile.suggestion_limit))
        large_files.sort(key=lambda item: item.size, reverse=True)
        print_large_files(large_files)

        suggestions = build_suggestions(large_files, scan_targets, profile)
        print_suggestions(suggestions)

        chart_dir = Path(args.chart_dir)
        pie_path = render_disk_usage_pie(disk_info, chart_dir)
        breakdown_paths = render_directory_breakdown(reports.values(), chart_dir)
        large_files_chart = render_large_files_chart(large_files, chart_dir)

        for path in [pie_path, large_files_chart]:
            if path:
                all_chart_paths.append(path)
        all_chart_paths.extend(breakdown_paths)

    if all_chart_paths:
        print("\nГрафики сохранены:")
        print_chart_info(all_chart_paths)
    else:
        print("\nГрафики не сгенерированы (matplotlib не установлен?)")


if __name__ == "__main__":
    main()
