import chess

from opening_trainer.pgn_loader import load_pgn_text, load_pgn_file
from opening_trainer.training_state import TrainingState


TEST_PGN = """
[Event "London Test"]
[ChapterName "London A1 – Testlinie"]
[ECO "D02"]
[Opening "Queen's Pawn Game: London System"]
[Result "*"]

1. d4 d5 2. Nf3 Nf6 3. Bf4 e6 *
"""


def test_pgn_loader_reads_variant_name_and_moves():
    lines = load_pgn_text(TEST_PGN)

    assert len(lines) == 1
    assert lines[0].name == "London A1 – Testlinie"
    assert lines[0].moves_san[:4] == ["d4", "d5", "Nf3", "Nf6"]
    assert lines[0].moves_uci[:4] == ["d2d4", "d7d5", "g1f3", "g8f6"]


def test_training_accepts_correct_move_and_auto_reply():
    line = load_pgn_text(TEST_PGN)[0]
    training = TrainingState(line)

    result = training.play_user_move_uci("d2d4")

    assert result.kind == "correct"
    assert result.played_san == "d4"
    assert result.auto_reply_san == "d5"
    assert training.ply_index == 2
    assert training.board.piece_at(chess.D4).symbol() == "P"
    assert training.board.piece_at(chess.D5).symbol() == "p"


def test_training_rejects_wrong_move_without_changing_position():
    line = load_pgn_text(TEST_PGN)[0]
    training = TrainingState(line)

    before = training.board.fen()
    result = training.play_user_move_uci("g1f3")

    assert result.kind == "wrong"
    assert result.expected_san == "d4"
    assert result.played_san == "Nf3"
    assert result.wrong_uci == "g1f3"
    assert training.board.fen() == before
    assert training.ply_index == 0


def test_undo_clears_wrong_marker_first():
    line = load_pgn_text(TEST_PGN)[0]
    training = TrainingState(line)

    result = training.play_user_move_uci("g1f3")
    assert result.kind == "wrong"
    assert training.last_wrong_uci == "g1f3"

    message = training.undo()

    assert message == "Falsche Markierung gelöscht."
    assert training.last_wrong_uci is None
    assert training.ply_index == 0


def test_undo_reverts_last_accepted_user_move_and_reply():
    line = load_pgn_text(TEST_PGN)[0]
    training = TrainingState(line)

    training.play_user_move_uci("d2d4")
    assert training.ply_index == 2

    message = training.undo()

    assert message == "Zug zurückgenommen."
    assert training.ply_index == 0
    assert training.board == chess.Board()


def test_solution_returns_expected_move():
    line = load_pgn_text(TEST_PGN)[0]
    training = TrainingState(line)

    solution = training.expected_solution()

    assert solution is not None
    assert solution.san == "d4"
    assert solution.uci == "d2d4"


def test_restart_resets_training():
    line = load_pgn_text(TEST_PGN)[0]
    training = TrainingState(line)

    training.play_user_move_uci("d2d4")
    assert training.ply_index == 2

    training.restart()

    assert training.ply_index == 0
    assert training.board == chess.Board()


from opening_trainer.board_geometry import BoardGeometry


def test_board_geometry_white_orientation_corners():
    geometry = BoardGeometry(square_size=60, margin=24)

    assert geometry.row_col_to_square(7, 0) == chess.A1
    assert geometry.row_col_to_square(7, 7) == chess.H1
    assert geometry.row_col_to_square(0, 0) == chess.A8
    assert geometry.row_col_to_square(0, 7) == chess.H8


def test_board_geometry_square_to_top_left():
    geometry = BoardGeometry(square_size=60, margin=24)

    assert geometry.square_to_top_left(chess.A8) == (24, 24)
    assert geometry.square_to_top_left(chess.H8) == (444, 24)
    assert geometry.square_to_top_left(chess.A1) == (24, 444)
    assert geometry.square_to_top_left(chess.H1) == (444, 444)


def test_board_geometry_point_to_square():
    geometry = BoardGeometry(square_size=60, margin=24)

    assert geometry.point_to_square(25, 25) == chess.A8
    assert geometry.point_to_square(445, 25) == chess.H8
    assert geometry.point_to_square(25, 445) == chess.A1
    assert geometry.point_to_square(445, 445) == chess.H1

    assert geometry.point_to_square(10, 10) is None
    assert geometry.point_to_square(600, 600) is None


def test_board_geometry_square_colours():
    assert BoardGeometry.is_dark_square(chess.A1) is True
    assert BoardGeometry.is_dark_square(chess.H1) is False
    assert BoardGeometry.is_dark_square(chess.A8) is False
    assert BoardGeometry.is_dark_square(chess.H8) is True


from legacy.board_widget import piece_to_symbol


def test_piece_to_symbol():
    assert piece_to_symbol(chess.Piece(chess.PAWN, chess.WHITE)) == "♟"
    assert piece_to_symbol(chess.Piece(chess.PAWN, chess.BLACK)) == "♟"
    assert piece_to_symbol(chess.Piece(chess.KING, chess.WHITE)) == "♚"
    assert piece_to_symbol(chess.Piece(chess.KING, chess.BLACK)) == "♚"
    assert piece_to_symbol(None) == ""


def test_board_geometry_black_orientation_corners():
    geometry = BoardGeometry(square_size=60, margin=24, flipped=True)

    assert geometry.row_col_to_square(7, 0) == chess.H8
    assert geometry.row_col_to_square(7, 7) == chess.A8
    assert geometry.row_col_to_square(0, 0) == chess.H1
    assert geometry.row_col_to_square(0, 7) == chess.A1


def test_board_geometry_black_orientation_top_left():
    geometry = BoardGeometry(square_size=60, margin=24, flipped=True)

    assert geometry.square_to_top_left(chess.H1) == (24, 24)
    assert geometry.square_to_top_left(chess.A1) == (444, 24)
    assert geometry.square_to_top_left(chess.H8) == (24, 444)
    assert geometry.square_to_top_left(chess.A8) == (444, 444)


def test_board_geometry_black_orientation_point_to_square():
    geometry = BoardGeometry(square_size=60, margin=24, flipped=True)

    assert geometry.point_to_square(25, 25) == chess.H1
    assert geometry.point_to_square(445, 25) == chess.A1
    assert geometry.point_to_square(25, 445) == chess.H8
    assert geometry.point_to_square(445, 445) == chess.A8


def test_board_geometry_white_coordinate_labels():
    geometry = BoardGeometry(square_size=60, margin=24, flipped=False)

    assert geometry.bottom_file_labels() == ["a", "b", "c", "d", "e", "f", "g", "h"]
    assert geometry.left_rank_labels() == ["8", "7", "6", "5", "4", "3", "2", "1"]


def test_board_geometry_black_coordinate_labels():
    geometry = BoardGeometry(square_size=60, margin=24, flipped=True)

    assert geometry.bottom_file_labels() == ["h", "g", "f", "e", "d", "c", "b", "a"]
    assert geometry.left_rank_labels() == ["1", "2", "3", "4", "5", "6", "7", "8"]


def test_black_training_auto_plays_first_white_move():
    line = load_pgn_text(TEST_PGN)[0]
    training = TrainingState(line, train_color=chess.BLACK)

    assert training.ply_index == 1
    assert training.board.piece_at(chess.D4).symbol() == "P"
    solution = training.expected_solution()
    assert solution is not None
    assert solution.san == "d5"
    assert solution.uci == "d7d5"


def test_black_training_accepts_black_reply_and_auto_plays_white_next_move():
    line = load_pgn_text(TEST_PGN)[0]
    training = TrainingState(line, train_color=chess.BLACK)

    result = training.play_user_move_uci("d7d5")

    assert result.kind == "correct"
    assert result.played_san == "d5"
    assert result.auto_reply_san == "Nf3"
    assert training.ply_index == 3
    assert training.board.piece_at(chess.D5).symbol() == "p"
    assert training.board.piece_at(chess.F3).symbol() == "N"


def test_black_training_rejects_wrong_black_reply_without_changing_position():
    line = load_pgn_text(TEST_PGN)[0]
    training = TrainingState(line, train_color=chess.BLACK)

    before = training.board.fen()
    result = training.play_user_move_uci("g8f6")

    assert result.kind == "wrong"
    assert result.expected_san == "d5"
    assert result.played_san == "Nf6"
    assert result.wrong_uci == "g8f6"
    assert training.board.fen() == before
    assert training.ply_index == 1


