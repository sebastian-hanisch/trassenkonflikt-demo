"""Feste Annahmen, Regler-Stufen, Presets und Farben der Trassenkonflikt-Demo (eine Wahrheitsquelle)."""

# ------------------------------------------------------------------ Strecke (feste Annahmen)
N_SEG = 5                   # Abschnitte der eingleisigen Strecke (Stationen 0..5)
N_OPS = 3                   # Bahnunternehmen A, B, C
OP_NAMES = ("A", "B", "C")
WINDOW = 120                # Wunschabfahrten liegen in den ersten 120 min
FAST_PCT = (60, 30, 30)     # Schnellzug-Anteil je Operator (Prozent)
CP_TIME_LIMIT = 15.0        # Sekunden je CP-SAT-Lauf live
CP_TIME_LIMIT_BUTTON = 60.0
FAIR_SMALL_PCT = 10.0       # Fairness gilt als „fast umsonst“, wenn sie weniger als so viel Prozent Gesamtverspätung kostet

# ------------------------------------------------------------------ Regler
TRAINS_OPTIONS = (6, 8, 10)
DEFAULT_TRAINS = 8
CLEAR_OPTIONS = (1, 2, 3)           # Räumzeit nach jedem Abschnitt (min)
DEFAULT_CLEAR = 2
SHARE_OPTIONS = tuple(range(30, 71, 10))   # Anteil der Züge von Operator A (Prozent, Regler mit Schritt 10); B und C teilen den Rest im Verhältnis 3:2; die Messreihe kennt 30, 50 und 70
DEFAULT_SHARE = 50
FAVOURED_OPTIONS = (0, 1, 2)        # bevorzugter Operator bei der Vorrangregel
DEFAULT_FAVOURED = 0
SEED_MIN, SEED_MAX = 0, 9999
DEFAULT_SEED = 500
VIEW_OPTIONS = ("fcfs", "prio", "search", "opt", "fair")
DEFAULT_VIEW = "fcfs"

METHODS = ("fcfs", "prio", "search", "opt", "fair")
METHOD_LABELS = {"fcfs": "Erstanmelder (FCFS)", "prio": "Vorrang", "search": "Reihenfolge verbessert", "opt": "Optimum Gesamtverspätung", "fair": "Fair (Min-Max, dann Summe)"}
METHOD_COLORS = {"fcfs": "#7d8898", "prio": "#c0392b", "search": "#c77700", "opt": "#2a6fb0", "fair": "#2e7d4f"}
OP_COLORS = ("#2a6fb0", "#c77700", "#8e44ad")

# ------------------------------------------------------------------ Messreihe
RESULTS_FILE = "data/trs_results.json"
SWEEP_SEEDS = range(100, 120)
SWEEP_SIZES = (6, 8, 10)
SWEEP_VARIANTS = (          # Name -> (Züge, Räumzeit, Anteil A, bevorzugter Operator)
    ("Standard (8 Züge)", 8, 2, 50, 0),
    ("6 Züge", 6, 2, 50, 0),
    ("10 Züge", 10, 2, 50, 0),
    ("Räumzeit 1 min", 8, 1, 50, 0),
    ("Räumzeit 3 min", 8, 3, 50, 0),
    ("Anteil A 30 %", 8, 2, 30, 0),
    ("Anteil A 70 %", 8, 2, 70, 0),
    ("Vorrang für B", 8, 2, 50, 1),
    ("Vorrang für C", 8, 2, 50, 2),
)
SWEEP_CP_LIMIT = 30.0

# ------------------------------------------------------------------ Presets (Seeds liegen außerhalb der Messreihen-Seeds)
PRESET_ORDER = ["Standard", "Dichter Verkehr", "Dünner Verkehr", "Dominanter Operator", "Enge Räumzeit"]
PRESETS = {
    "Standard": {"trains": 8, "clear": 2, "share": 50, "favoured": 0, "seed": 500},
    "Dichter Verkehr": {"trains": 10, "clear": 2, "share": 50, "favoured": 0, "seed": 500},
    "Dünner Verkehr": {"trains": 6, "clear": 2, "share": 50, "favoured": 0, "seed": 500},
    "Dominanter Operator": {"trains": 8, "clear": 2, "share": 70, "favoured": 1, "seed": 500},
    "Enge Räumzeit": {"trains": 8, "clear": 3, "share": 50, "favoured": 0, "seed": 500},
}
PRESET_HELP = {
    "Standard": "8 Züge von drei Bahnunternehmen auf einem Gleis: der Grundfall.",
    "Dichter Verkehr": "10 Züge im selben Zeitfenster: mehr Konflikte, die Regeln kosten mehr.",
    "Dünner Verkehr": "6 Züge: wenige Konflikte, die Regeln liegen näher am Optimum.",
    "Dominanter Operator": "Operator A stellt 70 % der Züge, Operator B hat Vorrang: die kleinen Unternehmen tragen die Verspätung.",
    "Enge Räumzeit": "3 statt 2 Minuten Räumzeit je Abschnitt: weniger Züge passen hintereinander.",
}


def op_name(i):
    return OP_NAMES[i]


def shares_for(share_a: int) -> list:
    rest = 100 - share_a
    b = rest * 3 // 5
    return [share_a, b, rest - b]


def fmt_min(x, digits=0):
    return f"{x:.{digits}f} min"
