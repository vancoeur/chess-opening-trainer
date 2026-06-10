from __future__ import annotations

import tkinter as tk
from dataclasses import dataclass
from pathlib import Path

import chess

from opening_trainer.board_geometry import BoardGeometry


PIECE_SYMBOLS = {
    chess.PAWN: "♟",
    chess.KNIGHT: "♞",
    chess.BISHOP: "♝",
    chess.ROOK: "♜",
    chess.QUEEN: "♛",
    chess.KING: "♚",
}

# Echte Figurengrafiken (Cburnett-Set, gemeinfrei) liegen unter assets/pieces/.
_ASSET_DIR = Path(__file__).resolve().parent.parent / "assets" / "pieces"

_PIECE_FILE = {
    (chess.WHITE, chess.PAWN): "wP",
    (chess.WHITE, chess.KNIGHT): "wN",
    (chess.WHITE, chess.BISHOP): "wB",
    (chess.WHITE, chess.ROOK): "wR",
    (chess.WHITE, chess.QUEEN): "wQ",
    (chess.WHITE, chess.KING): "wK",
    (chess.BLACK, chess.PAWN): "bP",
    (chess.BLACK, chess.KNIGHT): "bN",
    (chess.BLACK, chess.BISHOP): "bB",
    (chess.BLACK, chess.ROOK): "bR",
    (chess.BLACK, chess.QUEEN): "bQ",
    (chess.BLACK, chess.KING): "bK",
}


@dataclass(frozen=True)
class BoardColours:
    light: str = "#ebecd0"
    dark: str = "#779556"
    last_move: str = "#f4f17a"
    hover: str = "#6fa8dc"
    wrong: str = "#e06666"
    solution: str = "#57bb8a"


def piece_to_symbol(piece: chess.Piece | None) -> str:
    if piece is None:
        return ""

    return PIECE_SYMBOLS[piece.piece_type]