def test_white_repeat_until_here_restarts_and_limits_section():
    line = load_pgn_text(TEST_PGN)[0]
    training = TrainingState(line)

    training.play_user_move_uci("d2d4")
    training.play_user_move_uci("g1f3")
    assert training.ply_index == 4

    message = training.repeat_until_here()

    assert message == "Abschnitt neu gestartet."
    assert training.section_limit_ply == 4
    assert training.ply_index == 0

    result1 = training.play_user_move_uci("d2d4")
    assert result1.kind == "correct"
    assert training.ply_index == 2
    assert training.is_finished() is False

    result2 = training.play_user_move_uci("g1f3")
    assert result2.kind == "correct"
    assert training.ply_index == 4
    assert training.is_finished() is True


def test_black_repeat_until_here_restarts_and_limits_section():
    line = load_pgn_text(TEST_PGN)[0]
    training = TrainingState(line, train_color=chess.BLACK)

    assert training.ply_index == 1

    training.play_user_move_uci("d7d5")
    assert training.ply_index == 3

    message = training.repeat_until_here()

    assert message == "Abschnitt neu gestartet."
    assert training.section_limit_ply == 3
    assert training.ply_index == 1

    result = training.play_user_move_uci("d7d5")
    assert result.kind == "correct"
    assert training.ply_index == 3
    assert training.is_finished() is True


def test_restart_full_line_clears_section_limit():
    line = load_pgn_text(TEST_PGN)[0]
    training = TrainingState(line)

    training.play_user_move_uci("d2d4")
    training.repeat_until_here()

    assert training.section_limit_ply == 2

    training.restart_full_line()

    assert training.section_limit_ply is None
    assert training.ply_index == 0


from opening_trainer.pgn_loader import load_pgn_folder


def test_load_pgn_folder_reads_multiple_pgn_files(tmp_path):
    first = tmp_path / "01_london.pgn"
    second = tmp_path / "02_italian.pgn"

    first.write_text(
        """
[Event "London"]
[ChapterName "London Test"]
[Result "*"]

1. d4 d5 *
""",
        encoding="utf-8",
    )

    second.write_text(
        """
[Event "Italian"]
[ChapterName "Italian Test"]
[Result "*"]

1. e4 e5 *
""",
        encoding="utf-8",
    )

    lines = load_pgn_folder(tmp_path)

    assert len(lines) == 2
    assert lines[0].name == "London Test"
    assert lines[1].name == "Italian Test"
    assert lines[0].moves_uci == ["d2d4", "d7d5"]
    assert lines[1].moves_uci == ["e2e4", "e7e5"]


def test_load_pgn_folder_ignores_non_pgn_files(tmp_path):
    pgn = tmp_path / "line.pgn"
    txt = tmp_path / "notes.txt"

    pgn.write_text(
        """
[Event "Only PGN"]
[ChapterName "Only PGN Test"]
[Result "*"]

1. c4 c5 *
""",
        encoding="utf-8",
    )
    txt.write_text("Das ist keine PGN-Datei.", encoding="utf-8")

    lines = load_pgn_folder(tmp_path)

    assert len(lines) == 1
    assert lines[0].name == "Only PGN Test"


def test_progress_text_for_white_training():
    line = load_pgn_text(TEST_PGN)[0]
    training = TrainingState(line)

    assert training.progress_text() == "Halbzug 1 von 6 · Weiß am Zug"

    training.play_user_move_uci("d2d4")

    assert training.progress_text() == "Halbzug 3 von 6 · Weiß am Zug"


def test_progress_text_for_black_training():
    line = load_pgn_text(TEST_PGN)[0]
    training = TrainingState(line, train_color=chess.BLACK)

    assert training.progress_text() == "Halbzug 2 von 6 · Schwarz am Zug"


def test_progress_text_for_active_section():
    line = load_pgn_text(TEST_PGN)[0]
    training = TrainingState(line)

    training.play_user_move_uci("d2d4")
    training.repeat_until_here()

    assert training.progress_text() == "Halbzug 1 von 2 · Weiß am Zug · Abschnitt aktiv"

    training.play_user_move_uci("d2d4")

    assert training.progress_text() == "Abgeschlossen · Halbzug 2 von 2 · Abschnitt aktiv"


def test_load_pgn_file_sets_source_name(tmp_path):
    pgn = tmp_path / "London_Test.pgn"
    pgn.write_text(TEST_PGN, encoding="utf-8")

    lines = load_pgn_file(pgn)

    assert len(lines) == 1
    assert lines[0].source_name == "London_Test.pgn"


def test_load_pgn_text_can_set_source_name():
    lines = load_pgn_text(TEST_PGN, source_name="Direkter Text")

    assert len(lines) == 1
    assert lines[0].source_name == "Direkter Text"


from opening_trainer.repertoire import LineKey, Repertoire, RepertoireCategory


def test_line_key_references_line_without_copying_moves():
    line = load_pgn_text(TEST_PGN, source_name="London.pgn")[0]

    key = LineKey.from_line(line)

    assert key == LineKey(source_name="London.pgn", line_name="London A1 – Testlinie")
    assert not hasattr(key, "moves_uci")
    assert not hasattr(key, "moves_san")


def test_repertoire_category_contains_line_by_key():
    line = load_pgn_text(TEST_PGN, source_name="London.pgn")[0]
    category = RepertoireCategory(name="Weiß", line_keys=[LineKey.from_line(line)])
    other_line = load_pgn_text(TEST_PGN, source_name="Other.pgn")[0]

    assert category.contains(line) is True
    assert category.contains(other_line) is False


def test_repertoire_returns_category_names_in_order():
    repertoire = Repertoire(
        categories=[
            RepertoireCategory(name="Weiß"),
            RepertoireCategory(name="Schwarz"),
        ]
    )

    assert repertoire.category_names() == ["Weiß", "Schwarz"]


def test_repertoire_lines_for_category_returns_matching_existing_lines_only():
    london = load_pgn_text(TEST_PGN, source_name="London.pgn")[0]
    italian = load_pgn_text(
        """
[Event "Italian"]
[ChapterName "Italian A1"]
[Result "*"]

1. e4 e5 *
""",
        source_name="Italian.pgn",
    )[0]
    missing = LineKey(source_name="Missing.pgn", line_name="Missing")
    repertoire = Repertoire(
        categories=[
            RepertoireCategory(
                name="Weiß",
                line_keys=[LineKey.from_line(london), missing],
            )
        ]
    )

    assert repertoire.lines_for_category("Weiß", [london, italian]) == [london]
    assert repertoire.lines_for_category("Schwarz", [london, italian]) == []


def test_repertoire_category_add_line_avoids_duplicates():
    line = load_pgn_text(TEST_PGN, source_name="London.pgn")[0]
    category = RepertoireCategory(name="Weiß")

    assert category.add_line(line) is True
    assert category.add_line(line) is False
    assert category.line_keys == [LineKey.from_line(line)]


def test_repertoire_category_remove_line_reports_result():
    line = load_pgn_text(TEST_PGN, source_name="London.pgn")[0]
    category = RepertoireCategory(name="Weiß", line_keys=[LineKey.from_line(line)])

    assert category.remove_line(line) is True
    assert category.remove_line(line) is False
    assert category.line_keys == []


def test_repertoire_renames_category_without_creating_duplicate_names():
    repertoire = Repertoire(
        categories=[
            RepertoireCategory(name="Weiß"),
            RepertoireCategory(name="Schwarz"),
        ]
    )

    assert repertoire.rename_category("Weiß", "Weißrepertoire") is True
    assert repertoire.rename_category("Schwarz", "Weißrepertoire") is False
    assert repertoire.rename_category("Fehlt", "Neu") is False
    assert repertoire.category_names() == ["Weißrepertoire", "Schwarz"]


def test_repertoire_deletes_category_by_name():
    repertoire = Repertoire(
        categories=[
            RepertoireCategory(name="Weiß"),
            RepertoireCategory(name="Schwarz"),
        ]
    )

    assert repertoire.delete_category("Weiß") is True
    assert repertoire.delete_category("Weiß") is False
    assert repertoire.category_names() == ["Schwarz"]


