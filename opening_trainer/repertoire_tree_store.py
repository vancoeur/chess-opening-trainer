"""Persists repertoire trees as local JSON — the app-owned source of truth.

Mirrors the other stores' ``to_dict``/``from_dict``/``save``/``load`` pattern;
each tree serializes via ``RepertoireTree.to_dict``. File: ``repertoire_trees.json``.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from opening_trainer.repertoire_tree import RepertoireTree


class RepertoireTreeStore:
    def __init__(self) -> None:
        self.trees: dict[str, RepertoireTree] = {}

    def add(self, tree: RepertoireTree) -> None:
        self.trees[tree.id] = tree

    def remove(self, tree_id: str) -> None:
        self.trees.pop(tree_id, None)

    def get(self, tree_id: str) -> RepertoireTree | None:
        return self.trees.get(tree_id)

    def all(self) -> list[RepertoireTree]:
        return list(self.trees.values())

    def by_side(self, side: str) -> list[RepertoireTree]:
        return [t for t in self.trees.values() if t.side == side]

    def to_dict(self) -> dict:
        return {"trees": [t.to_dict() for t in self.trees.values()]}

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "RepertoireTreeStore":
        store = cls()
        for raw in data.get("trees", []):
            try:
                tree = RepertoireTree.from_dict(raw)
            except (KeyError, TypeError, ValueError):
                continue
            store.trees[tree.id] = tree
        return store

    def save(self, path: str | Path) -> None:
        p = Path(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(self.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8")

    @classmethod
    def load(cls, path: str | Path) -> "RepertoireTreeStore":
        p = Path(path)
        if not p.exists():
            return cls()
        try:
            data = json.loads(p.read_text(encoding="utf-8"))
            if not isinstance(data, dict):
                return cls()
            return cls.from_dict(data)
        except (json.JSONDecodeError, KeyError, TypeError, ValueError):
            return cls()
