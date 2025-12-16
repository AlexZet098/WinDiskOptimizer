from __future__ import annotations

import importlib.util
from pathlib import Path
from typing import Iterable, List, Sequence

from .scanner import DirectoryReport, ItemUsage
from .utils import DiskInfo, format_size


def _matplotlib_available() -> bool:
    return importlib.util.find_spec("matplotlib") is not None


def matplotlib_ready() -> bool:
    """Return True when matplotlib is available for rendering charts."""

    return _matplotlib_available()


def _add_hover_tooltips(ax, artists: Sequence, labels: Sequence[str], sizes: Sequence[int]) -> None:
    """Attach hover tooltips to matplotlib artists showing label and size."""

    fig = ax.figure
    annotation = ax.annotate(
        "",
        xy=(0, 0),
        xytext=(10, 10),
        textcoords="offset points",
        bbox=dict(boxstyle="round", fc="w"),
        arrowprops=dict(arrowstyle="->"),
    )
    annotation.set_visible(False)

    def on_move(event):
        if event.inaxes != ax:
            if annotation.get_visible():
                annotation.set_visible(False)
                fig.canvas.draw_idle()
            return

        for artist, label, size in zip(artists, labels, sizes):
            contains, _ = artist.contains(event)
            if contains:
                annotation.xy = (event.xdata, event.ydata)
                annotation.set_text(f"{label}\n{format_size(size)}")
                annotation.set_visible(True)
                fig.canvas.draw_idle()
                return

        if annotation.get_visible():
            annotation.set_visible(False)
            fig.canvas.draw_idle()

    fig.canvas.mpl_connect("motion_notify_event", on_move)


def build_disk_usage_figure(disk: DiskInfo):
    """Create a pie chart figure for used vs free disk space."""

    if not _matplotlib_available():
        return None

    import matplotlib.pyplot as plt

    fig, ax = plt.subplots(figsize=(5, 4))
    wedges, _ = ax.pie([disk.used, disk.free], labels=["Использовано", "Свободно"], autopct="%1.1f%%")
    ax.set_title(f"{disk.mount_point} — использование диска")
    _add_hover_tooltips(ax, wedges, ["Использовано", "Свободно"], [disk.used, disk.free])
    fig.tight_layout()
    return fig


def build_directory_breakdown_figure(report: DirectoryReport, chart_type: str = "bar"):
    """Create a chart showing the largest children inside a directory."""

    if not _matplotlib_available() or not report.children:
        return None

    import matplotlib.pyplot as plt

    top_children = report.children[:15]
    labels = [child.path.name or child.path.as_posix() for child in top_children]
    hover_labels = [child.path.as_posix() for child in top_children]
    sizes = [child.size for child in top_children]

    fig, ax = plt.subplots(figsize=(8, 4))
    if chart_type == "pie":
        wedges, _ = ax.pie(sizes, labels=labels, autopct="%1.1f%%")
        ax.set_title(f"{report.root} — доли каталогов/файлов")
        _add_hover_tooltips(ax, wedges, hover_labels, sizes)
    else:
        bars = ax.barh(labels, sizes)
        ax.set_xlabel("Размер (байт)")
        ax.set_title(f"{report.root} — крупнейшие элементы")
        fig.tight_layout()
        _add_hover_tooltips(ax, bars, hover_labels, sizes)
    return fig


def build_large_files_figure(items: List[ItemUsage]):
    """Create a bar chart for the largest files found."""

    if not _matplotlib_available() or not items:
        return None

    import matplotlib.pyplot as plt

    top_items = items[:15]
    labels = [item.path.name for item in top_items]
    hover_labels = [item.path.as_posix() for item in top_items]
    sizes = [item.size for item in top_items]

    fig, ax = plt.subplots(figsize=(8, 4))
    bars = ax.bar(labels, sizes)
    ax.set_ylabel("Размер (байт)")
    ax.set_title("Крупные файлы")
    fig.autofmt_xdate(rotation=45)
    fig.tight_layout()
    _add_hover_tooltips(ax, bars, hover_labels, sizes)
    return fig


def _save_figure(figure, output: Path) -> Path:
    output.parent.mkdir(parents=True, exist_ok=True)
    figure.savefig(output, bbox_inches="tight")
    try:
        import matplotlib.pyplot as plt

        plt.close(figure)
    except Exception:
        pass
    return output


def render_disk_usage_pie(disk: DiskInfo, chart_dir: Path) -> Path | None:
    fig = build_disk_usage_figure(disk)
    if not fig:
        return None
    output = chart_dir / f"{disk.mount_point.as_posix().replace('/', '_')}_usage.png"
    return _save_figure(fig, output)


def render_directory_breakdown(reports: Iterable[DirectoryReport], chart_dir: Path) -> List[Path]:
    generated: List[Path] = []
    for report in reports:
        fig = build_directory_breakdown_figure(report)
        if not fig:
            continue
        output = chart_dir / f"{report.root.as_posix().replace('/', '_')}_breakdown.png"
        generated.append(_save_figure(fig, output))
    return generated


def render_large_files_chart(items: List[ItemUsage], chart_dir: Path) -> Path | None:
    fig = build_large_files_figure(items)
    if not fig:
        return None
    output = chart_dir / "large_files.png"
    return _save_figure(fig, output)