def test_repertoire_adds_and_removes_lines_from_category():
    line = load_pgn_text(TEST_PGN, source_name="London.pgn")[0]
    repertoire = Repertoire(categories=[RepertoireCategory(name="Weiß")])

    assert repertoire.add_line_to_category("Weiß", line) is True
    assert repertoire.add_line_to_category("Weiß", line) is False
    assert repertoire.add_line_to_category("Fehlt", line) is False
    assert repertoire.lines_for_category("Weiß", [line]) == [line]

    assert repertoire.remove_line_from_category("Weiß", line) is True
    assert repertoire.remove_line_from_category("Weiß", line) is False
    assert repertoire.remove_line_from_category("Fehlt", line) is False
    assert repertoire.lines_for_category("Weiß", [line]) == []


from opening_trainer.repertoire_store import RepertoireStore


def test_repertoire_store_saves_and_loads_json(tmp_path):
    path = tmp_path / "repertoire.json"
    repertoire = Repertoire(
        categories=[
            RepertoireCategory(
                name="Weiß",
                line_keys=[
                    LineKey(source_name="London.pgn", line_name="London A1"),
                    LineKey(source_name="Italian.pgn", line_name="Italian A1"),
                ],
            ),
            RepertoireCategory(name="Schwarz"),
        ]
    )

    RepertoireStore(repertoire).save(path)
    loaded = RepertoireStore.load(path)

    assert loaded.repertoire == repertoire


def test_repertoire_store_loads_missing_file_as_empty(tmp_path):
    loaded = RepertoireStore.load(tmp_path / "missing_repertoire.json")

    assert loaded.repertoire == Repertoire()


def test_repertoire_store_loads_invalid_json_as_empty(tmp_path):
    path = tmp_path / "repertoire.json"
    path.write_text("{kaputt", encoding="utf-8")

    loaded = RepertoireStore.load(path)

    assert loaded.repertoire == Repertoire()


def test_repertoire_store_loads_invalid_shape_as_empty(tmp_path):
    path = tmp_path / "repertoire.json"
    path.write_text('{"categories": [{"line_keys": []}]}', encoding="utf-8")

    loaded = RepertoireStore.load(path)

    assert loaded.repertoire == Repertoire()


from opening_trainer.stats_store import StatsStore


def test_stats_store_counts_line_attempts():
    store = StatsStore()

    store.add_event(
        source_name="London.pgn",
        line_name="London A1",
        fen_before="fen-one",
        expected_san="d4",
        played_san="d4",
        correct=True,
        timestamp="2026-05-23T10:00:00+00:00",
    )
    store.add_event(
        source_name="London.pgn",
        line_name="London A1",
        fen_before="fen-two",
        expected_san="Nf3",
        played_san="Bf4",
        correct=False,
        timestamp="2026-05-23T10:01:00+00:00",
    )

    stats = store.stats_for_line(source_name="London.pgn", line_name="London A1")

    assert stats.attempts == 2
    assert stats.correct == 1
    assert stats.wrong == 1
    assert stats.accuracy == 0.5
    assert stats.last_trained == "2026-05-23T10:01:00+00:00"


def test_stats_store_separates_lines():
    store = StatsStore()

    store.add_event(
        source_name="London.pgn",
        line_name="London A1",
        fen_before="fen-one",
        expected_san="d4",
        played_san="d4",
        correct=True,
        timestamp="2026-05-23T10:00:00+00:00",
    )
    store.add_event(
        source_name="Italian.pgn",
        line_name="Italian A1",
        fen_before="fen-two",
        expected_san="e4",
        played_san="d4",
        correct=False,
        timestamp="2026-05-23T10:01:00+00:00",
    )

    london = store.stats_for_line(source_name="London.pgn", line_name="London A1")
    italian = store.stats_for_line(source_name="Italian.pgn", line_name="Italian A1")

    assert london.attempts == 1
    assert london.correct == 1
    assert italian.attempts == 1
    assert italian.wrong == 1


def test_stats_store_saves_and_loads_json(tmp_path):
    path = tmp_path / "stats.json"
    store = StatsStore()

    store.add_event(
        source_name="London.pgn",
        line_name="London A1",
        fen_before="fen-one",
        expected_san="d4",
        played_san="d4",
        correct=True,
        timestamp="2026-05-23T10:00:00+00:00",
    )

    store.save(path)
    loaded = StatsStore.load(path)

    stats = loaded.stats_for_line(source_name="London.pgn", line_name="London A1")

    assert stats.attempts == 1
    assert stats.correct == 1
    assert stats.wrong == 0


def test_stats_store_loads_missing_file_as_empty(tmp_path):
    path = tmp_path / "missing.json"

    loaded = StatsStore.load(path)

    stats = loaded.stats_for_line(source_name="London.pgn", line_name="London A1")
    assert stats.attempts == 0
    assert stats.correct == 0
    assert stats.wrong == 0
    assert stats.accuracy == 0.0



def test_clear_wrong_marker():
    line = load_pgn_text(TEST_PGN)[0]
    training = TrainingState(line)

    result = training.play_user_move_uci("g1f3")
    assert result.kind == "wrong"
    assert training.last_wrong_uci == "g1f3"

    training.clear_wrong_marker()

    assert training.last_wrong_uci is None
    assert training.ply_index == 0


def test_stats_store_collects_error_positions_for_line():
    store = StatsStore()

    store.add_event(
        source_name="London.pgn",
        line_name="London A1",
        fen_before="fen-one",
        expected_san="d4",
        played_san="Nf3",
        correct=False,
        timestamp="2026-05-23T10:00:00+00:00",
    )
    store.add_event(
        source_name="London.pgn",
        line_name="London A1",
        fen_before="fen-one",
        expected_san="d4",
        played_san="c4",
        correct=False,
        timestamp="2026-05-23T10:01:00+00:00",
    )
    store.add_event(
        source_name="London.pgn",
        line_name="London A1",
        fen_before="fen-two",
        expected_san="Nf3",
        played_san="Bf4",
        correct=False,
        timestamp="2026-05-23T10:02:00+00:00",
    )
    store.add_event(
        source_name="Italian.pgn",
        line_name="Italian A1",
        fen_before="fen-three",
        expected_san="e4",
        played_san="d4",
        correct=False,
        timestamp="2026-05-23T10:03:00+00:00",
    )

    positions = store.error_positions_for_line(source_name="London.pgn", line_name="London A1")

    assert len(positions) == 2
    assert positions[0].fen_before == "fen-one"
    assert positions[0].expected_san == "d4"
    assert positions[0].wrong_count == 2
    assert positions[0].last_played_san == "c4"
    assert positions[1].fen_before == "fen-two"
    assert positions[1].wrong_count == 1


def test_stats_store_finds_most_common_error_position():
    store = StatsStore()

    store.add_event(
        source_name="London.pgn",
        line_name="London A1",
        fen_before="fen-one",
        expected_san="d4",
        played_san="Nf3",
        correct=False,
        timestamp="2026-05-23T10:00:00+00:00",
    )
    store.add_event(
        source_name="London.pgn",
        line_name="London A1",
        fen_before="fen-two",
        expected_san="Nf3",
        played_san="Bf4",
        correct=False,
        timestamp="2026-05-23T10:01:00+00:00",
    )
    store.add_event(
        source_name="London.pgn",
        line_name="London A1",
        fen_before="fen-two",
        expected_san="Nf3",
        played_san="Nc3",
        correct=False,
        timestamp="2026-05-23T10:02:00+00:00",
    )

    position = store.most_common_error_position(source_name="London.pgn", line_name="London A1")

    assert position is not None
    assert position.fen_before == "fen-two"
    assert position.expected_san == "Nf3"
    assert position.wrong_count == 2


def test_stats_store_returns_no_error_position_when_line_has_no_errors():
    store = StatsStore()

    store.add_event(
        source_name="London.pgn",
        line_name="London A1",
        fen_before="fen-one",
        expected_san="d4",
        played_san="d4",
        correct=True,
        timestamp="2026-05-23T10:00:00+00:00",
    )

    positions = store.error_positions_for_line(source_name="London.pgn", line_name="London A1")
    position = store.most_common_error_position(source_name="London.pgn", line_name="London A1")

    assert positions == []
    assert position is None