class BoardWidget(tk.Canvas):
    """Tkinter-Schachbrett.

    Diese Klasse zeichnet nur Brett, Figuren und Markierungen.
    Die Brettgeometrie kommt ausschließlich aus BoardGeometry.
    """

    def __init__(
        self,
        master: tk.Misc,
        geometry: BoardGeometry | None = None,
        colours: BoardColours | None = None,
        on_square_click=None,
        on_trainable_hover=None,
        on_drag_move=None,
    ) -> None:
        self.geometry = geometry or BoardGeometry(square_size=56, margin=24)
        self.colours = colours or BoardColours()
        self.on_square_click = on_square_click
        self.on_trainable_hover = on_trainable_hover
        self.on_drag_move = on_drag_move

        super().__init__(
            master,
            width=self.geometry.canvas_size,
            height=self.geometry.canvas_size,
            highlightthickness=0,
        )

        self.board = chess.Board()
        self.last_move_uci: str | None = None
        self.wrong_move_uci: str | None = None
        self.solution_uci: str | None = None
        self.hover_square: chess.Square | None = None
        self.hover_piece_colour: chess.Color | None = chess.WHITE

        self._press_square: chess.Square | None = None
        self._press_xy: tuple[int, int] = (0, 0)
        self._dragging = False
        self._drag_source: chess.Square | None = None
        self._drag_item = None

        self._anim_skip: chess.Square | None = None
        self._anim_item = None
        self._anim_after = None

        self._load_piece_images()

        self.bind("<ButtonPress-1>", self._on_press)
        self.bind("<B1-Motion>", self._on_drag)
        self.bind("<ButtonRelease-1>", self._on_release)
        self.bind("<Motion>", self._handle_motion)
        self.bind("<Leave>", self._handle_leave)
        self.redraw()

    def set_board(self, board: chess.Board) -> None:
        self._cancel_anim()
        self.board = board.copy(stack=False)
        self.redraw()

    def _cancel_anim(self) -> None:
        if self._anim_after is not None:
            try:
                self.after_cancel(self._anim_after)
            except Exception:
                pass
            self._anim_after = None
        if self._anim_item is not None:
            try:
                self.delete(self._anim_item)
            except Exception:
                pass
            self._anim_item = None
        self._anim_skip = None

    def animate_move(self, uci: str | None, on_done=None, steps: int = 9, interval: int = 16) -> None:
        """Lässt die gerade gezogene Figur von Start- zu Zielfeld gleiten.

        Setzt voraus, dass das Brett bereits den Endzustand zeigt. Fehlt etwas
        (kein Bild, ungültiger Zug), passiert nichts – die Stellung bleibt
        korrekt.
        """
        self._cancel_anim()
        try:
            move = chess.Move.from_uci(uci) if uci else None
        except (ValueError, TypeError):
            move = None
        piece = self.board.piece_at(move.to_square) if move else None
        image = self._piece_images.get((piece.color, piece.piece_type)) if piece else None
        if move is None or image is None:
            if on_done:
                on_done()
            return

        half = self.geometry.square_size / 2
        sx, sy = self.geometry.square_to_top_left(move.from_square)
        tx, ty = self.geometry.square_to_top_left(move.to_square)
        x0, y0 = sx + half, sy + half
        x1, y1 = tx + half, ty + half

        self._anim_skip = move.to_square
        self.redraw()
        self._anim_item = self.create_image(x0, y0, image=image)

        def step(i: int) -> None:
            if not self.winfo_exists():
                return
            t = i / steps
            self.coords(self._anim_item, x0 + (x1 - x0) * t, y0 + (y1 - y0) * t)
            if i < steps:
                self._anim_after = self.after(interval, lambda: step(i + 1))
            else:
                self._anim_after = None
                if self._anim_item is not None:
                    self.delete(self._anim_item)
                    self._anim_item = None
                self._anim_skip = None
                self.redraw()
                if on_done:
                    on_done()

        step(1)

    def set_flipped(self, flipped: bool) -> None:
        self.geometry = BoardGeometry(
            square_size=self.geometry.square_size,
            margin=self.geometry.margin,
            flipped=flipped,
        )
        self.config(
            width=self.geometry.canvas_size,
            height=self.geometry.canvas_size,
        )
        self.redraw()

    def toggle_flipped(self) -> None:
        self.set_flipped(not self.geometry.flipped)

    def set_last_move(self, move_uci: str | None) -> None:
        self.last_move_uci = move_uci
        self.redraw()

    def set_wrong_move(self, move_uci: str | None) -> None:
        self.wrong_move_uci = move_uci
        self.redraw()

    def set_solution(self, move_uci: str | None) -> None:
        self.solution_uci = move_uci
        self.redraw()

    def set_hover_piece_colour(self, colour: chess.Color | None) -> None:
        self.hover_piece_colour = colour
        self.hover_square = None
        self.redraw()

    def clear_marks(self) -> None:
        self.last_move_uci = None
        self.wrong_move_uci = None
        self.solution_uci = None
        self.redraw()

    def _draggable_at(self, square: chess.Square | None):
        if square is None:
            return None
        piece = self.board.piece_at(square)
        if piece is None:
            return None
        if self.hover_piece_colour is not None and piece.color != self.hover_piece_colour:
            return None
        return self._piece_images.get((piece.color, piece.piece_type))

    def _on_press(self, event) -> None:
        self._press_square = self.geometry.point_to_square(event.x, event.y)
        self._press_xy = (event.x, event.y)
        self._dragging = False
        self._drag_source = None

    def _on_drag(self, event) -> None:
        if self._press_square is None:
            return

        if not self._dragging:
            if abs(event.x - self._press_xy[0]) + abs(event.y - self._press_xy[1]) < 5:
                return
            image = self._draggable_at(self._press_square)
            if image is None:
                return
            self._dragging = True
            self._drag_source = self._press_square
            self.redraw()  # zeichnet das Brett ohne die aufgenommene Figur
            self._drag_item = self.create_image(event.x, event.y, image=image)
        else:
            self.coords(self._drag_item, event.x, event.y)

    def _on_release(self, event) -> None:
        if self._dragging:
            source = self._drag_source
            target = self.geometry.point_to_square(event.x, event.y)
            self._dragging = False
            self._drag_source = None
            if self._drag_item is not None:
                self.delete(self._drag_item)
                self._drag_item = None
            self.redraw()
            if (
                source is not None
                and target is not None
                and target != source
                and self.on_drag_move is not None
            ):
                self.on_drag_move(source, target)
        else:
            # Keine Bewegung -> als Klick behandeln (Klick-Klick bleibt erhalten).
            if self._press_square is not None and self.on_square_click is not None:
                self.on_square_click(self._press_square)

        self._press_square = None

    def _handle_motion(self, event) -> None:
        if self._anim_after is not None:
            return
        square = self.geometry.point_to_square(event.x, event.y)
        new_hover: chess.Square | None = None

        if square is not None:
            piece = self.board.piece_at(square)
            if piece is not None and piece.color == self.hover_piece_colour:
                new_hover = square

        if new_hover is not None and self.on_trainable_hover is not None:
            self.on_trainable_hover(new_hover)

        if new_hover != self.hover_square:
            self.hover_square = new_hover
            self.redraw()

    def _handle_leave(self, event) -> None:
        if self.hover_square is not None:
            self.hover_square = None
            self.redraw()

    def redraw(self) -> None:
        self.delete("all")
        self._draw_squares()
        self._draw_hover()
        self._draw_marks()
        self._draw_coordinates()
        self._draw_pieces()

    def _draw_squares(self) -> None:
        for square in chess.SQUARES:
            x, y = self.geometry.square_to_top_left(square)
            colour = self.colours.dark if self.geometry.is_dark_square(square) else self.colours.light
            self.create_rectangle(
                x,
                y,
                x + self.geometry.square_size,
                y + self.geometry.square_size,
                fill=colour,
                outline=colour,
            )

    def _draw_hover(self) -> None:
        if self.hover_square is None:
            return

        x, y = self.geometry.square_to_top_left(self.hover_square)
        inset = 3
        self.create_rectangle(
            x + inset,
            y + inset,
            x + self.geometry.square_size - inset,
            y + self.geometry.square_size - inset,
            outline=self.colours.hover,
            width=3,
        )

    def _draw_marks(self) -> None:
        for move_uci, colour in (
            (self.last_move_uci, self.colours.last_move),
            (self.wrong_move_uci, self.colours.wrong),
            (self.solution_uci, self.colours.solution),
        ):
            if not move_uci:
                continue

            try:
                move = chess.Move.from_uci(move_uci)
            except ValueError:
                continue

            for square in (move.from_square, move.to_square):
                x, y = self.geometry.square_to_top_left(square)
                inset = 4
                self.create_rectangle(
                    x + inset,
                    y + inset,
                    x + self.geometry.square_size - inset,
                    y + self.geometry.square_size - inset,
                    outline=colour,
                    width=4,
                )

    def _draw_coordinates(self) -> None:
        font = ("Helvetica", 11)

        for file_index, file_name in enumerate(self.geometry.bottom_file_labels()):
            x = self.geometry.margin + file_index * self.geometry.square_size + self.geometry.square_size / 2
            y = self.geometry.margin + self.geometry.board_size + 12
            self.create_text(x, y, text=file_name, font=font, fill="#333333")

        for row, rank in enumerate(self.geometry.left_rank_labels()):
            x = self.geometry.margin - 12
            y = self.geometry.margin + row * self.geometry.square_size + self.geometry.square_size / 2
            self.create_text(x, y, text=rank, font=font, fill="#333333")

    def _load_piece_images(self) -> None:
        """Lädt die Figurengrafiken einmalig. Fehlen sie, bleibt das Brett über
        den Unicode-Fallback funktionsfähig."""
        self._piece_images: dict[tuple[bool, int], tk.PhotoImage] = {}
        for key, name in _PIECE_FILE.items():
            path = _ASSET_DIR / f"{name}.png"
            if not path.exists():
                continue
            try:
                self._piece_images[key] = tk.PhotoImage(file=str(path))
            except tk.TclError:
                pass

    def _draw_pieces(self) -> None:
        images = getattr(self, "_piece_images", {})
        font_size = int(self.geometry.square_size * 0.72)
        font = ("Arial Unicode MS", font_size)

        for square, piece in self.board.piece_map().items():
            if square == self._drag_source or square == self._anim_skip:
                continue
            x, y = self.geometry.square_to_top_left(square)
            cx = x + self.geometry.square_size / 2
            cy = y + self.geometry.square_size / 2

            image = images.get((piece.color, piece.piece_type))
            if image is not None:
                self.create_image(cx, cy, image=image)
                continue

            # Fallback: Unicode-Glyph, falls die Grafiken fehlen.
            symbol = piece_to_symbol(piece)
            if piece.color == chess.WHITE:
                for dx, dy in ((-1, 0), (1, 0), (0, -1), (0, 1)):
                    self.create_text(cx + dx, cy + dy, text=symbol, font=font, fill="#333333")
                self.create_text(cx, cy, text=symbol, font=font, fill="#ffffff")
            else:
                self.create_text(cx, cy, text=symbol, font=font, fill="#111111")
