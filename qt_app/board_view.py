from __future__ import annotations

from pathlib import Path

import chess
from PySide6 import QtCore, QtGui, QtWidgets, QtSvg

from opening_trainer.board_geometry import BoardGeometry
from qt_app.paths import asset_dir

_PIECE_FILE = {
    (chess.WHITE, chess.PAWN): "wP", (chess.WHITE, chess.KNIGHT): "wN",
    (chess.WHITE, chess.BISHOP): "wB", (chess.WHITE, chess.ROOK): "wR",
    (chess.WHITE, chess.QUEEN): "wQ", (chess.WHITE, chess.KING): "wK",
    (chess.BLACK, chess.PAWN): "bP", (chess.BLACK, chess.KNIGHT): "bN",
    (chess.BLACK, chess.BISHOP): "bB", (chess.BLACK, chess.ROOK): "bR",
    (chess.BLACK, chess.QUEEN): "bQ", (chess.BLACK, chess.KING): "bK",
}

# Wählbare Brettfarben (helles Feld, dunkles Feld). Reihenfolge = Menü-Reihenfolge.
BOARD_THEMES: dict[str, tuple[str, str]] = {
    "green": ("#ebecd0", "#779556"),   # Standard (Lichess-Grün)
    "brown": ("#f0d9b5", "#b58863"),   # Holz/Braun
    "blue":  ("#dee3e6", "#8ca2ad"),   # Blau
    "grey":  ("#e8e8e8", "#8f8f8f"),   # Grau
}

# Aktuelle Feldfarben — werden vom Zeichnen direkt gelesen und von
# set_board_theme() in-place geändert (alle Bretter teilen sie sich).
LIGHT = QtGui.QColor("#ebecd0")
DARK = QtGui.QColor("#779556")
LAST = QtGui.QColor(245, 235, 90, 150)
WRONG = QtGui.QColor(224, 102, 102, 150)
SOLUTION = QtGui.QColor(120, 200, 120, 150)
COORD_LIGHT = QtGui.QColor("#ebecd0")
COORD_DARK = QtGui.QColor("#779556")

# Vom UI-Theme (hell/dunkel) gesetzte Palette für selbstgemalte Hilfs-Widgets
# (MasteryBar/Koordinaten), damit sie im Dunkelmodus nicht hell aufleuchten.
UI_MUTED = QtGui.QColor("#6b7180")
UI_BORDER = QtGui.QColor("#e4e6ef")
UI_NEUTRAL = QtGui.QColor("#d2d2c8")     # »neu/leer«-Segment der Fortschritts-Leiste


def set_ui_palette(muted: str, border: str, neutral: str) -> None:
    """UI-Farben für die selbstgemalten Balken/Koordinaten setzen (in-place,
    alle Widgets teilen sie sich). Vom Oberflächen-Theme aufgerufen."""
    UI_MUTED.setNamedColor(muted)
    UI_BORDER.setNamedColor(border)
    UI_NEUTRAL.setNamedColor(neutral)


def set_board_theme(name: str) -> None:
    """Setzt die aktuelle Brettfarbe (mutiert die geteilten LIGHT/DARK-Objekte).
    Danach müssen vorhandene Bretter mit ``update()`` neu gezeichnet werden."""
    light, dark = BOARD_THEMES.get(name, BOARD_THEMES["green"])
    LIGHT.setNamedColor(light)
    DARK.setNamedColor(dark)