def test_jump_to_fen_finds_position_inside_line():
    line = load_pgn_text(TEST_PGN)[0]
    reference = TrainingState(line)

    reference.play_user_move_uci("d2d4")
    fen_after_d4_d5 = reference.board.fen()

    training = TrainingState(line)
    found = training.jump_to_fen(fen_after_d4_d5)

    assert found is True
    assert training.board.fen() == fen_after_d4_d5
    assert training.ply_index == 2

    solution = training.expected_solution()
    assert solution is not None
    assert solution.san == "Nf3"
    assert solution.uci == "g1f3"


def test_jump_to_fen_accepts_correct_move_after_jump():
    line = load_pgn_text(TEST_PGN)[0]
    reference = TrainingState(line)

    reference.play_user_move_uci("d2d4")
    fen_after_d4_d5 = reference.board.fen()

    training = TrainingState(line)
    assert training.jump_to_fen(fen_after_d4_d5) is True

    result = training.play_user_move_uci("g1f3")

    assert result.kind == "correct"
    assert result.played_san == "Nf3"


def test_jump_to_fen_rejects_wrong_move_after_jump():
    line = load_pgn_text(TEST_PGN)[0]
    reference = TrainingState(line)

    reference.play_user_move_uci("d2d4")
    fen_after_d4_d5 = reference.board.fen()

    training = TrainingState(line)
    assert training.jump_to_fen(fen_after_d4_d5) is True

    before = training.board.fen()
    result = training.play_user_move_uci("b1c3")

    assert result.kind == "wrong"
    assert result.expected_san == "Nf3"
    assert result.played_san == "Nc3"
    assert training.board.fen() == before


def test_jump_to_fen_returns_false_for_unknown_position():
    line = load_pgn_text(TEST_PGN)[0]
    training = TrainingState(line)

    unknown_fen = "8/8/8/8/8/8/8/8 w - - 0 1"

    assert training.jump_to_fen(unknown_fen) is False


def test_stats_store_correct_retry_reduces_active_error_position():
    store = StatsStore()

    store.add_event(
        source_name="London.pgn",
        line_name="London A1",
        fen_before="fen-one",
        expected_san="d4",
        played_san="Nf3",
        correct=False,
        timestamp="2026-05-23T10:00:00+00:00",
    )
    store.add_event(
        source_name="London.pgn",
        line_name="London A1",
        fen_before="fen-one",
        expected_san="d4",
        played_san="d4",
        correct=True,
        timestamp="2026-05-23T10:01:00+00:00",
    )

    positions = store.error_positions_for_line(source_name="London.pgn", line_name="London A1")
    position = store.most_common_error_position(source_name="London.pgn", line_name="London A1")

    assert positions == []
    assert position is None


def test_stats_store_correct_retry_partly_reduces_repeated_error_position():
    store = StatsStore()

    store.add_event(
        source_name="London.pgn",
        line_name="London A1",
        fen_before="fen-one",
        expected_san="d4",
        played_san="Nf3",
        correct=False,
        timestamp="2026-05-23T10:00:00+00:00",
    )
    store.add_event(
        source_name="London.pgn",
        line_name="London A1",
        fen_before="fen-one",
        expected_san="d4",
        played_san="c4",
        correct=False,
        timestamp="2026-05-23T10:01:00+00:00",
    )
    store.add_event(
        source_name="London.pgn",
        line_name="London A1",
        fen_before="fen-one",
        expected_san="d4",
        played_san="d4",
        correct=True,
        timestamp="2026-05-23T10:02:00+00:00",
    )

    positions = store.error_positions_for_line(source_name="London.pgn", line_name="London A1")

    assert len(positions) == 1
    assert positions[0].fen_before == "fen-one"
    assert positions[0].expected_san == "d4"
    assert positions[0].wrong_count == 1
    assert positions[0].last_played_san == "c4"


def test_error_position_label():
    store = StatsStore()

    store.add_event(
        source_name="London.pgn",
        line_name="London A1",
        fen_before="fen-one",
        expected_san="Nf3",
        played_san="Bf4",
        correct=False,
        timestamp="2026-05-23T10:00:00+00:00",
    )

    position = store.most_common_error_position(source_name="London.pgn", line_name="London A1")

    assert position is not None
    assert position.label() == "1× Fehler · erwartet: Nf3 · zuletzt gespielt: Bf4"


def test_stats_store_later_wrong_reactivates_error_after_previous_correct_retry():
    store = StatsStore()

    store.add_event(
        source_name="Italian.pgn",
        line_name="Italian A1",
        fen_before="fen-one",
        expected_san="Bc4",
        played_san="Bc4",
        correct=True,
        timestamp="2026-05-23T10:00:00+00:00",
    )
    store.add_event(
        source_name="Italian.pgn",
        line_name="Italian A1",
        fen_before="fen-one",
        expected_san="Bc4",
        played_san="Bd3",
        correct=False,
        timestamp="2026-05-23T10:01:00+00:00",
    )

    positions = store.error_positions_for_line(source_name="Italian.pgn", line_name="Italian A1")

    assert len(positions) == 1
    assert positions[0].fen_before == "fen-one"
    assert positions[0].expected_san == "Bc4"
    assert positions[0].wrong_count == 1
    assert positions[0].last_played_san == "Bd3"


def test_stats_store_correct_retry_only_reduces_existing_open_error():
    store = StatsStore()

    store.add_event(
        source_name="Italian.pgn",
        line_name="Italian A1",
        fen_before="fen-one",
        expected_san="Bc4",
        played_san="Bd3",
        correct=False,
        timestamp="2026-05-23T10:00:00+00:00",
    )
    store.add_event(
        source_name="Italian.pgn",
        line_name="Italian A1",
        fen_before="fen-one",
        expected_san="Bc4",
        played_san="Bc4",
        correct=True,
        timestamp="2026-05-23T10:01:00+00:00",
    )
    store.add_event(
        source_name="Italian.pgn",
        line_name="Italian A1",
        fen_before="fen-one",
        expected_san="Bc4",
        played_san="Bd3",
        correct=False,
        timestamp="2026-05-23T10:02:00+00:00",
    )

    positions = store.error_positions_for_line(source_name="Italian.pgn", line_name="Italian A1")

    assert len(positions) == 1
    assert positions[0].wrong_count == 1
    assert positions[0].last_played_san == "Bd3"


def test_stats_store_keeps_all_wrong_move_events_even_after_correct_retry():
    store = StatsStore()

    store.add_event(
        source_name="Italian.pgn",
        line_name="Italian A1",
        fen_before="fen-one",
        expected_san="Bc4",
        played_san="Bd3",
        correct=False,
        timestamp="2026-05-23T10:00:00+00:00",
    )
    store.add_event(
        source_name="Italian.pgn",
        line_name="Italian A1",
        fen_before="fen-one",
        expected_san="Bc4",
        played_san="Bc4",
        correct=True,
        timestamp="2026-05-23T10:01:00+00:00",
    )

    wrong_events = store.wrong_move_events_for_line(
        source_name="Italian.pgn",
        line_name="Italian A1",
    )

    assert len(wrong_events) == 1
    assert wrong_events[0].expected_san == "Bc4"
    assert wrong_events[0].played_san == "Bd3"
    assert wrong_events[0].correct is False


def test_stats_store_wrong_move_summary_groups_by_position_expected_and_played_move():
    store = StatsStore()

    store.add_event(
        source_name="Italian.pgn",
        line_name="Italian A1",
        fen_before="fen-one",
        expected_san="Bc4",
        played_san="Bd3",
        correct=False,
        timestamp="2026-05-23T10:00:00+00:00",
    )
    store.add_event(
        source_name="Italian.pgn",
        line_name="Italian A1",
        fen_before="fen-one",
        expected_san="Bc4",
        played_san="Bd3",
        correct=False,
        timestamp="2026-05-23T10:01:00+00:00",
    )
    store.add_event(
        source_name="Italian.pgn",
        line_name="Italian A1",
        fen_before="fen-one",
        expected_san="Bc4",
        played_san="Nf3",
        correct=False,
        timestamp="2026-05-23T10:02:00+00:00",
    )

    summary = store.wrong_move_summary_for_line(
        source_name="Italian.pgn",
        line_name="Italian A1",
    )

    assert len(summary) == 2
    assert summary[0].expected_san == "Bc4"
    assert summary[0].played_san == "Bd3"
    assert summary[0].count == 2
    assert summary[1].played_san == "Nf3"
    assert summary[1].count == 1


