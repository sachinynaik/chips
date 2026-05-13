from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class Policy:
    scope: str
    forbidden: list[str] = field(default_factory=list)
    required: list[str] = field(default_factory=list)


class PolicyLoader:
    def __init__(self, policies: list[Policy]) -> None:
        self._policies = policies

    def for_scope(self, scope: str | None) -> list[Policy]:
        return [
            p for p in self._policies
            if p.scope == "*" or p.scope == scope
        ]

    @classmethod
    def from_yaml_string(cls, text: str) -> PolicyLoader:
        import yaml
        data = yaml.safe_load(text) or {}
        return cls(_parse_policies(data))

    @classmethod
    def from_file(cls, path: str) -> PolicyLoader:
        try:
            with open(path, encoding="utf-8") as f:
                import yaml
                data = yaml.safe_load(f) or {}
            return cls(_parse_policies(data))
        except FileNotFoundError:
            return cls([])


def _parse_policies(data: dict) -> list[Policy]:
    return [
        Policy(
            scope=entry["scope"],
            forbidden=list(entry.get("forbidden") or []),
            required=list(entry.get("required") or []),
        )
        for entry in (data.get("policies") or [])
    ]
