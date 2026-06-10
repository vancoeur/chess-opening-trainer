import tkinter as tk

import chess

from opening_trainer.board_geometry import BoardGeometry
from opening_trainer.board_widget import BoardWidget


def main() -> None:
    root = tk.Tk()
    root.title("Brettprüfung")

    frame = tk.Frame(root, padx=12, pady=12)
    frame.pack()

    info = tk.Label(
        frame,
        text=(
            "Sichtprüfung: a1 muss unten links liegen, h8 oben rechts. "
            "a1 dunkel, h1 hell, a8 hell, h8 dunkel."
        ),
        anchor="w",
        justify="left",
    )
    info.pack(anchor="w", pady=(0, 8))

    board = chess.Board()
    widget = BoardWidget(
        frame,
        geometry=BoardGeometry(square_size=56, margin=28),
    )
    widget.set_board(board)
    widget.pack()

    button = tk.Button(frame, text="Brett drehen", command=widget.toggle_flipped)
    button.pack(pady=(8, 0))

    root.mainloop()


if __name__ == "__main__":
    main()
