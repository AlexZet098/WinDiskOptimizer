from __future__ import annotations

import threading
import tkinter as tk
from dataclasses import dataclass
from pathlib import Path
from tkinter import filedialog, messagebox, ttk
from typing import Iterable, List

from .charts import (
    build_directory_breakdown_figure,
    build_disk_usage_figure,
    build_large_files_figure,
    matplotlib_ready,
)
from .profiles import PROFILES, OptimizationProfile, resolve_profile
from .scanner import ItemUsage, analyze_targets, find_large_files
from .suggestions import Suggestion, build_suggestions
from .utils import collect_disk_info, detect_mount_points, ensure_paths, format_size


@dataclass
class ChartVisual:
    title: str
    figure: object


@dataclass
class ScanResult:
    text: str
    charts: List[ChartVisual]


def _format_disk_section(
    disk_path: Path,
    profile: OptimizationProfile,
    deep_scan_targets: List[Path],
    chart_mode: str,
) -> tuple[str, List[ChartVisual]]:
    lines: List[str] = []
    visuals: List[ChartVisual] = []
    disk_info = collect_disk_info(disk_path)
    lines.append(f"Диск: {disk_info.mount_point}")
    lines.append(f"  Всего: {format_size(disk_info.total)}")
    lines.append(f"  Использовано: {format_size(disk_info.used)} ({disk_info.usage_percent:.1f}%)")
    lines.append(f"  Свободно: {format_size(disk_info.free)}")

    scan_targets = [disk_path] + deep_scan_targets
    reports = analyze_targets(scan_targets, profile)

    for report in reports.values():
        lines.append("")
        lines.append(f"Каталог: {report.root}")
        lines.append(f"  Размер: {format_size(report.total_size)}")
        lines.append(f"  Файлов: {report.files}, Папок: {report.directories}")
        for child in report.children[:10]:
            marker = "[D]" if child.is_dir else "[F]"
            lines.append(f"    {marker} {child.path} — {format_size(child.size)}")

    large_files: List[ItemUsage] = []
    for target in scan_targets:
        large_files.extend(find_large_files(target, profile, profile.suggestion_limit))
    large_files.sort(key=lambda item: item.size, reverse=True)

    if large_files:
        lines.append("\nКрупные файлы:")
        for item in large_files[:20]:
            lines.append(f"  {item.path} — {format_size(item.size)}")
    else:
        lines.append("\nКрупные файлы не найдены по заданным порогам.")

    suggestions: Iterable[Suggestion] = build_suggestions(large_files, scan_targets, profile)
    lines.append("\nПредложения по очистке:")
    for suggestion in suggestions:
        lines.append(f"  {suggestion.path}")
        lines.append(f"    Причина: {suggestion.reason}")
        lines.append(f"    Можно освободить: {format_size(suggestion.reclaimable)}")
        lines.append(f"    Риск: {suggestion.risk}")

    disk_chart = build_disk_usage_figure(disk_info)
    if disk_chart:
        visuals.append(ChartVisual(title=f"{disk_info.mount_point} — использование", figure=disk_chart))

    for report in reports.values():
        chart = build_directory_breakdown_figure(report, chart_type=chart_mode)
        if chart:
            visuals.append(ChartVisual(title=f"{report.root} — разбивка", figure=chart))

    large_files_chart = build_large_files_figure(large_files)
    if large_files_chart:
        visuals.append(ChartVisual(title=f"{disk_info.mount_point} — крупные файлы", figure=large_files_chart))

    if not visuals and not matplotlib_ready():
        lines.append("\nГрафики не отображены: matplotlib недоступен.")

    return "\n".join(lines), visuals