def test_wrong_move_summary_label():
    store = StatsStore()

    store.add_event(
        source_name="Italian.pgn",
        line_name="Italian A1",
        fen_before="fen-one",
        expected_san="Bc4",
        played_san="Bd3",
        correct=False,
        timestamp="2026-05-23T10:00:00+00:00",
    )

    summary = store.wrong_move_summary_for_line(
        source_name="Italian.pgn",
        line_name="Italian A1",
    )

    assert summary[0].label() == "1× · erwartet: Bc4 · gespielt: Bd3"


from opening_trainer.settings_store import AppSettings, SettingsStore


def test_settings_store_loads_missing_file_as_defaults(tmp_path):
    path = tmp_path / "missing_settings.json"

    store = SettingsStore.load(path)

    assert store.settings.last_pgn_folder == ""
    assert store.settings.last_pgn_path == ""
    assert store.settings.last_pgn_kind == ""
    assert store.settings.train_color == "white"
    assert store.settings.window_geometry == ""


def test_settings_store_saves_and_loads_json(tmp_path):
    path = tmp_path / "settings.json"
    store = SettingsStore(
        AppSettings(
            last_pgn_folder="/tmp",
            last_pgn_path="/tmp/pgn/openings.pgn",
            last_pgn_kind="file",
            train_color="black",
            window_geometry="1200x800+20+30",
        )
    )

    store.save(path)
    loaded = SettingsStore.load(path)

    assert loaded.settings.last_pgn_folder == "/tmp"
    assert loaded.settings.last_pgn_path == "/tmp/pgn/openings.pgn"
    assert loaded.settings.last_pgn_kind == "file"
    assert loaded.settings.train_color == "black"
    assert loaded.settings.window_geometry == "1200x800+20+30"


def test_settings_store_update_keeps_unspecified_values():
    store = SettingsStore(
        AppSettings(
            last_pgn_folder="/tmp/pgn",
            last_pgn_path="/tmp/pgn",
            last_pgn_kind="folder",
            train_color="white",
            window_geometry="1000x700+10+10",
        )
    )

    store.update(train_color="black")

    assert store.settings.last_pgn_folder == "/tmp/pgn"
    assert store.settings.last_pgn_path == "/tmp/pgn"
    assert store.settings.last_pgn_kind == "folder"
    assert store.settings.train_color == "black"
    assert store.settings.window_geometry == "1000x700+10+10"


def test_wrong_move_summary_distinguishes_problems_from_events():
    store = StatsStore()

    repeated_events = [
        ("fen-one", "Bc4", "Bd3", "2026-05-23T10:00:00+00:00"),
        ("fen-one", "Bc4", "Bd3", "2026-05-23T10:01:00+00:00"),
        ("fen-one", "Bc4", "Bd3", "2026-05-23T10:02:00+00:00"),
        ("fen-two", "Nf3", "Nc3", "2026-05-23T10:03:00+00:00"),
    ]

    for fen_before, expected_san, played_san, timestamp in repeated_events:
        store.add_event(
            source_name="Italian.pgn",
            line_name="Italian A1",
            fen_before=fen_before,
            expected_san=expected_san,
            played_san=played_san,
            correct=False,
            timestamp=timestamp,
        )

    summary = store.wrong_move_summary_for_line(
        source_name="Italian.pgn",
        line_name="Italian A1",
    )

    problem_count = len(summary)
    event_count = sum(item.count for item in summary)

    assert problem_count == 2
    assert event_count == 4
    assert summary[0].fen_before == "fen-one"
    assert summary[0].expected_san == "Bc4"
    assert summary[0].played_san == "Bd3"
    assert summary[0].count == 3
    assert summary[1].fen_before == "fen-two"
    assert summary[1].expected_san == "Nf3"
    assert summary[1].played_san == "Nc3"
    assert summary[1].count == 1


def test_error_session_finds_selected_problem_by_position_expected_and_played():
    from opening_trainer.error_session import session_index_for_selected_problem
    from opening_trainer.stats_store import WrongMoveSummary

    session_positions = [
        WrongMoveSummary(
            fen_before="fen-one",
            expected_san="Bc4",
            played_san="Bd3",
            count=3,
            last_timestamp="2026-05-23T10:00:00+00:00",
        ),
        WrongMoveSummary(
            fen_before="fen-two",
            expected_san="Nf3",
            played_san="Nc3",
            count=1,
            last_timestamp="2026-05-23T10:01:00+00:00",
        ),
    ]

    selected_position = WrongMoveSummary(
        fen_before="fen-one",
        expected_san="Bc4",
        played_san="Bd3",
        count=99,
        last_timestamp="2026-05-23T11:00:00+00:00",
    )

    assert session_index_for_selected_problem(session_positions, selected_position) == 0


def test_error_session_does_not_match_different_played_move():
    from opening_trainer.error_session import session_index_for_selected_problem
    from opening_trainer.stats_store import WrongMoveSummary

    session_positions = [
        WrongMoveSummary(
            fen_before="fen-one",
            expected_san="Bc4",
            played_san="Bd3",
            count=3,
            last_timestamp="2026-05-23T10:00:00+00:00",
        ),
    ]

    selected_position = WrongMoveSummary(
        fen_before="fen-one",
        expected_san="Bc4",
        played_san="Nf3",
        count=1,
        last_timestamp="2026-05-23T10:01:00+00:00",
    )

    assert session_index_for_selected_problem(session_positions, selected_position) is None

def test_error_session_messages_describe_problem_and_history():
    from opening_trainer.error_session import (
        finished_session_message,
        loaded_session_message,
        solved_session_message,
        wrong_move_history_text,
    )
    from opening_trainer.stats_store import WrongMoveSummary

    problem = WrongMoveSummary(
        fen_before="fen-one",
        expected_san="Bc4",
        played_san="Bd3",
        count=3,
        last_timestamp="2026-05-23T10:00:00+00:00",
    )

    history = wrong_move_history_text(problem)

    assert history == "früher 3× aufgetreten"
    assert loaded_session_message(1, 16, history, 0, 0) == (
        "Fehlzugproblem 1 von 16 geladen · früher 3× aufgetreten · Sitzung: richtig 0 · falsch 0."
    )
    assert solved_session_message(1, 16, history, 1, 0) == (
        "Fehlzugproblem 1 von 16 gelöst · früher 3× aufgetreten · "
        "Sitzung: richtig 1 · falsch 0. Weiter mit „Nächstes Fehlzugproblem“."
    )
    assert solved_session_message(16, 16, history, 16, 0) == (
        "Letztes Fehlzugproblem gelöst · früher 3× aufgetreten · Sitzung: richtig 16 · falsch 0."
    )
    assert finished_session_message(16, 15, 1) == (
        "Fehlzug-Sitzung abgeschlossen: 16 Fehlzugprobleme · richtig 15 · falsch 1."
    )

def test_session_mode_text_includes_progress_and_counts():
    from opening_trainer.error_session import session_mode_text

    assert session_mode_text("Fehlzug-Sitzung", 2, 5, 1, 0) == (
        "Modus: Fehlzug-Sitzung · Fehlzugproblem 2 von 5 · richtig 1 · falsch 0"
    )


def test_wrong_move_session_counts_problems_not_historical_events():
    from opening_trainer.error_session import WrongMoveSession
    from opening_trainer.stats_store import WrongMoveSummary

    positions = [
        WrongMoveSummary(
            fen_before="fen-one",
            expected_san="Bc4",
            played_san="Bd3",
            count=3,
            last_timestamp="2026-05-23T10:00:00+00:00",
        ),
        WrongMoveSummary(
            fen_before="fen-two",
            expected_san="Nf3",
            played_san="Nc3",
            count=1,
            last_timestamp="2026-05-23T10:01:00+00:00",
        ),
    ]

    session = WrongMoveSession(positions=positions)

    assert session.total == 2
    assert session.correct == 0
    assert session.wrong == 0
    assert session.is_finished is False

    first = session.next_problem()
    assert first is positions[0]
    assert session.current_display_index() == 2

    session.mark_correct()
    assert session.correct == 1
    assert session.wrong == 0

    second = session.next_problem()
    assert second is positions[1]
    session.mark_wrong()

    assert session.correct == 1
    assert session.wrong == 1
    assert session.is_finished is True
    assert session.next_problem() is None


