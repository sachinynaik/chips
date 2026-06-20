from __future__ import annotations

from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path


def test_all_down_revisions_reference_existing_revision_ids():
    versions_dir = Path("migrations/versions")
    revisions: dict[str, object] = {}
    down_revisions: dict[str, object] = {}

    for path in versions_dir.glob("*.py"):
        if path.name == "__init__.py":
            continue
        spec = spec_from_file_location(path.stem, path)
        module = module_from_spec(spec)
        assert spec and spec.loader
        spec.loader.exec_module(module)
        revisions[module.revision] = path.name
        down_revisions[module.revision] = module.down_revision

    for revision, down_revision in down_revisions.items():
        if down_revision is None:
            continue
        if isinstance(down_revision, str):
            assert down_revision in revisions, (
                f"{revision} references missing down_revision {down_revision!r}"
            )
            continue
        for parent in down_revision:
            assert parent in revisions, (
                f"{revision} references missing down_revision {parent!r}"
            )
