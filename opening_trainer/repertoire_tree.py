"""Repertoire as a move TREE — the app-owned source of truth.

A tree models a branching opening repertoire: each node is reached by exactly one
move (``move_uci``) from its parent; ``children_ids[0]`` is the main line, the
rest are variations. Node ids are stable, opaque tokens generated once at
creation — never derived from the position or move — so they survive edits,
re-parents and merges.

This module is pure data + structure operations; it does NOT need a chess board
(move legality is the loader's / UI's concern). Per-position training is derived
separately in ``position_book``.
"""
from __future__ import annotations

import secrets
from dataclasses import dataclass, field
from typing import Iterator

WHITE = "white"
BLACK = "black"
NONE = "none"
_VALID_SIDES = {WHITE, BLACK, NONE}


def _new_id() -> str:
    """Stabile, undurchsichtige Knoten-/Baum-ID (überlebt Edits/Merges)."""
    return secrets.token_hex(4)


@dataclass
class RepertoireNode:
    id: str
    move_uci: str | None              # Zug, der zu diesem Knoten führte; None = Wurzel
    parent_id: str | None
    children_ids: list[str] = field(default_factory=list)   # [0] = Hauptlinie
    comment: str = ""


@dataclass
class RepertoireTree:
    id: str
    name: str
    side: str                          # "white" | "black" | "none"
    root_id: str
    nodes: dict[str, RepertoireNode]
    headers: dict[str, str] = field(default_factory=dict)
    start_fen: str | None = None       # None = Standard-Grundstellung

    # --- Konstruktion ---------------------------------------------------
    @classmethod
    def new(cls, name: str = "", side: str = NONE, start_fen: str | None = None) -> "RepertoireTree":
        root = RepertoireNode(id=_new_id(), move_uci=None, parent_id=None)
        return cls(
            id=_new_id(),
            name=name,
            side=side if side in _VALID_SIDES else NONE,
            root_id=root.id,
            nodes={root.id: root},
            start_fen=start_fen,
        )

    # --- Zugriff --------------------------------------------------------
    @property
    def root(self) -> RepertoireNode:
        return self.nodes[self.root_id]

    def children_of(self, node_id: str) -> list[RepertoireNode]:
        return [self.nodes[c] for c in self.nodes[node_id].children_ids]

    def child_with_move(self, node_id: str, move_uci: str) -> RepertoireNode | None:
        for child in self.children_of(node_id):
            if child.move_uci == move_uci:
                return child
        return None

    def path_to(self, node_id: str) -> list[str]:
        """Zugfolge (UCI) von der Wurzel bis zu diesem Knoten."""
        moves: list[str] = []
        node = self.nodes[node_id]
        while node.parent_id is not None:
            moves.append(node.move_uci)  # type: ignore[arg-type]
            node = self.nodes[node.parent_id]
        moves.reverse()
        return moves

    def iter_nodes(self) -> Iterator[RepertoireNode]:
        return iter(self.nodes.values())

    # --- Mutationen -----------------------------------------------------
    def add_child(self, parent_id: str, move_uci: str, comment: str = "") -> RepertoireNode:
        """Hängt einen Zug an. Existiert der Zug bereits als Kind, wird der
        vorhandene Knoten zurückgegeben (keine doppelten Geschwister-Züge)."""
        existing = self.child_with_move(parent_id, move_uci)
        if existing is not None:
            if comment and not existing.comment:
                existing.comment = comment
            return existing
        node = RepertoireNode(id=_new_id(), move_uci=move_uci, parent_id=parent_id, comment=comment)
        self.nodes[node.id] = node
        self.nodes[parent_id].children_ids.append(node.id)
        return node

    def delete_subtree(self, node_id: str) -> None:
        """Entfernt einen Knoten samt allen Nachfahren. Die Wurzel bleibt."""
        if node_id == self.root_id:
            raise ValueError("Die Wurzel kann nicht gelöscht werden.")
        node = self.nodes[node_id]
        to_remove: list[str] = []
        stack = [node_id]
        while stack:
            nid = stack.pop()
            to_remove.append(nid)
            stack.extend(self.nodes[nid].children_ids)
        if node.parent_id is not None:
            self.nodes[node.parent_id].children_ids.remove(node_id)
        for nid in to_remove:
            del self.nodes[nid]

    def promote(self, node_id: str) -> None:
        """Macht den Knoten zur Hauptlinie seiner Geschwister (Index 0)."""
        node = self.nodes[node_id]
        if node.parent_id is None:
            return
        siblings = self.nodes[node.parent_id].children_ids
        siblings.remove(node_id)
        siblings.insert(0, node_id)

    def set_side(self, side: str) -> None:
        self.side = side if side in _VALID_SIDES else NONE

    # --- Serialisierung -------------------------------------------------
    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "side": self.side,
            "root_id": self.root_id,
            "start_fen": self.start_fen,
            "headers": dict(self.headers),
            "nodes": [
                {
                    "id": n.id,
                    "move_uci": n.move_uci,
                    "parent_id": n.parent_id,
                    "children_ids": list(n.children_ids),
                    "comment": n.comment,
                }
                for n in self.nodes.values()
            ],
        }

    @classmethod
    def from_dict(cls, data: dict) -> "RepertoireTree":
        nodes: dict[str, RepertoireNode] = {}
        for raw in data.get("nodes", []):
            nodes[str(raw["id"])] = RepertoireNode(
                id=str(raw["id"]),
                move_uci=raw.get("move_uci"),
                parent_id=raw.get("parent_id"),
                children_ids=[str(c) for c in raw.get("children_ids", [])],
                comment=str(raw.get("comment", "")),
            )
        return cls(
            id=str(data["id"]),
            name=str(data.get("name", "")),
            side=str(data.get("side", NONE)),
            root_id=str(data["root_id"]),
            nodes=nodes,
            headers={str(k): str(v) for k, v in data.get("headers", {}).items()},
            start_fen=data.get("start_fen"),
        )
