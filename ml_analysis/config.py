"""All thresholds, weights and defaults in one place. Every run writes these to manifest.json."""
from __future__ import annotations
import json
from dataclasses import dataclass, field, asdict, fields


@dataclass
class Config:
    # ---- which leagues count as complete (recap) ----
    min_league_rounds: int = 8            # a league needs this many scored rounds to be 'complete'
    # ---- data handling ----
    halt_on_unjoined: bool = True         # stop if any vote row fails to join to a song
    performance_excluded_statuses: tuple = ("Forfeited", "Zero-vote", "Mismatch", "Unscored")
    default_cap: float = 1.0              # max votes per song when Rounds tab leaves it blank
    cap_overrides: dict = field(default_factory=dict)   # {league_number: cap}, wins over blank Rounds values
    # ---- league analysis ----
    top_n: int = 5
    twin_weights: tuple = (0.70, 0.30)    # (cosine, jaccard)
    twin_min_shared_rounds: int = 4
    twin_near_tie_margin: float = 0.03
    gem_min_eligible: int = 3
    gem_min_positive: int = 2
    gem_min_round_percentile: float = 0.50
    gem_weights: tuple = (0.70, 0.30)     # (breadth percentile, bad-finish percentile)
    gem_sensitivity_weights: tuple = (0.50, 0.50)
    # ---- recap thresholds ----
    min_submissions_average: int = 3
    min_submissions_award: int = 4
    min_shared_rounds_pair: int = 3
    min_ballots: int = 3
    high_vote_threshold: int = 3
    high_vote_cap_share: float = 0.30
    tie_tolerance: float = 1e-9
    # ---- recap scopes ----
    recap_periods: dict = field(default_factory=dict)   # {"Year One": [1,2,3,4,5,6,7]} extra named periods for the dashboard

    @classmethod
    def from_json(cls, path: str | None) -> "Config":
        cfg = cls()
        if not path:
            return cfg
        with open(path, encoding="utf-8") as fh:
            raw = json.load(fh)
        names = {f.name for f in fields(cls)}
        unknown = set(raw) - names
        if unknown:
            raise ValueError(f"Unknown config keys: {sorted(unknown)}")
        for k, v in raw.items():
            if k == "cap_overrides":
                v = {int(a): float(b) for a, b in v.items()}
            elif k == "recap_periods":
                v = {str(a): [int(x) for x in b] for a, b in v.items()}
            elif isinstance(getattr(cfg, k), tuple):
                v = tuple(v)
            setattr(cfg, k, v)
        return cfg

    def to_dict(self) -> dict:
        d = asdict(self)
        d["cap_overrides"] = {str(k): v for k, v in self.cap_overrides.items()}
        d["recap_periods"] = {str(k): list(v) for k, v in self.recap_periods.items()}
        return d