class DiskOptimizerApp:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title("WinDiskOptimizer — визуальный интерфейс")
        self.root.geometry("950x650")

        self.profile_var = tk.StringVar(value="safe")
        self.chart_mode_var = tk.StringVar(value="bar")
        self.deep_scan_paths: List[Path] = []
        self.scanning = False
        self.chart_canvases: List[object] = []

        self._build_layout()
        self._load_mounts()

    def _build_layout(self) -> None:
        main = ttk.Frame(self.root, padding=10)
        main.pack(fill=tk.BOTH, expand=True)

        left = ttk.Frame(main)
        left.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 10))

        ttk.Label(left, text="Доступные диски").pack(anchor=tk.W)
        self.mount_list = tk.Listbox(left, selectmode=tk.MULTIPLE, height=8)
        self.mount_list.pack(fill=tk.X)

        btn_frame = ttk.Frame(left)
        btn_frame.pack(fill=tk.X, pady=5)
        ttk.Button(btn_frame, text="Обновить", command=self._load_mounts).pack(side=tk.LEFT, expand=True, fill=tk.X)
        ttk.Button(btn_frame, text="Сканировать", command=self.start_scan).pack(side=tk.LEFT, expand=True, fill=tk.X, padx=(5, 0))

        ttk.Label(left, text="Профиль оптимизации").pack(anchor=tk.W, pady=(10, 0))
        for key, profile in PROFILES.items():
            ttk.Radiobutton(left, text=f"{profile.name} — {profile.description}", variable=self.profile_var, value=key).pack(
                anchor=tk.W
            )

        ttk.Label(left, text="Тип диаграммы для разбивки").pack(anchor=tk.W, pady=(10, 0))
        chart_mode = ttk.Frame(left)
        chart_mode.pack(fill=tk.X)
        ttk.Radiobutton(chart_mode, text="Гистограмма", variable=self.chart_mode_var, value="bar").pack(
            side=tk.LEFT, expand=True, fill=tk.X
        )
        ttk.Radiobutton(chart_mode, text="Круговая", variable=self.chart_mode_var, value="pie").pack(
            side=tk.LEFT, expand=True, fill=tk.X
        )

        ttk.Label(left, text="Глубокий скан").pack(anchor=tk.W, pady=(10, 0))
        self.deep_list = tk.Listbox(left, height=6)
        self.deep_list.pack(fill=tk.X)

        deep_btns = ttk.Frame(left)
        deep_btns.pack(fill=tk.X, pady=5)
        ttk.Button(deep_btns, text="Добавить", command=self.add_deep_scan).pack(side=tk.LEFT, expand=True, fill=tk.X)
        ttk.Button(deep_btns, text="Удалить", command=self.remove_deep_scan).pack(
            side=tk.LEFT, expand=True, fill=tk.X, padx=(5, 0)
        )

        right = ttk.Frame(main)
        right.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        header = ttk.Frame(right)
        header.pack(fill=tk.X)
        self.status_label = ttk.Label(header, text="Готов к сканированию")
        self.status_label.pack(side=tk.LEFT)

        self.chart_notice = ttk.Label(right, text="Графики появятся после сканирования")
        self.chart_notice.pack(anchor=tk.W, pady=(5, 0))

        self.chart_notebook = ttk.Notebook(right)
        self.chart_notebook.pack(fill=tk.BOTH, expand=True, pady=(5, 0))

        self.output = tk.Text(right, wrap=tk.WORD, height=10)
        self.output.pack(fill=tk.BOTH, expand=True, pady=(5, 0))

    def _load_mounts(self) -> None:
        mounts = detect_mount_points()
        self.mount_list.delete(0, tk.END)
        for mount in mounts:
            self.mount_list.insert(tk.END, str(mount))
        self.status_label.config(text="Диски обновлены")

    def add_deep_scan(self) -> None:
        selection = filedialog.askdirectory(title="Выберите папку для глубокого сканирования")
        if not selection:
            return
        path = Path(selection)
        if path.exists() and path not in self.deep_scan_paths:
            self.deep_scan_paths.append(path)
            self.deep_list.insert(tk.END, str(path))

    def remove_deep_scan(self) -> None:
        selected = list(self.deep_list.curselection())
        selected.reverse()
        for index in selected:
            self.deep_list.delete(index)
            del self.deep_scan_paths[index]

    def start_scan(self) -> None:
        if self.scanning:
            return
        selected_indices = self.mount_list.curselection()
        selected_mounts = [self.mount_list.get(i) for i in selected_indices]
        if not selected_mounts:
            selected_mounts = list(self.mount_list.get(0, tk.END))
        if not selected_mounts:
            messagebox.showinfo("Нет дисков", "Диски не обнаружены. Добавьте точки монтирования вручную через CLI.")
            return

        profile = resolve_profile(self.profile_var.get())
        deep_scan_targets = ensure_paths([str(p) for p in self.deep_scan_paths])
        chart_mode = self.chart_mode_var.get()

        self.scanning = True
        self.status_label.config(text="Идёт анализ...")
        self.output.delete("1.0", tk.END)
        self._clear_charts()
        self.chart_notice.config(text="Выполняется построение графиков...")

        thread = threading.Thread(
            target=self._execute_scan, args=(selected_mounts, profile, deep_scan_targets, chart_mode), daemon=True
        )
        thread.start()

    def _execute_scan(
        self, selected_mounts: List[str], profile: OptimizationProfile, deep_scan_targets: List[Path], chart_mode: str
    ) -> None:
        lines: List[str] = []
        visuals: List[ChartVisual] = []
        lines.append(f"Выбран профиль: {profile.name} — {profile.description}\n")

        for mount in selected_mounts:
            disk_path = Path(mount)
            if not disk_path.exists():
                lines.append(f"Диск {mount} недоступен")
                continue
            section, section_charts = _format_disk_section(disk_path, profile, deep_scan_targets, chart_mode)
            lines.append(section)
            visuals.extend(section_charts)
            lines.append("\n" + "-" * 40 + "\n")

        result = ScanResult("\n".join(lines), visuals)
        self.root.after(0, self._on_scan_complete, result)

    def _on_scan_complete(self, result: ScanResult) -> None:
        self.scanning = False
        self.status_label.config(text="Анализ завершён")
        self.output.insert(tk.END, result.text)
        self._display_charts(result.charts)

    def _clear_charts(self) -> None:
        for tab_id in self.chart_notebook.tabs():
            self.chart_notebook.forget(tab_id)
        self.chart_canvases.clear()

    def _display_charts(self, charts: List[ChartVisual]) -> None:
        if not charts:
            if not matplotlib_ready():
                self.chart_notice.config(text="Matplotlib не установлен: графики недоступны")
            else:
                self.chart_notice.config(text="Данные для построения графиков отсутствуют")
            return

        try:
            from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
        except ImportError:
            self.chart_notice.config(text="Matplotlib бэкенд недоступен")
            return

        self.chart_notice.config(text="Наведите курсор на сектор, чтобы увидеть путь и размер")
        for visual in charts:
            frame = ttk.Frame(self.chart_notebook)
            canvas = FigureCanvasTkAgg(visual.figure, master=frame)
            canvas.draw()
            widget = canvas.get_tk_widget()
            widget.pack(fill=tk.BOTH, expand=True)
            self.chart_canvases.append(canvas)
            tab_title = visual.title if len(visual.title) <= 32 else visual.title[:31] + "…"
            self.chart_notebook.add(frame, text=tab_title)


def main() -> None:
    root = tk.Tk()
    app = DiskOptimizerApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
