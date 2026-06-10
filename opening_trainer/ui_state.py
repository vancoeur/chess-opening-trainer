from __future__ import annotations

from dataclasses import dataclass

from opening_trainer.app_mode import AppMode


@dataclass(frozen=True)
class UiStateInput:
    """Reiner Eingabezustand für die Button-Freigaben.

    Enthält nur die Entscheidungsgrundlagen, keine Tk-Widgets. Dadurch ist
    die Freigabelogik ohne laufende GUI testbar.
    """

    has_selected_line: bool
    has_current_line: bool
    has_training: bool
    mode: AppMode
    error_panel_active: bool
    has_error_rows: bool
    has_error_selection: bool
    has_error_session: bool
    has_lines: bool = False
    set_line_finished: bool = False


@dataclass(frozen=True)
class ButtonStates:
    """Freigabezustand je Trainingsbutton. True bedeutet aktiv."""

    start: bool
    restart: bool
    undo: bool
    solution: bool
    repeat: bool
    wrong_session: bool
    selected_error: bool
    session_next: bool
    train_white: bool
    train_black: bool
    train_group: bool
    next_line: bool


def button_states(state: UiStateInput) -> ButtonStates:
    """Bestimmt für jeden Trainingsbutton, ob er aktiv sein soll.

    Reine Funktion: gleiche Eingabe ergibt gleiche Ausgabe, keine
    Seiteneffekte. Die Logik entspricht dem früheren _update_ui_state.
    """

    variant_ready = state.has_selected_line
    wrong_session_ready = state.has_selected_line or state.has_current_line
    repeat_ready = state.has_training and state.mode in {
        AppMode.VARIANT_TRAINING,
        AppMode.SECTION_TRAINING,
    }
    selected_error_ready = (
        state.error_panel_active
        and state.has_error_rows
        and state.has_error_selection
    )
    next_line_ready = state.mode == AppMode.SET_TRAINING and state.set_line_finished

    return ButtonStates(
        start=variant_ready,
        restart=state.has_training,
        undo=state.has_training,
        solution=state.has_training,
        repeat=repeat_ready,
        wrong_session=wrong_session_ready,
        selected_error=selected_error_ready,
        session_next=state.has_error_session,
        train_white=state.has_lines,
        train_black=state.has_lines,
        train_group=state.has_lines,
        next_line=next_line_ready,
    )


# Bezeichner der rechten Reiter.
TAB_LIBRARY = "library"
TAB_ERRORS = "errors"


def tab_for_mode(mode: AppMode) -> str | None:
    """Welcher Reiter beim Moduswechsel in den Vordergrund soll.

    Reine Funktion. None bedeutet: aktiven Reiter nicht wechseln, damit die
    App den Nutzer nicht ungefragt wegspringt.
    """
    if mode == AppMode.WRONG_MOVE_SESSION:
        return TAB_ERRORS
    return None
