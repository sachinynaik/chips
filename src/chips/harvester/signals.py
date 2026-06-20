from __future__ import annotations

from collections.abc import Iterable, Mapping
import math
from typing import Literal


GeneratedKind = Literal["generated", "scaffolded"]

_SCAFFOLDED_SEGMENTS = (
    "/migrations/",
    "/alembic/versions/",
    "/scaffold/",
    "/scaffolds/",
)
_GENERATED_SEGMENTS = (
    "/__generated__/",
    "/generated/",
    "/gen/",
)
_GENERATED_MARKERS = (
    ".generated.",
    "_generated.",
    ".gen.",
    ".g.",
    ".pb.",
)


def classify_generated_kind(file_path: str) -> GeneratedKind | None:
    normalized = file_path.replace("\\", "/").casefold()
    wrapped = f"/{normalized.strip('/')}/"
    if any(segment in wrapped for segment in _SCAFFOLDED_SEGMENTS):
        return "scaffolded"
    if any(segment in wrapped for segment in _GENERATED_SEGMENTS):
        return "generated"
    if any(marker in normalized for marker in _GENERATED_MARKERS):
        return "generated"
    return None


def normalized_entropy(frequencies: Iterable[float | int]) -> float:
    values = [float(freq) for freq in frequencies if freq > 0]
    if len(values) <= 1:
        return 0.0
    total = sum(values)
    if total <= 0:
        return 0.0
    entropy = 0.0
    for value in values:
        probability = value / total
        entropy -= probability * math.log(probability)
    normalized = entropy / math.log(len(values))
    if math.isclose(normalized, 1.0, rel_tol=1e-12, abs_tol=1e-12):
        return 1.0
    return max(0.0, min(normalized, 1.0))


def cochange_entropy_for_file(
    file_path: str,
    partner_frequencies: Mapping[str, float | int],
) -> float:
    if classify_generated_kind(file_path) is not None:
        return 0.0
    real_partner_frequencies = [
        frequency
        for partner, frequency in partner_frequencies.items()
        if classify_generated_kind(partner) is None
    ]
    return normalized_entropy(real_partner_frequencies)