def test_wrong_move_session_can_start_at_selected_index():
    from opening_trainer.error_session import WrongMoveSession
    from opening_trainer.stats_store import WrongMoveSummary

    positions = [
        WrongMoveSummary("fen-one", "Bc4", "Bd3", 3, "2026-05-23T10:00:00+00:00"),
        WrongMoveSummary("fen-two", "Nf3", "Nc3", 1, "2026-05-23T10:01:00+00:00"),
        WrongMoveSummary("fen-three", "O-O", "h3", 2, "2026-05-23T10:02:00+00:00"),
    ]

    session = WrongMoveSession(positions=positions, index=1)

    assert session.total == 3
    assert session.current_display_index() == 2

    problem = session.next_problem()

    assert problem is positions[1]
    assert session.current_display_index() == 3


def test_wrong_move_session_can_start_at_last_selected_index():
    from opening_trainer.error_session import WrongMoveSession
    from opening_trainer.stats_store import WrongMoveSummary

    positions = [
        WrongMoveSummary("fen-one", "Bc4", "Bd3", 3, "2026-05-23T10:00:00+00:00"),
        WrongMoveSummary("fen-two", "Nf3", "Nc3", 1, "2026-05-23T10:01:00+00:00"),
        WrongMoveSummary("fen-three", "O-O", "h3", 2, "2026-05-23T10:02:00+00:00"),
    ]

    session = WrongMoveSession(positions=positions, index=2)

    assert session.current_display_index() == 3
    assert session.next_problem() is positions[2]
    assert session.is_finished is True
    assert session.next_problem() is None


def test_app_mode_labels_are_stable():
    from opening_trainer.app_mode import AppMode

    assert [mode.name for mode in AppMode] == [
        "IDLE",
        "VARIANT_TRAINING",
        "SECTION_TRAINING",
        "WRONG_MOVE_SESSION",
        "SET_TRAINING",
    ]
    assert AppMode.IDLE.value == "Bereit"
    assert AppMode.VARIANT_TRAINING.value == "Variantentraining"
    assert AppMode.SECTION_TRAINING.value == "Abschnittstraining"
    assert AppMode.WRONG_MOVE_SESSION.value == "Fehlzug-Sitzung"
    assert AppMode.SET_TRAINING.value == "Set-Training"

def test_settings_store_loads_invalid_json_as_defaults(tmp_path):
    from opening_trainer.settings_store import SettingsStore

    path = tmp_path / "settings.json"
    path.write_text("{broken", encoding="utf-8")

    store = SettingsStore.load(path)

    assert store.settings.last_pgn_folder == ""
    assert store.settings.last_pgn_path == ""
    assert store.settings.last_pgn_kind == ""
    assert store.settings.train_color == "white"
    assert store.settings.window_geometry == ""


def test_stats_store_loads_invalid_json_as_empty(tmp_path):
    from opening_trainer.stats_store import StatsStore

    path = tmp_path / "training_stats.json"
    path.write_text("{broken", encoding="utf-8")

    store = StatsStore.load(path)

    assert store.events == []


def test_export_training_events_csv_writes_header_and_rows(tmp_path):
    import csv

    from opening_trainer.stats_export import CSV_FIELDS, export_training_events_csv
    from opening_trainer.stats_store import StatsStore

    store = StatsStore()
    store.add_event(
        source_name="Italian.pgn",
        line_name="Italian A1",
        fen_before="fen-one",
        expected_san="Bc4",
        played_san="Bc4",
        correct=True,
        timestamp="2026-05-23T10:00:00+00:00",
    )
    store.add_event(
        source_name="Italian.pgn",
        line_name="Italian A1",
        fen_before="fen-two",
        expected_san="Nf3",
        played_san="Nc3",
        correct=False,
        timestamp="2026-05-23T10:01:00+00:00",
    )

    path = tmp_path / "exports" / "training_events.csv"

    export_training_events_csv(store, path)

    with path.open(encoding="utf-8", newline="") as csv_file:
        reader = csv.DictReader(csv_file)
        rows = list(reader)

    assert reader.fieldnames == CSV_FIELDS
    assert rows[0]["correct"] == "true"
    assert rows[0]["expected_san"] == "Bc4"
    assert rows[1]["correct"] == "false"
    assert rows[1]["played_san"] == "Nc3"


def test_export_training_events_csv_handles_empty_optional_moves(tmp_path):
    import csv

    from opening_trainer.stats_export import export_training_events_csv
    from opening_trainer.stats_store import StatsStore

    store = StatsStore()
    store.add_event(
        source_name="Italian.pgn",
        line_name="Italian A1",
        fen_before="fen-one",
        expected_san=None,
        played_san=None,
        correct=False,
        timestamp="2026-05-23T10:00:00+00:00",
    )

    path = tmp_path / "training_events.csv"

    export_training_events_csv(store, path)

    with path.open(encoding="utf-8", newline="") as csv_file:
        rows = list(csv.DictReader(csv_file))

    assert rows[0]["expected_san"] == ""
    assert rows[0]["played_san"] == ""


def test_summarize_training_sessions_groups_events_by_time_gap():
    from opening_trainer.session_log import summarize_training_sessions
    from opening_trainer.stats_store import TrainingEvent

    events = [
        TrainingEvent("2026-05-23T10:00:00+00:00", "Italian.pgn", "A1", "fen1", "Bc4", "Bc4", True),
        TrainingEvent("2026-05-23T10:20:00+00:00", "Italian.pgn", "A1", "fen2", "Nf3", "Nc3", False),
        TrainingEvent("2026-05-23T11:05:00+00:00", "Italian.pgn", "A1", "fen3", "O-O", "O-O", True),
    ]

    summaries = summarize_training_sessions(events, max_gap_minutes=30)

    assert len(summaries) == 2
    assert summaries[0].started_at == "2026-05-23T10:00:00+00:00"
    assert summaries[0].ended_at == "2026-05-23T10:20:00+00:00"
    assert summaries[0].attempts == 2
    assert summaries[0].correct == 1
    assert summaries[0].wrong == 1
    assert summaries[0].accuracy == 0.5
    assert summaries[1].attempts == 1
    assert summaries[1].correct == 1


def test_summarize_training_sessions_returns_empty_list_without_events():
    from opening_trainer.session_log import summarize_training_sessions

    assert summarize_training_sessions([]) == []


def test_overall_progress_aggregates_sessions_and_trend():
    from opening_trainer.session_log import overall_progress
    from opening_trainer.stats_store import TrainingEvent

    events = [
        TrainingEvent("2026-05-23T10:00:00+00:00", "S", "A", "f", "Bc4", "Bd3", False),
        TrainingEvent("2026-05-23T10:05:00+00:00", "S", "A", "f", "Nf3", "Nf3", True),
        TrainingEvent("2026-05-23T11:00:00+00:00", "S", "A", "f", "O-O", "O-O", True),
    ]

    overview = overall_progress(events)

    assert overview.session_count == 2
    assert overview.attempts == 3
    assert overview.correct == 2
    assert overview.wrong == 1
    assert overview.accuracy == 2 / 3
    assert overview.first_accuracy == 0.5
    assert overview.last_accuracy == 1.0


def test_overall_progress_without_events():
    from opening_trainer.session_log import overall_progress

    overview = overall_progress([])

    assert overview.session_count == 0
    assert overview.attempts == 0
    assert overview.first_accuracy is None
    assert overview.last_accuracy is None


from datetime import date

from opening_trainer.scheduler import Card, new_card, is_new, is_due, review, DEFAULT_EASE, MIN_EASE


def test_scheduler_new_card_defaults():
    c = new_card()
    assert c.interval_days == 0 and c.ease == DEFAULT_EASE and c.due == "" and c.reps == 0
    assert is_new(c) is True


def test_scheduler_is_due():
    today = date(2026, 6, 3)
    assert is_due(new_card(), today) is False  # neu = nicht fällig
    assert is_due(Card(due="2026-06-01"), today) is True   # überfällig
    assert is_due(Card(due="2026-06-03"), today) is True   # heute
    assert is_due(Card(due="2026-06-10"), today) is False  # später


