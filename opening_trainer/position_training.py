"""Per-position training over a repertoire TREE (replaces the linear TrainingState).

Walks a tree: opponent moves are auto-played (main line = ``children_ids[0]``),
and at each of the trained side's turns the user must produce one of the
prescribed moves (the node's children). The graded unit is the POSITION
(``board.epd()``), so the schedule/stats are per-position and transpositions
share one card. Reuses ``MoveResult``/``Solution`` so the UI feedback is unchanged.

v1 scope (see plan): one tree, opponent follows the main line, "any prescribed
move is correct". Enumerated-branch drilling is a later phase.
"""
from __future__ import annotations

import chess

from opening_trainer.repertoire_tree import RepertoireTree
from opening_trainer.training_state import MoveResult, Solution


def _start_board(tree: RepertoireTree) -> chess.Board:
    return chess.Board(tree.start_fen) if tree.start_fen else chess.Board()


class PositionTrainer:
    def __init__(self, tree: RepertoireTree, side: chess.Color, start_node_id: str | None = None,
                 opponent_pick=None) -> None:
        self.tree = tree
        self.side = side
        # Welcher Gegnerzug an einer Verzweigung gespielt wird. Standard: Hauptlinie
        # (deterministisch/testbar). Der Drill kann hier zufällig wählen, um ALLE
        # vorbereiteten Äste abzudecken.
        self._opponent_pick = opponent_pick or (lambda children: children[0])
        self.board = _start_board(tree)
        self.node = tree.root
        self.last_move_uci: str | None = None
        self.last_wrong_uci: str | None = None
        self.last_card_epd: str | None = None     # die zuletzt benotete Stellung (für den Lernplan)
        if start_node_id and start_node_id in tree.nodes:
            for uci in tree.path_to(start_node_id):
                move = chess.Move.from_uci(uci)
                if move not in self.board.legal_moves:
                    break
                self.board.push(move)
                self.last_move_uci = uci
            self.node = tree.nodes[start_node_id]
        self._auto_advance()

    # --- Navigation -----------------------------------------------------
    def _is_user_turn(self) -> bool:
        return self.board.turn == self.side

    def _auto_advance(self) -> list[tuple[str, str]]:
        """Spielt Gegnerzüge (Hauptlinie) bis die trainierte Seite am Zug ist."""
        replies: list[tuple[str, str]] = []
        while not self._is_user_turn():
            children = self.tree.children_of(self.node.id)
            if not children:
                break
            child = self._opponent_pick(children)
            move = chess.Move.from_uci(child.move_uci) if child.move_uci else None
            if move is None or move not in self.board.legal_moves:
                break
            san = self.board.san(move)
            self.board.push(move)
            self.node = child
            self.last_move_uci = child.move_uci
            replies.append((san, child.move_uci))
        return replies

    def is_finished(self) -> bool:
        return not self._is_user_turn() or not self.tree.children_of(self.node.id)

    def current_epd(self) -> str | None:
        """EPD der Stellung, in der die trainierte Seite jetzt ziehen muss."""
        return None if self.is_finished() else self.board.epd()

    def expected_moves(self) -> set[str]:
        """Vorgesehene eigene Züge (UCI) in der aktuellen Stellung."""
        if self.is_finished():
            return set()
        return {c.move_uci for c in self.tree.children_of(self.node.id) if c.move_uci}

    def expected_solution(self) -> Solution | None:
        if self.is_finished():
            return None
        child = self.tree.children_of(self.node.id)[0]
        move = chess.Move.from_uci(child.move_uci)
        if move not in self.board.legal_moves:
            return None
        return Solution(san=self.board.san(move), uci=child.move_uci)

    # --- Spielen --------------------------------------------------------
    def play_user_move_uci(self, move_uci: str) -> MoveResult:
        self.last_wrong_uci = None
        self.last_card_epd = None

        if self.is_finished():
            return MoveResult(kind="finished", message="Linie ist bereits beendet.")

        try:
            played = chess.Move.from_uci(move_uci)
        except ValueError:
            sol = self.expected_solution()
            return MoveResult("wrong", "Ungültige Zugeingabe.",
                              expected_san=sol.san if sol else None, played_san=move_uci)

        if played not in self.board.legal_moves:
            sol = self.expected_solution()
            self.last_wrong_uci = played.uci()
            return MoveResult("wrong", "Illegaler Zug.",
                              expected_san=sol.san if sol else None,
                              played_san=move_uci, wrong_uci=played.uci())

        played_san = self.board.san(played)
        sol = self.expected_solution()
        if played.uci() not in self.expected_moves():
            self.last_wrong_uci = played.uci()
            return MoveResult("wrong", "Falscher Zug.",
                              expected_san=sol.san if sol else None,
                              played_san=played_san, wrong_uci=played.uci())

        # Richtig: Stellung benoten (epd), in das passende Kind weitergehen.
        self.last_card_epd = self.board.epd()
        child = self.tree.child_with_move(self.node.id, played.uci())
        self.board.push(played)
        self.node = child
        self.last_move_uci = played.uci()

        replies = self._auto_advance()
        auto_san, auto_uci = (replies[-1] if replies else (None, None))

        if self.is_finished():
            message = "Richtig. Linie abgeschlossen."
        elif auto_san:
            message = f"Richtig. Programm spielt: {auto_san}"
        else:
            message = "Richtig."

        return MoveResult(
            kind="correct",
            message=message,
            expected_san=played_san,
            played_san=played_san,
            last_move_uci=self.last_move_uci,
            auto_reply_san=auto_san,
            auto_reply_uci=auto_uci,
        )
