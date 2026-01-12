from __future__ import annotations

from dataclasses import dataclass
from typing import Dict


@dataclass(frozen=True)
class OptimizationProfile:
    name: str
    description: str
    max_depth: int
    large_file_threshold: int
    suggestion_limit: int
    follow_symlinks: bool


PROFILES: Dict[str, OptimizationProfile] = {
    "fast": OptimizationProfile(
        name="Быстро",
        description="Поверхностный анализ, только верхний уровень каталогов.",
        max_depth=1,
        large_file_threshold=250 * 1024 * 1024,
        suggestion_limit=10,
        follow_symlinks=False,
    ),
    "safe": OptimizationProfile(
        name="Безопасно",
        description="Сбалансированный анализ с глубоким сканированием общих каталогов.",
        max_depth=2,
        large_file_threshold=150 * 1024 * 1024,
        suggestion_limit=20,
        follow_symlinks=False,
    ),
    "aggressive": OptimizationProfile(
        name="Агрессивно",
        description="Максимально глубокий анализ, включает симлинки и большие файлы.",
        max_depth=4,
        large_file_threshold=75 * 1024 * 1024,
        suggestion_limit=40,
        follow_symlinks=True,
    ),
}


def resolve_profile(alias: str | None) -> OptimizationProfile:
    if not alias:
        return PROFILES["safe"]
    normalized = alias.lower()
    if normalized in PROFILES:
        return PROFILES[normalized]
    raise ValueError(f"Неизвестный профиль оптимизации: {alias}")