def test_scheduler_pass_sequence_grows_interval():
    today = date(2026, 6, 3)
    c = review(new_card(), True, today)
    assert c.interval_days == 1 and c.reps == 1 and c.due == "2026-06-04"
    assert is_new(c) is False

    c = review(c, True, today)
    assert c.interval_days == 3 and c.reps == 2 and c.due == "2026-06-06"

    c = review(c, True, today)
    assert c.interval_days == 8 and c.reps == 3  # round(3 * 2.5) = 8


def test_scheduler_fail_resets_and_lowers_ease():
    today = date(2026, 6, 3)
    c = Card(interval_days=8, ease=2.5, due="2026-06-11", reps=3)
    c = review(c, False, today)
    assert c.interval_days == 0 and c.reps == 0 and c.due == "2026-06-03"
    assert c.ease == 2.3


def test_scheduler_ease_has_floor():
    today = date(2026, 6, 3)
    c = new_card()
    for _ in range(20):
        c = review(c, False, today)
    assert c.ease == MIN_EASE


from opening_trainer.schedule_store import ScheduleStore


def test_schedule_store_card_for_defaults_to_new():
    store = ScheduleStore()
    assert is_new(store.card_for("L.pgn", "A1")) is True


def test_schedule_store_round_trip(tmp_path):
    path = tmp_path / "schedule.json"
    store = ScheduleStore()
    store.set_card("L.pgn", "A1", Card(interval_days=3, ease=2.4, due="2026-06-06", reps=2, last_reviewed="2026-06-03"))

    store.save(path)
    loaded = ScheduleStore.load(path)

    c = loaded.card_for("L.pgn", "A1")
    assert c.interval_days == 3 and c.ease == 2.4 and c.due == "2026-06-06" and c.reps == 2


def test_schedule_store_loads_missing_and_corrupt_as_empty(tmp_path):
    assert ScheduleStore.load(tmp_path / "missing.json").cards == {}
    bad = tmp_path / "bad.json"
    bad.write_text("{kaputt", encoding="utf-8")
    assert ScheduleStore.load(bad).cards == {}


def test_opening_sides_set_get_and_none():
    from opening_trainer.opening_sides import OpeningSides, WHITE, NONE

    sides = OpeningSides()
    assert sides.side_of("Q.pgn", "A1") is None  # ohne Zuordnung
    sides.set_side("Q.pgn", "A1", WHITE)
    assert sides.side_of("Q.pgn", "A1") == WHITE
    sides.set_side("Q.pgn", "A1", NONE)
    assert sides.side_of("Q.pgn", "A1") == NONE  # bewusste „keine" bleibt erhalten


def test_opening_sides_round_trip_and_robust_load(tmp_path):
    from opening_trainer.opening_sides import OpeningSides, BLACK

    path = tmp_path / "sides.json"
    sides = OpeningSides()
    sides.set_side("Q.pgn", "C84 · Ruy López", BLACK)
    sides.save(path)

    loaded = OpeningSides.load(path)
    assert loaded.side_of("Q.pgn", "C84 · Ruy López") == BLACK

    assert OpeningSides.load(tmp_path / "missing.json").sides == {}
    bad = tmp_path / "bad.json"
    bad.write_text("{kaputt", encoding="utf-8")
    assert OpeningSides.load(bad).sides == {}


def test_schedule_store_due_lines_orders_reviews_then_news():
    london = load_pgn_text(TEST_PGN, source_name="London.pgn")[0]
    italian = load_pgn_text(ITALIAN_PGN, source_name="Italian.pgn")[0]
    french = load_pgn_text(FRENCH_PGN, source_name="French.pgn")[0]
    today = date(2026, 6, 3)

    store = ScheduleStore()
    # london: überfällig (älteres Datum), italian: heute fällig, french: neu
    store.set_card("London.pgn", london.name, Card(interval_days=2, ease=2.5, due="2026-06-01", reps=2))
    store.set_card("Italian.pgn", italian.name, Card(interval_days=1, ease=2.5, due="2026-06-03", reps=1))

    due = store.due_lines([london, italian, french], today, new_limit=10)

    # zuerst die fälligen nach Datum (london vor italian), dann die neue (french)
    assert due == [london, italian, french]

    # Neulimit greift
    assert store.due_lines([french], today, new_limit=0) == []


from opening_trainer.app_mode import AppMode
from opening_trainer.ui_state import UiStateInput, button_states


def _ui_state(**overrides) -> UiStateInput:
    defaults = dict(
        has_selected_line=False,
        has_current_line=False,
        has_training=False,
        mode=AppMode.IDLE,
        error_panel_active=False,
        has_error_rows=False,
        has_error_selection=False,
        has_error_session=False,
    )
    defaults.update(overrides)
    return UiStateInput(**defaults)


def test_button_states_idle_disables_everything():
    states = button_states(_ui_state())

    assert states.start is False
    assert states.restart is False
    assert states.undo is False
    assert states.solution is False
    assert states.repeat is False
    assert states.wrong_session is False
    assert states.selected_error is False
    assert states.session_next is False


def test_button_states_selected_line_enables_start_and_wrong_session():
    states = button_states(_ui_state(has_selected_line=True))

    assert states.start is True
    assert states.wrong_session is True
    assert states.restart is False
    assert states.repeat is False


def test_button_states_current_line_alone_enables_wrong_session():
    states = button_states(_ui_state(has_current_line=True))

    assert states.start is False
    assert states.wrong_session is True


def test_button_states_training_enables_basic_controls():
    states = button_states(
        _ui_state(has_training=True, mode=AppMode.VARIANT_TRAINING)
    )

    assert states.restart is True
    assert states.undo is True
    assert states.solution is True
    assert states.repeat is True


def test_button_states_repeat_only_in_variant_or_section_mode():
    section = button_states(
        _ui_state(has_training=True, mode=AppMode.SECTION_TRAINING)
    )
    wrong_move = button_states(
        _ui_state(has_training=True, mode=AppMode.WRONG_MOVE_SESSION)
    )

    assert section.repeat is True
    assert wrong_move.repeat is False
    assert wrong_move.undo is True


def test_button_states_selected_error_requires_panel_rows_and_selection():
    ready = button_states(
        _ui_state(
            error_panel_active=True,
            has_error_rows=True,
            has_error_selection=True,
        )
    )
    no_selection = button_states(
        _ui_state(
            error_panel_active=True,
            has_error_rows=True,
            has_error_selection=False,
        )
    )
    panel_inactive = button_states(
        _ui_state(
            error_panel_active=False,
            has_error_rows=True,
            has_error_selection=True,
        )
    )

    assert ready.selected_error is True
    assert no_selection.selected_error is False
    assert panel_inactive.selected_error is False


def test_button_states_session_next_follows_error_session():
    assert button_states(_ui_state(has_error_session=True)).session_next is True
    assert button_states(_ui_state(has_error_session=False)).session_next is False


def test_button_states_set_training_buttons_need_lines():
    ready = button_states(_ui_state(has_lines=True))
    empty = button_states(_ui_state(has_lines=False))

    assert ready.train_white is True
    assert ready.train_black is True
    assert ready.train_group is True
    assert empty.train_white is False
    assert empty.train_group is False


def test_button_states_next_line_only_in_set_training_when_finished():
    ready = button_states(_ui_state(mode=AppMode.SET_TRAINING, set_line_finished=True))
    not_finished = button_states(_ui_state(mode=AppMode.SET_TRAINING, set_line_finished=False))
    wrong_mode = button_states(_ui_state(mode=AppMode.VARIANT_TRAINING, set_line_finished=True))

    assert ready.next_line is True
    assert not_finished.next_line is False
    assert wrong_mode.next_line is False


def test_tab_for_mode_focuses_errors_only_in_wrong_move_session():
    from opening_trainer.ui_state import TAB_ERRORS, tab_for_mode

    assert tab_for_mode(AppMode.WRONG_MOVE_SESSION) == TAB_ERRORS
    assert tab_for_mode(AppMode.IDLE) is None
    assert tab_for_mode(AppMode.VARIANT_TRAINING) is None
    assert tab_for_mode(AppMode.SECTION_TRAINING) is None


from opening_trainer.training_run import TrainingRun


def test_training_run_empty_set_is_finished():
    run = TrainingRun(lines=[])

    assert run.total == 0
    assert run.is_finished is True
    assert run.current_line() is None
    assert run.progress_text() == "Set leer"


