# Legacy: old Tkinter program

These files are the **earlier Tkinter interface** (as it was before the switch
to Qt). They are **no longer the main program** — the active app is the Qt
version (`qt_app/`, start with `python3 qt_main.py`, packaged as
“Opening Trainer.app”).

Kept here for reference only:
- `main.py` – old entry point (Tkinter)
- `ui_app.py` – old Tkinter interface
- `board_widget.py` – old Tkinter board (Unicode pieces)

The **core logic** (PGN, training, statistics, repertoire, scheduler …) still
lives in `opening_trainer/` and is used by both interfaces.

Start (only if needed): `python3 -m legacy.main`
