from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

import chess

from opening_trainer.pgn_loader import OpeningLine


ResultKind = Literal["correct", "wrong", "finished"]


@dataclass(frozen=True)
class MoveResult:
    kind: ResultKind
    message: str
    expected_san: str | None = None
    played_san: str | None = None
    wrong_uci: str | None = None
    last_move_uci: str | None = None
    auto_reply_san: str | None = None
    auto_reply_uci: str | None = None


@dataclass(frozen=True)
class Solution:
    san: str
    uci: str


class TrainingState:
    """Trainingslogik ohne GUI.

    train_color bestimmt, welche Seite der Nutzer trainiert.
    - Weiß: Nutzer beginnt, Programm antwortet mit Schwarz.
    - Schwarz: Programm spielt den ersten weißen Zug automatisch, Nutzer antwortet mit Schwarz.
    """

    def __init__(self, line: OpeningLine, train_color: chess.Color = chess.WHITE) -> None:
        self.line = line
        self.train_color = train_color
        self.board = chess.Board()
        self.ply_index = 0
        self.history: list[tuple[str, int]] = []
        self.last_wrong_uci: str | None = None
        self.last_move_uci: str | None = None
        self.section_limit_ply: int | None = None
        self._auto_advance_to_user_turn()

    def restart(self) -> None:
        self.board.reset()
        self.ply_index = 0
        self.history.clear()
        self.last_wrong_uci = None
        self.last_move_uci = None
        self._auto_advance_to_user_turn()

    def jump_to_fen(self, fen: str) -> bool:
        """Springt innerhalb der aktuellen Variante zu einer bekannten Stellung.

        Die Stellung wird nur akzeptiert, wenn sie beim Nachspielen der
        PGN-Hauptvariante tatsächlich erreicht wird. Dadurch bleibt die PGN
        die Autorität für den erwarteten nächsten Zug.
        """
        probe = chess.Board()

        if probe.fen() == fen:
            self.board = probe
            self.ply_index = 0
            self.history.clear()
            self.last_wrong_uci = None
            self.last_move_uci = None
            self._auto_advance_to_user_turn()
            return True

        for index, move_uci in enumerate(self.line.moves_uci):
            move = chess.Move.from_uci(move_uci)
            if move not in probe.legal_moves:
                return False

            probe.push(move)

            if probe.fen() == fen:
                self.board = probe
                self.ply_index = index + 1
                self.history.clear()
                self.last_wrong_uci = None
                self.last_move_uci = move.uci()
                self._auto_advance_to_user_turn()
                return True

        return False

    def restart_full_line(self) -> None:
        self.section_limit_ply = None
        self.restart()

    def repeat_until_here(self) -> str:
        if self.ply_index <= 0:
            return "Noch kein Abschnitt erreicht."

        self.section_limit_ply = self.ply_index
        self.restart()
        return "Abschnitt neu gestartet."

    def _is_user_turn(self) -> bool:
        return self.board.turn == self.train_color

    def _auto_advance_to_user_turn(self) -> list[tuple[str, str]]:
        """Spielt PGN-Züge automatisch, bis die trainierte Seite am Zug ist.

        Gibt die automatisch gespielten Züge als Liste von (san, uci) zurück.
        """
        replies: list[tuple[str, str]] = []

        while self.ply_index < self.active_limit() and not self._is_user_turn():
            move = chess.Move.from_uci(self.line.moves_uci[self.ply_index])
            if move not in self.board.legal_moves:
                break
            san = self.board.san(move)
            self.board.push(move)
            self.ply_index += 1
            self.last_move_uci = move.uci()
            replies.append((san, move.uci()))

        return replies

    def active_limit(self) -> int:
        if self.section_limit_ply is None:
            return len(self.line.moves_uci)
        return min(self.section_limit_ply, len(self.line.moves_uci))

    def is_finished(self) -> bool:
        return self.ply_index >= self.active_limit()

    def progress_text(self) -> str:
        limit = self.active_limit()
        turn = "Weiß" if self.board.turn == chess.WHITE else "Schwarz"
        section = " · Abschnitt aktiv" if self.section_limit_ply is not None else ""

        if self.is_finished():
            return f"Abgeschlossen · Halbzug {self.ply_index} von {limit}{section}"

        return f"Halbzug {self.ply_index + 1} von {limit} · {turn} am Zug{section}"

    def expected_move(self) -> chess.Move | None:
        if self.is_finished():
            return None
        return chess.Move.from_uci(self.line.moves_uci[self.ply_index])

    def expected_solution(self) -> Solution | None:
        move = self.expected_move()
        if move is None:
            return None
        san = self.board.san(move)
        return Solution(san=san, uci=move.uci())

    def play_user_move_uci(self, move_uci: str) -> MoveResult:
        self.last_wrong_uci = None

        if self.is_finished():
            return MoveResult(kind="finished", message="Variante ist bereits beendet.")

        try:
            played_move = chess.Move.from_uci(move_uci)
        except ValueError:
            expected = self.expected_solution()
            return MoveResult(
                kind="wrong",
                message="Ungültige Zugeingabe.",
                expected_san=expected.san if expected else None,
                played_san=move_uci,
                wrong_uci=None,
            )

        if played_move not in self.board.legal_moves:
            expected = self.expected_solution()
            self.last_wrong_uci = played_move.uci()
            return MoveResult(
                kind="wrong",
                message="Illegaler Zug.",
                expected_san=expected.san if expected else None,
                played_san=move_uci,
                wrong_uci=played_move.uci(),
            )

        expected_move = self.expected_move()
        assert expected_move is not None
        expected_san = self.board.san(expected_move)
        played_san = self.board.san(played_move)

        if played_move != expected_move:
            self.last_wrong_uci = played_move.uci()
            return MoveResult(
                kind="wrong",
                message="Falscher Zug.",
                expected_san=expected_san,
                played_san=played_san,
                wrong_uci=played_move.uci(),
            )

        snapshot_fen = self.board.fen()
        snapshot_ply = self.ply_index
        self.history.append((snapshot_fen, snapshot_ply))

        self.board.push(expected_move)
        self.ply_index += 1
        self.last_move_uci = expected_move.uci()

        auto_reply_san: str | None = None
        auto_reply_uci: str | None = None

        replies = self._auto_advance_to_user_turn()
        if replies:
            auto_reply_san, auto_reply_uci = replies[-1]

        if self.is_finished():
            message = "Richtig. Variante abgeschlossen."
        elif auto_reply_san:
            message = f"Richtig. Programm spielt: {auto_reply_san}"
        else:
            message = "Richtig."

        return MoveResult(
            kind="correct",
            message=message,
            expected_san=expected_san,
            played_san=played_san,
            last_move_uci=self.last_move_uci,
            auto_reply_san=auto_reply_san,
            auto_reply_uci=auto_reply_uci,
        )

    def clear_wrong_marker(self) -> None:
        self.last_wrong_uci = None

    def undo(self) -> str:
        if self.last_wrong_uci:
            self.last_wrong_uci = None
            return "Falsche Markierung gelöscht."

        if not self.history:
            return "Kein Zug zum Zurücknehmen."

        fen, ply = self.history.pop()
        self.board.set_fen(fen)
        self.ply_index = ply
        self.last_move_uci = None
        return "Zug zurückgenommen."