def test_training_run_walks_lines_in_order():
    run = TrainingRun(lines=["a", "b", "c"])

    assert run.total == 3
    assert run.is_finished is False
    assert run.current_line() == "a"
    assert run.current_display_index() == 1

    assert run.advance() == "b"
    assert run.current_line() == "b"
    assert run.current_display_index() == 2

    assert run.advance() == "c"
    assert run.current_display_index() == 3
    assert run.is_finished is False


def test_training_run_finishes_after_last_line():
    run = TrainingRun(lines=["a", "b"])

    run.advance()
    assert run.is_finished is False

    assert run.advance() is None
    assert run.is_finished is True
    assert run.current_line() is None
    assert run.advance() is None


def test_training_run_counts_correct_and_wrong():
    run = TrainingRun(lines=["a", "b"])

    run.mark_correct()
    run.mark_correct()
    run.mark_wrong()

    assert run.correct == 2
    assert run.wrong == 1


def test_training_run_progress_text():
    run = TrainingRun(lines=["a", "b", "c"])
    run.mark_correct()

    assert run.progress_text() == "Variante 1 von 3 · fehlerfrei 1 · mit Fehler 0"

    run.advance()
    run.advance()
    run.advance()

    assert run.progress_text() == "Set abgeschlossen · 3 Varianten · fehlerfrei 1 · mit Fehler 0"


def test_training_run_can_start_at_index():
    run = TrainingRun(lines=["a", "b", "c"], index=1)

    assert run.current_line() == "b"
    assert run.current_display_index() == 2


from opening_trainer.repertoire import SIDE_BLACK, SIDE_NONE, SIDE_WHITE


ITALIAN_PGN = """
[Event "I"]
[ChapterName "Italienisch A"]
[Result "*"]

1. e4 e5 *
"""

FRENCH_PGN = """
[Event "F"]
[ChapterName "Französisch A"]
[Result "*"]

1. e4 e6 *
"""


def test_category_side_defaults_to_none():
    assert RepertoireCategory(name="Englisch").side == SIDE_NONE


def test_repertoire_set_category_side_validates():
    repertoire = Repertoire(categories=[RepertoireCategory(name="Englisch")])

    assert repertoire.set_category_side("Englisch", SIDE_WHITE) is True
    assert repertoire.category("Englisch").side == SIDE_WHITE
    assert repertoire.set_category_side("Englisch", SIDE_NONE) is True
    assert repertoire.category("Englisch").side == SIDE_NONE
    assert repertoire.set_category_side("Fehlt", SIDE_WHITE) is False
    assert repertoire.set_category_side("Englisch", "grün") is False


def test_repertoire_lines_for_side_unions_dedup_and_keeps_order():
    london = load_pgn_text(TEST_PGN, source_name="London.pgn")[0]
    italian = load_pgn_text(ITALIAN_PGN, source_name="Italian.pgn")[0]
    french = load_pgn_text(FRENCH_PGN, source_name="French.pgn")[0]

    repertoire = Repertoire(
        categories=[
            RepertoireCategory(name="A", line_keys=[LineKey.from_line(london)], side=SIDE_WHITE),
            RepertoireCategory(
                name="B",
                line_keys=[LineKey.from_line(london), LineKey.from_line(italian)],
                side=SIDE_WHITE,
            ),
            RepertoireCategory(name="C", line_keys=[LineKey.from_line(french)], side=SIDE_BLACK),
        ]
    )

    all_lines = [london, italian, french]

    # london ist in A und B, erscheint aber nur einmal; Reihenfolge wie all_lines
    assert repertoire.lines_for_side(SIDE_WHITE, all_lines) == [london, italian]
    assert repertoire.lines_for_side(SIDE_BLACK, all_lines) == [french]
    assert repertoire.lines_for_side(SIDE_NONE, all_lines) == []


def test_repertoire_category_summaries_for_side():
    repertoire = Repertoire(
        categories=[
            RepertoireCategory(
                name="Englisch",
                line_keys=[LineKey("a.pgn", "1"), LineKey("a.pgn", "2")],
                side=SIDE_WHITE,
            ),
            RepertoireCategory(name="Slawisch", line_keys=[LineKey("b.pgn", "1")], side=SIDE_BLACK),
            RepertoireCategory(name="Offen", side=SIDE_NONE),
        ]
    )

    assert repertoire.category_summaries_for_side(SIDE_WHITE) == [("Englisch", 2)]
    assert repertoire.category_summaries_for_side(SIDE_BLACK) == [("Slawisch", 1)]
    assert repertoire.category_summaries_for_side(SIDE_NONE) == [("Offen", 0)]


def test_repertoire_store_round_trips_side(tmp_path):
    path = tmp_path / "rep.json"
    repertoire = Repertoire(categories=[RepertoireCategory(name="Englisch", side=SIDE_WHITE)])

    RepertoireStore(repertoire).save(path)
    loaded = RepertoireStore.load(path)

    assert loaded.repertoire.category("Englisch").side == SIDE_WHITE


def test_repertoire_store_loads_category_without_side_as_none(tmp_path):
    path = tmp_path / "rep.json"
    path.write_text('{"categories": [{"name": "Alt", "line_keys": []}]}', encoding="utf-8")

    loaded = RepertoireStore.load(path)

    assert loaded.repertoire.category("Alt").side == SIDE_NONE


def test_stats_store_aggregates_set_stats_over_lines():
    from opening_trainer.stats_store import SetStats

    london = load_pgn_text(TEST_PGN, source_name="London.pgn")[0]
    italian = load_pgn_text(ITALIAN_PGN, source_name="Italian.pgn")[0]
    french = load_pgn_text(FRENCH_PGN, source_name="French.pgn")[0]  # ungeübt

    store = StatsStore()
    for played, correct in [("d4", True), ("d4", True), ("Nf3", False)]:
        store.add_event(
            source_name="London.pgn",
            line_name=london.name,
            fen_before="f",
            expected_san="d4",
            played_san=played,
            correct=correct,
            timestamp="2026-05-23T10:00:00+00:00",
        )
    store.add_event(
        source_name="Italian.pgn",
        line_name=italian.name,
        fen_before="f",
        expected_san="e4",
        played_san="e4",
        correct=True,
        timestamp="2026-05-23T10:01:00+00:00",
    )

    set_stats = store.stats_for_lines([london, italian, french])

    assert set_stats.lines_total == 3
    assert set_stats.lines_trained == 2
    assert set_stats.attempts == 4
    assert set_stats.correct == 3
    assert set_stats.wrong == 1
    assert set_stats.accuracy == 0.75


def test_stats_store_set_stats_empty():
    from opening_trainer.stats_store import SetStats

    assert StatsStore().stats_for_lines([]) == SetStats(0, 0, 0, 0, 0, 0.0)


def test_stats_store_orders_weakest_first():
    london = load_pgn_text(TEST_PGN, source_name="London.pgn")[0]   # geübt, 100 %
    italian = load_pgn_text(ITALIAN_PGN, source_name="Italian.pgn")[0]  # geübt, 50 %
    french = load_pgn_text(FRENCH_PGN, source_name="French.pgn")[0]  # nie geübt

    store = StatsStore()
    for played, correct in [("d4", True), ("d4", True)]:
        store.add_event(source_name="London.pgn", line_name=london.name, fen_before="f",
                        expected_san="d4", played_san=played, correct=correct,
                        timestamp="2026-05-23T10:00:00+00:00")
    for played, correct in [("e4", True), ("Nf3", False)]:
        store.add_event(source_name="Italian.pgn", line_name=italian.name, fen_before="f",
                        expected_san="e4", played_san=played, correct=correct,
                        timestamp="2026-05-23T10:01:00+00:00")

    ordered = store.order_lines_weakest_first([london, italian, french])

    # nie geübt zuerst, dann nach Trefferquote aufsteigend (50 % vor 100 %)
    assert ordered == [french, italian, london]


def test_stats_store_orders_weakest_first_is_stable_without_stats():
    london = load_pgn_text(TEST_PGN, source_name="London.pgn")[0]
    italian = load_pgn_text(ITALIAN_PGN, source_name="Italian.pgn")[0]

    ordered = StatsStore().order_lines_weakest_first([london, italian])

    assert ordered == [london, italian]
