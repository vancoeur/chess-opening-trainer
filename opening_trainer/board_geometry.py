from __future__ import annotations

import chess


class BoardGeometry:
    """Reine Brettgeometrie ohne GUI.

    White orientation:
    - a1 liegt unten links.
    - h8 liegt oben rechts.

    Black orientation:
    - h8 liegt unten links.
    - a1 liegt oben rechts.

    Feldfarben bleiben unabhängig von der Orientierung schachlich korrekt:
    - a1 ist dunkel.
    """

    def __init__(self, square_size: int = 60, margin: int = 24, flipped: bool = False) -> None:
        if square_size <= 0:
            raise ValueError("square_size must be positive")
        if margin < 0:
            raise ValueError("margin must be non-negative")
        self.square_size = square_size
        self.margin = margin
        self.flipped = flipped

    @property
    def board_size(self) -> int:
        return self.square_size * 8

    @property
    def canvas_size(self) -> int:
        return self.board_size + 2 * self.margin

    def square_to_row_col(self, square: chess.Square) -> tuple[int, int]:
        file_index = chess.square_file(square)
        rank_index = chess.square_rank(square)

        if self.flipped:
            row = rank_index
            col = 7 - file_index
        else:
            row = 7 - rank_index
            col = file_index

        return row, col

    def row_col_to_square(self, row: int, col: int) -> chess.Square:
        if not 0 <= row <= 7:
            raise ValueError("row must be between 0 and 7")
        if not 0 <= col <= 7:
            raise ValueError("col must be between 0 and 7")

        if self.flipped:
            file_index = 7 - col
            rank_index = row
        else:
            file_index = col
            rank_index = 7 - row

        return chess.square(file_index, rank_index)

    def square_to_top_left(self, square: chess.Square) -> tuple[int, int]:
        row, col = self.square_to_row_col(square)
        x = self.margin + col * self.square_size
        y = self.margin + row * self.square_size
        return x, y

    def point_to_square(self, x: int, y: int) -> chess.Square | None:
        board_x = x - self.margin
        board_y = y - self.margin

        if board_x < 0 or board_y < 0:
            return None
        if board_x >= self.board_size or board_y >= self.board_size:
            return None

        col = board_x // self.square_size
        row = board_y // self.square_size
        return self.row_col_to_square(row, col)

    @staticmethod
    def is_dark_square(square: chess.Square) -> bool:
        file_index = chess.square_file(square)
        rank_index = chess.square_rank(square)
        return (file_index + rank_index) % 2 == 0

    def bottom_file_labels(self) -> list[str]:
        """Dateibeschriftung unten, abhängig von der Brettorientierung."""
        labels: list[str] = []
        for col in range(8):
            square = self.row_col_to_square(7, col)
            labels.append(chess.FILE_NAMES[chess.square_file(square)])
        return labels

    def left_rank_labels(self) -> list[str]:
        """Reihenbeschriftung links, abhängig von der Brettorientierung."""
        labels: list[str] = []
        for row in range(8):
            square = self.row_col_to_square(row, 0)
            labels.append(str(chess.square_rank(square) + 1))
        return labels