class BoardView(QtWidgets.QWidget):
    """Modernes Schachbrett (Qt) mit Drag & Drop. Nutzt die getestete
    BoardGeometry und die vorhandenen Figurengrafiken."""

    moveRequested = QtCore.Signal(int, int)  # from_square, to_square

    def __init__(self, square_size: int = 74, margin: int = 22) -> None:
        super().__init__()
        self._geo = BoardGeometry(square_size=square_size, margin=margin)
        self.board = chess.Board()
        self.train_color = chess.WHITE
        self.edit_mode = False        # True: beide Farben ziehbar (Repertoire-Editor)
        self.last_move: tuple[int, int] | None = None
        self.wrong_square: int | None = None
        self.solution_squares: tuple[int, int] | None = None
        self._drag_from: int | None = None
        self._drag_pos: QtCore.QPoint | None = None
        self._legal_targets: set[int] = set()
        self._selected: int | None = None          # per Klick gewähltes Feld
        self._press_square: int | None = None
        self._press_pos: QtCore.QPoint | None = None
        self._dragging = False
        self._anim = None
        self._anim_skip: int | None = None
        self._anim_pm = None
        self._anim_xy: tuple[int, int] | None = None
        self._pieces = self._load_pieces(square_size)
        side = self._geo.canvas_size
        self.setFixedSize(side, side)

    def board_pixels(self) -> int:
        """Kantenlänge des eigentlichen 8×8-Spielfelds (ohne Koordinatenrand)."""
        return self._geo.board_size

    def board_offset(self) -> int:
        """Abstand der oberen Brettkante von der Oberkante des Widgets (Rand)."""
        return self._geo.margin

    def _load_pieces(self, size: int) -> dict:
        """Figuren als scharfe Vektorgrafik (SVG) rendern, Retina-bewusst.
        Logische Größe = Feldgröße; gezeichnet wird mit (size*dpr) Pixeln, damit
        es auf hochauflösenden Displays gestochen scharf bleibt. PNG als Fallback."""
        out = {}
        base = asset_dir()
        screen = QtGui.QGuiApplication.primaryScreen()
        dpr = max(2.0, screen.devicePixelRatio() if screen else 2.0)
        device = max(1, int(round(size * dpr)))
        for key, name in _PIECE_FILE.items():
            svg = base / f"{name}.svg"
            if svg.exists():
                renderer = QtSvg.QSvgRenderer(str(svg))
                image = QtGui.QImage(device, device, QtGui.QImage.Format_ARGB32_Premultiplied)
                image.fill(QtCore.Qt.transparent)
                painter = QtGui.QPainter(image)
                painter.setRenderHint(QtGui.QPainter.Antialiasing)
                renderer.render(painter)
                painter.end()
                pm = QtGui.QPixmap.fromImage(image)
                pm.setDevicePixelRatio(dpr)
                out[key] = pm
                continue
            png = base / f"{name}.png"
            if png.exists():
                pm = QtGui.QPixmap(str(png)).scaled(
                    device, device, QtCore.Qt.KeepAspectRatio, QtCore.Qt.SmoothTransformation
                )
                pm.setDevicePixelRatio(dpr)
                out[key] = pm
        return out

    def set_board(self, board: chess.Board, last_move: tuple[int, int] | None = None) -> None:
        self._cancel_anim()
        self.board = board.copy(stack=False)
        self.last_move = last_move
        self.wrong_square = None
        self.solution_squares = None
        self._selected = None
        self._legal_targets = set()
        self._press_square = None
        self.update()

    def _cancel_anim(self) -> None:
        if self._anim is not None:
            self._anim.stop()
            self._anim = None
        self._anim_skip = None
        self._anim_pm = None
        self._anim_xy = None

    def animate(self, from_square: int, to_square: int, on_done=None, duration: int = 170) -> None:
        """Lässt die gezogene Figur weich von Start- zu Zielfeld gleiten.
        Setzt voraus, dass das Brett bereits den Endzustand zeigt."""
        self._cancel_anim()
        piece = self.board.piece_at(to_square)
        pm = self._pieces.get((piece.color, piece.piece_type)) if piece else None
        if pm is None:
            if on_done:
                on_done()
            return

        sx, sy = self._geo.square_to_top_left(from_square)
        tx, ty = self._geo.square_to_top_left(to_square)

        self._anim_skip = to_square
        self._anim_pm = pm

        anim = QtCore.QVariantAnimation(self)
        anim.setDuration(duration)
        anim.setStartValue(0.0)
        anim.setEndValue(1.0)
        anim.setEasingCurve(QtCore.QEasingCurve.OutCubic)
        anim.valueChanged.connect(
            lambda t: (
                setattr(self, "_anim_xy", (int(sx + (tx - sx) * t), int(sy + (ty - sy) * t))),
                self.update(),
            )
        )

        def finished() -> None:
            self._anim = None
            self._anim_skip = None
            self._anim_pm = None
            self._anim_xy = None
            self.update()
            if on_done:
                on_done()

        anim.finished.connect(finished)
        self._anim = anim
        anim.start()

    def set_flipped(self, flipped: bool) -> None:
        self._geo = BoardGeometry(square_size=self._geo.square_size, margin=self._geo.margin, flipped=flipped)
        self.update()

    def flash_wrong(self, square: int) -> None:
        self.wrong_square = square
        self.update()
        QtCore.QTimer.singleShot(700, self._clear_wrong)

    def _clear_wrong(self) -> None:
        self.wrong_square = None
        self.update()

    def show_solution(self, from_square: int, to_square: int) -> None:
        self.solution_squares = (from_square, to_square)
        self.update()

    # --- Zeichnen --------------------------------------------------------

    def paintEvent(self, _event) -> None:
        p = QtGui.QPainter(self)
        p.setRenderHint(QtGui.QPainter.Antialiasing)
        p.setRenderHint(QtGui.QPainter.SmoothPixmapTransform)
        s = self._geo.square_size

        for sq in chess.SQUARES:
            x, y = self._geo.square_to_top_left(sq)
            p.fillRect(x, y, s, s, DARK if self._geo.is_dark_square(sq) else LIGHT)

        for group, colour in ((self.last_move, LAST), (self.solution_squares, SOLUTION)):
            if group:
                for sq in group:
                    x, y = self._geo.square_to_top_left(sq)
                    p.fillRect(x, y, s, s, colour)
        if self.wrong_square is not None:
            x, y = self._geo.square_to_top_left(self.wrong_square)
            p.fillRect(x, y, s, s, WRONG)
        highlight = self._drag_from if self._drag_from is not None else self._selected
        if highlight is not None:
            x, y = self._geo.square_to_top_left(highlight)
            p.fillRect(x, y, s, s, QtGui.QColor(245, 235, 90, 110))

        self._draw_coordinates(p)

        for sq, piece in self.board.piece_map().items():
            if sq == self._drag_from or sq == self._anim_skip:
                continue
            pm = self._pieces.get((piece.color, piece.piece_type))
            if pm is None:
                continue
            x, y = self._geo.square_to_top_left(sq)
            p.drawPixmap(int(x), int(y), pm)

        if self._legal_targets:
            hint = QtGui.QColor(60, 70, 40, 55)
            for t in self._legal_targets:
                x, y = self._geo.square_to_top_left(t)
                cx, cy = x + s / 2, y + s / 2
                if self.board.piece_at(t) is not None:  # Schlagzug -> Ring
                    pen = QtGui.QPen(hint)
                    pen.setWidth(max(3, s // 11))
                    p.setPen(pen)
                    p.setBrush(QtCore.Qt.NoBrush)
                    p.drawEllipse(QtCore.QPointF(cx, cy), s * 0.44, s * 0.44)
                else:  # freies Feld -> Punkt
                    p.setPen(QtCore.Qt.NoPen)
                    p.setBrush(hint)
                    p.drawEllipse(QtCore.QPointF(cx, cy), s * 0.16, s * 0.16)

        if self._anim_pm is not None and self._anim_xy is not None:
            p.drawPixmap(self._anim_xy[0], self._anim_xy[1], self._anim_pm)

        if self._drag_from is not None and self._drag_pos is not None:
            piece = self.board.piece_at(self._drag_from)
            pm = self._pieces.get((piece.color, piece.piece_type)) if piece else None
            if pm is not None:
                p.drawPixmap(int(self._drag_pos.x() - s / 2), int(self._drag_pos.y() - s / 2), pm)
        p.end()

    def _draw_coordinates(self, p: QtGui.QPainter) -> None:
        g = self._geo
        m = g.margin
        if m <= 0:
            return
        s = g.square_size
        font = QtGui.QFont()
        font.setPointSize(11)
        font.setBold(True)
        p.setFont(font)
        p.setPen(UI_MUTED)
        board_bottom = m + g.board_size
        # Buchstaben unter dem Brett, Ziffern links daneben – im Rand.
        for col, label in enumerate(g.bottom_file_labels()):
            x, _ = g.square_to_top_left(g.row_col_to_square(7, col))
            rect = QtCore.QRectF(x, board_bottom, s, m)
            p.drawText(rect, QtCore.Qt.AlignHCenter | QtCore.Qt.AlignVCenter, label)
        for row, label in enumerate(g.left_rank_labels()):
            _, y = g.square_to_top_left(g.row_col_to_square(row, 0))
            rect = QtCore.QRectF(0, y, m, s)
            p.drawText(rect, QtCore.Qt.AlignHCenter | QtCore.Qt.AlignVCenter, label)

    # --- Eingabe: Ziehen UND Klick-Klick ---------------------------------

    def _square_at(self, pos: QtCore.QPoint) -> int | None:
        return self._geo.point_to_square(pos.x(), pos.y())

    def _own_targets(self, square: int) -> set[int]:
        return {m.to_square for m in self.board.legal_moves if m.from_square == square}

    def _movable_color(self):
        """Farbe, deren Figuren aufgenommen werden dürfen: beim Training nur die
        eigene, im Editor die jeweils am Zug befindliche."""
        return self.board.turn if self.edit_mode else self.train_color

    def clear_selection(self) -> None:
        self._selected = None
        if not self._dragging:
            self._legal_targets = set()
        self.update()

    def mousePressEvent(self, event) -> None:
        self._press_square = self._square_at(event.position().toPoint())
        self._press_pos = event.position().toPoint()
        self._dragging = False

    def mouseMoveEvent(self, event) -> None:
        if self._press_square is None or self._press_pos is None:
            return
        pos = event.position().toPoint()
        if not self._dragging:
            if abs(pos.x() - self._press_pos.x()) + abs(pos.y() - self._press_pos.y()) < 6:
                return
            piece = self.board.piece_at(self._press_square)
            if piece is None or piece.color != self._movable_color():
                return
            # Drag beginnt: Figur aufnehmen (überschreibt Klick-Auswahl).
            self._dragging = True
            self._drag_from = self._press_square
            self._selected = None
            self._legal_targets = self._own_targets(self._press_square)
        self._drag_pos = pos
        self.update()

    def mouseReleaseEvent(self, event) -> None:
        release = self._square_at(event.position().toPoint())

        if self._dragging:
            source = self._drag_from
            self._dragging = False
            self._drag_from = None
            self._drag_pos = None
            self._legal_targets = set()
            self.update()
            if release is not None and release != source:
                self.moveRequested.emit(source, release)
            self._press_square = None
            return

        # Keine Bewegung -> Klick (Klick-Klick).
        self._press_square = None
        if release is None:
            self.clear_selection()
            return
        # Zweiter Klick auf ein gültiges Zielfeld -> Zug.
        if self._selected is not None and release in self._legal_targets:
            source = self._selected
            self.clear_selection()
            self.moveRequested.emit(source, release)
            return
        # Erster Klick auf eigene Figur -> auswählen.
        piece = self.board.piece_at(release)
        if piece is not None and piece.color == self._movable_color():
            self._selected = release
            self._legal_targets = self._own_targets(release)
            self.update()
        else:
            self.clear_selection()


class EvalBar(QtWidgets.QWidget):
    """Schmale senkrechte Bewertungs-Leiste neben dem Brett.

    Zeigt die Stockfish-Bewertung der aktuellen Stellung: heller Anteil = Weiß,
    dunkler Anteil = Schwarz. Dreht mit dem Brett mit (``flipped``). Die Zahl
    oben ist immer aus Weiß-Sicht (+ = Weiß besser, ``M3`` = Matt).
    """

    _LIGHT = QtGui.QColor("#efeee4")
    _DARK = QtGui.QColor("#3a3f33")

    def __init__(self, height: int, width: int = 24) -> None:
        super().__init__()
        self.setFixedSize(width, height)
        self._cp = 0          # Centibauern aus Weiß-Sicht
        self._mate = 0        # signiert: + = Weiß setzt matt, 0 = kein Matt
        self._flipped = False
        self._has_value = False

    def set_flipped(self, flipped: bool) -> None:
        self._flipped = flipped
        self.update()

    def set_eval(self, cp: int, mate: int = 0) -> None:
        self._cp = cp
        self._mate = mate
        self._has_value = True
        self.update()

    def clear(self) -> None:
        self._has_value = False
        self.update()

    def _white_fraction(self) -> float:
        if self._mate != 0:
            return 1.0 if self._mate > 0 else 0.0
        import math
        return 1.0 / (1.0 + math.pow(10.0, -(self._cp / 600.0)))

    def paintEvent(self, event) -> None:  # noqa: N802
        p = QtGui.QPainter(self)
        p.setRenderHint(QtGui.QPainter.Antialiasing, False)
        w, h = self.width(), self.height()
        if not self._has_value:
            p.fillRect(0, 0, w, h, QtGui.QColor("#d9d9cf"))
            p.end()
            return
        wf = max(0.0, min(1.0, self._white_fraction()))
        white_h = int(round(wf * h))
        p.fillRect(0, 0, w, h, self._DARK)
        if self._flipped:                       # Weiß oben (Schwarz unten am Brett)
            p.fillRect(0, 0, w, white_h, self._LIGHT)
            light_at_top = True
        else:                                   # Weiß unten (Standard)
            p.fillRect(0, h - white_h, w, white_h, self._LIGHT)
            light_at_top = False
        if self._mate != 0:
            txt = ("" if self._mate > 0 else "-") + "M" + str(abs(self._mate))
        else:
            txt = f"{self._cp / 100.0:+.1f}"
        p.setPen(self._DARK if light_at_top else self._LIGHT)
        font = p.font()
        font.setPointSize(8)
        font.setBold(True)
        p.setFont(font)
        p.drawText(QtCore.QRect(0, 2, w, 15), QtCore.Qt.AlignHCenter, txt)
        p.end()


class MasteryBar(QtWidgets.QWidget):
    """Waagerechter Drei-Segment-Balken: grün=sitzt, gelb=wackelt, grau=neu —
    breitenproportional zu den Anzahlen. Macht den Lernstand sichtbar."""

    _GREEN = QtGui.QColor("#779556")
    _YELLOW = QtGui.QColor("#d8a657")
    # »neu/leer« folgt dem UI-Theme (hell/dunkel) statt fest hellgrau zu sein.

    def __init__(self, height: int = 24) -> None:
        super().__init__()
        self.setFixedHeight(height)
        self.setMinimumWidth(200)
        self._sitzt = 0
        self._wackelt = 0
        self._neu = 0

    def set_counts(self, sitzt: int, wackelt: int, neu: int) -> None:
        self._sitzt, self._wackelt, self._neu = sitzt, wackelt, neu
        self.update()

    _MIN_VISIBLE = 14   # px — vorhandene Anteile immer sichtbar, auch wenn winzig

    def paintEvent(self, event) -> None:  # noqa: N802
        p = QtGui.QPainter(self)
        p.setRenderHint(QtGui.QPainter.Antialiasing, True)
        w, h = self.width(), self.height()
        rect = QtCore.QRectF(0.5, 0.5, w - 1, h - 1)
        path = QtGui.QPainterPath()
        path.addRoundedRect(rect, 5, 5)
        p.setClipPath(path)
        counts = [self._sitzt, self._wackelt, self._neu]
        colors = [self._GREEN, self._YELLOW, UI_NEUTRAL]
        total = sum(counts)
        if total <= 0:
            p.fillRect(0, 0, w, h, UI_NEUTRAL)
            self._draw_border(p, rect)
            p.end()
            return
        present = [i for i in range(3) if counts[i] > 0]
        # Rohbreiten nach Anteil, aber jeder vorhandene Anteil bekommt eine
        # Mindestbreite — damit z. B. ein einzelnes „sitzt" sichtbar bleibt.
        widths = [0.0, 0.0, 0.0]
        for i in present:
            widths[i] = max(self._MIN_VISIBLE, w * counts[i] / total)
        diff = sum(widths) - w
        if diff > 0:                       # zu breit: vom größten Anteil abziehen
            for i in sorted(present, key=lambda j: -widths[j]):
                take = min(diff, widths[i] - self._MIN_VISIBLE)
                widths[i] -= take
                diff -= take
                if diff <= 0:
                    break
        elif diff < 0:                     # Rest dem größten Anteil geben
            widths[max(present, key=lambda j: widths[j])] += -diff
        x = 0
        for k, i in enumerate(present):
            seg = (w - x) if k == len(present) - 1 else int(round(widths[i]))
            p.fillRect(x, 0, seg, h, colors[i])
            x += seg
        self._draw_border(p, rect)
        p.end()

    @staticmethod
    def _draw_border(p, rect) -> None:
        p.setClipping(False)
        pen = QtGui.QPen(UI_BORDER)
        pen.setWidth(1)
        p.setPen(pen)
        p.setBrush(QtCore.Qt.NoBrush)
        p.drawRoundedRect(rect, 5, 5)


class WdlBar(QtWidgets.QWidget):
    """Schmaler Balken Weiß/Remis/Schwarz für eine Zug-Zeile im Explorer."""

    _WHITE = QtGui.QColor("#efeee4")
    _DRAW = QtGui.QColor("#b9b9ad")
    _BLACK = QtGui.QColor("#3a3f33")

    def __init__(self, width: int = 150, height: int = 16) -> None:
        super().__init__()
        self.setFixedSize(width, height)
        self._w = 0
        self._d = 0
        self._b = 0

    def set_wdl(self, white: int, draws: int, black: int) -> None:
        self._w, self._d, self._b = white, draws, black
        self.update()

    def paintEvent(self, event) -> None:  # noqa: N802
        p = QtGui.QPainter(self)
        p.setRenderHint(QtGui.QPainter.Antialiasing, False)
        w, h = self.width(), self.height()
        total = self._w + self._d + self._b
        if total <= 0:
            p.fillRect(0, 0, w, h, self._DRAW)
            p.end()
            return
        ww = int(round(w * self._w / total))
        dw = int(round(w * self._d / total))
        p.fillRect(0, 0, ww, h, self._WHITE)
        p.fillRect(ww, 0, dw, h, self._DRAW)
        p.fillRect(ww + dw, 0, w - ww - dw, h, self._BLACK)
        p.end()
