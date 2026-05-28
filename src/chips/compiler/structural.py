"""Structural retrieval via tree-sitter AST parsing.

Parses function/class definitions from source files and builds a lightweight
call graph. Returns budget-aware context: definitions are added hop by hop
outward from anchor symbols until the token budget is exhausted.

Supported languages: Python, JavaScript/TypeScript.
Falls back gracefully (returns empty list) if tree-sitter is unavailable or
a file cannot be parsed.
"""
from __future__ import annotations

import logging
import os
from dataclasses import dataclass, field
from pathlib import Path

logger = logging.getLogger(__name__)

try:
    import tree_sitter_python as _tspython
    import tree_sitter_javascript as _tsjs
    from tree_sitter import Language, Parser, Node
    _TS_AVAILABLE = True
except ImportError:
    _TS_AVAILABLE = False

_LANG_CACHE: dict[str, object] = {}


def _get_language(ext: str) -> object | None:
    if not _TS_AVAILABLE:
        return None
    if ext in _LANG_CACHE:
        return _LANG_CACHE[ext]
    try:
        if ext in (".py",):
            lang = Language(_tspython.language())  # type: ignore[arg-type]
        elif ext in (".js", ".mjs", ".cjs"):
            lang = Language(_tsjs.language())  # type: ignore[arg-type]
        elif ext in (".ts", ".tsx"):
            try:
                import tree_sitter_typescript as _tsts
                lang = Language(_tsts.language_typescript())  # type: ignore[arg-type]
            except Exception:
                return None
        else:
            return None
        _LANG_CACHE[ext] = lang
        return lang
    except Exception as exc:
        logger.debug("tree-sitter language load failed for %s: %s", ext, exc)
        return None


@dataclass(frozen=True)
class StructuralSymbol:
    name: str
    kind: str  # "function" | "class" | "method"
    file_path: str
    start_line: int
    end_line: int
    body_text: str
    callees: list[str] = field(default_factory=list)


def _extract_symbols(source: bytes, file_path: str, lang: object) -> list[StructuralSymbol]:
    """Parse source and extract function/class definitions with call targets."""
    try:
        parser = Parser(lang)  # type: ignore[arg-type]
        tree = parser.parse(source)
    except Exception as exc:
        logger.debug("parse failed for %s: %s", file_path, exc)
        return []

    symbols: list[StructuralSymbol] = []
    lines = source.decode("utf-8", errors="replace").splitlines()

    def visit(node: "Node") -> None:  # type: ignore[name-defined]
        if node.type in ("function_definition", "function_declaration",
                          "method_definition", "arrow_function",
                          "class_definition", "class_declaration"):
            name = ""
            for child in node.children:
                if child.type == "identifier":
                    name = child.text.decode("utf-8", errors="replace") if child.text else ""
                    break
            if not name:
                for child in node.children:
                    for grandchild in child.children:
                        if grandchild.type == "identifier":
                            name = grandchild.text.decode("utf-8", errors="replace") if grandchild.text else ""
                            break
                    if name:
                        break

            kind_map = {
                "function_definition": "function",
                "function_declaration": "function",
                "method_definition": "method",
                "arrow_function": "function",
                "class_definition": "class",
                "class_declaration": "class",
            }
            kind = kind_map.get(node.type, "function")
            start = node.start_point[0]
            end = node.end_point[0]
            body = "\n".join(lines[start:end + 1])

            # Collect call targets within this definition
            callees: list[str] = []
            _collect_calls(node, callees)

            if name:
                symbols.append(StructuralSymbol(
                    name=name,
                    kind=kind,
                    file_path=file_path,
                    start_line=start + 1,
                    end_line=end + 1,
                    body_text=body,
                    callees=list(dict.fromkeys(callees)),  # deduplicate preserving order
                ))

        for child in node.children:
            visit(child)

    visit(tree.root_node)
    return symbols


def _collect_calls(node: "Node", out: list[str]) -> None:  # type: ignore[name-defined]
    """Recursively collect identifiers used in call expressions."""
    if node.type in ("call", "call_expression"):
        func = node.child_by_field_name("function") or node.child_by_field_name("callee")
        if func is not None:
            name = ""
            if func.type == "identifier" and func.text:
                name = func.text.decode("utf-8", errors="replace")
            elif func.type in ("attribute", "member_expression"):
                for child in func.children:
                    if child.type == "identifier" and child.text:
                        name = child.text.decode("utf-8", errors="replace")
            if name:
                out.append(name)
    for child in node.children:
        _collect_calls(child, out)


def retrieve_structural(
    file_paths: list[str],
    *,
    anchor_names: list[str] | None = None,
    token_budget: int = 2000,
    hop_depth: int = 2,
) -> list[dict]:
    """Return structural context for the given files within the token budget.

    Performs a BFS outward from anchor symbols (or top-level symbols if none
    given), adding symbol definitions until the budget is exhausted.

    Returns a list of dicts suitable for creating SoftContextItems:
        {"item_id": str, "text": str, "kind": str, "file": str, "callees": list[str]}
    """
    if not _TS_AVAILABLE or not file_paths:
        return []

    # Parse all files
    all_symbols: dict[str, StructuralSymbol] = {}
    for fp in file_paths:
        path = Path(fp)
        if not path.exists():
            continue
        ext = path.suffix.lower()
        lang = _get_language(ext)
        if lang is None:
            continue
        try:
            source = path.read_bytes()
        except OSError as exc:
            logger.debug("cannot read %s: %s", fp, exc)
            continue
        for sym in _extract_symbols(source, fp, lang):
            all_symbols[sym.name] = sym

    if not all_symbols:
        return []

    # BFS from anchors
    anchors = anchor_names or list(all_symbols.keys())[:5]
    visited: set[str] = set()
    queue: list[str] = [a for a in anchors if a in all_symbols]
    results: list[dict] = []
    tokens_used = 0

    # Approximate token count: chars / 4 (tiktoken optional overhead avoidance here)
    def _tok(text: str) -> int:
        return max(1, len(text) // 4)

    depth_map: dict[str, int] = {name: 0 for name in queue}

    while queue:
        name = queue.pop(0)
        if name in visited:
            continue
        visited.add(name)
        sym = all_symbols.get(name)
        if sym is None:
            continue

        cost = _tok(sym.body_text)
        if tokens_used + cost > token_budget:
            break

        results.append({
            "item_id": f"struct:{sym.file_path}:{sym.name}",
            "text": f"[{sym.kind}] {sym.name} ({os.path.basename(sym.file_path)}:{sym.start_line})\n{sym.body_text}",
            "kind": sym.kind,
            "file": sym.file_path,
            "callees": sym.callees,
        })
        tokens_used += cost

        # Enqueue callees if within hop depth
        current_depth = depth_map.get(name, 0)
        if current_depth < hop_depth:
            for callee in sym.callees:
                if callee not in visited and callee in all_symbols:
                    depth_map.setdefault(callee, current_depth + 1)
                    queue.append(callee)

    return results
