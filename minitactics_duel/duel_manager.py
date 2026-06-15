# duel_manager.py
import random
import importlib
from config import DUEL_TYPES  # ABSOLUTE import; works when running as a script

# New minigames; import lazily
_MODS = {
    "RUNE_WEAVE":      "rune_weave",
    "GUARD_BREAK":     "guard_break",
    "SKIRMISH_LANES":  "skirmish_lanes",
    "ARC_SHOT":        "arc_shot",
    "SUDDEN_SPARK":    "sudden_spark",  # used explicitly as a tiebreaker
}

def _run_module(mod, screen, defender="CPU", difficulty="NORMAL", context=None):
    """
    Call either `run(...)` or construct a *Duel class and call .run().
    """
    if hasattr(mod, "run"):
        return mod.run(screen, defender=defender, difficulty=difficulty, context=context)
    # else: look for a class that ends with "Duel"
    duel_cls = None
    for name, obj in mod.__dict__.items():
        if name.endswith("Duel") and isinstance(obj, type):
            duel_cls = obj
            break
    if duel_cls is None and hasattr(mod, "Duel"):
        duel_cls = getattr(mod, "Duel")
    if duel_cls is None:
        raise RuntimeError(f"No runnable entry point found in {mod.__name__}")
    duel = duel_cls(screen, defender=defender, difficulty=difficulty, context=context)
    return duel.run()

class DuelManager:
    def __init__(self, screen):
        self.screen = screen

    def random_type(self):
        return random.choice(DUEL_TYPES)

    def run(self, duel_type=None, defender="CPU", difficulty="NORMAL", context=None):
        if duel_type is None:
            duel_type = self.random_type()
        mod_name = _MODS.get(duel_type)
        if not mod_name:
            raise ValueError(f"Unknown duel type: {duel_type}")

        # ABSOLUTE import so top-level script runs work:
        mod = importlib.import_module(f"duels.{mod_name}")
        return _run_module(mod, self.screen, defender=defender, difficulty=difficulty, context=context)
