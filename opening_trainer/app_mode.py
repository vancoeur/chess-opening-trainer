from __future__ import annotations

from enum import Enum


class AppMode(Enum):
    IDLE = "Bereit"
    VARIANT_TRAINING = "Variantentraining"
    SECTION_TRAINING = "Abschnittstraining"
    WRONG_MOVE_SESSION = "Fehlzug-Sitzung"
    SET_TRAINING = "Set-Training"
