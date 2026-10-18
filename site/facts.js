/* Single source of truth for every number on the page. Strict JSON inside the assignment so tests can parse it.
   Each group has a "_src" note (where it comes from). Nothing here is invented; "estimate" items say so. */
window.FACTS = {
  "collision": {
    "_src": "docs/RESULTS.md, Round 6 (fresh run, 2026-10-18, 9 levels x 10 runs per side, evals/harbor/stats.py)",
    "runs_total": 180, "levels_count": 9, "runs_per_level_side": 10, "runs_per_side": 90,
    "with_clean": 72, "without_clean": 48, "with_pct": 80, "without_pct": 53,
    "gap_points": 26.7, "ci_level": 95, "ci_low": 13.3, "ci_high": 40.4, "p_below": 0.001,
    "cost_clean_with": 0.0113, "cost_clean_without": 0.0159, "cost_clean_drop_pct": 29,
    "cost_run_with": 0.0090, "cost_run_without": 0.0085, "cost_run_diff_pct": 6,
    "levels": [
      {"id": "L1", "without": 6, "with": 9},
      {"id": "L2", "without": 9, "with": 10},
      {"id": "L3", "without": 0, "with": 9, "note": "three sessions adding discount, tax and a report to the same code"},
      {"id": "L4", "without": 3, "with": 7, "note": "a rename while features land"},
      {"id": "L6", "without": 0, "with": 1, "note": "two sessions both adding the same stock reservation (not fixed)"},
      {"id": "L7", "without": 9, "with": 10},
      {"id": "L8", "without": 9, "with": 9},
      {"id": "L9", "without": 7, "with": 10},
      {"id": "L10", "without": 5, "with": 7}
    ]
  },
  "memory": {
    "_src": "docs/RESULTS-RELAY.md (150 runs, 3 setups; tasks R1-R4 pooled, 40 runs each; R5 control; R6 addendum)",
    "runs_total": 150, "setups": 3, "pooled_runs_each": 40,
    "tool_pass": 38, "notes_pass": 37, "none_pass": 18,
    "tool_pct": 95, "notes_pct": 92, "none_pct": 45,
    "cost_success_tool": 0.0058, "cost_success_notes": 0.0068, "cost_success_none": 0.0117,
    "irrelevant_cost_pct": 7,
    "task_continue": {"tool": 10, "none": 0},
    "task_rule": {"tool": 8, "none": 0, "recheck": 10},
    "task_convention": {"tool": 10, "none": 8},
    "task_runs": 10,
    "r6": {"tool": 10, "notes": 9, "none": 0, "runs": 10, "irrelevant_rules": 20}
  },
  "cost": {
    "_src": "docs/RESULTS-TOKENS.md and docs/RESULTS.md round 6; README (hooks, fail-open); docs/UI.md (board polling)",
    "first_version_pct": 31, "first_ratio": 1.31, "shipped_ratio": 1.04, "base_ratio": 1.00, "turns_ratio": 0.99,
    "hook_seconds": 0.1, "hook_errors": 0, "board_poll_seconds": 1.5
  },
  "cochange": {
    "_src": "docs/RESULTS-COCHANGE.md (offline, 6 real open-source Python projects, held-out last 30% of history)",
    "projects": 6, "cases": 2716,
    "hit_pct": 66.5, "hit_pct_same_cases": 64.9, "same_folder_pct": 56.0, "most_changed_pct": 53.1,
    "strict_right_pct": 73, "strict_shown_pct": 17,
    "query_ms": 0.3, "index_commits": 800, "index_s_low": 0.2, "index_s_high": 0.3
  },
  "retract": {
    "_src": "docs/RESULTS-PROVENANCE.md and docs/FALKORDB-DEEP-DIVE.md (25 generated test graphs)",
    "graphs": 25, "notes_each": 200, "ms": 3, "precision": 1.0, "recall": 1.0,
    "search_mixed_pct": 65, "search_paraphrase_pct": 0
  },
  "second": {
    "_src": "docs/RESULTS.md round 7, part 2 (second, stronger model; levels L3, L4, L9, 8 runs each, list prices)",
    "runs": 24, "with_clean": 20, "without_clean": 8, "with_pct": 83, "without_pct": 33,
    "gap_points": 50, "ci_low": 25, "ci_high": 72, "p": 0.001, "levels_count": 3, "runs_per_level": 8,
    "cost_clean_with": 0.115, "cost_clean_without": 0.314, "models": 2
  },
  "proof": {"_src": "180 collision runs + 150 memory runs (docs/RESULTS.md round 6, docs/RESULTS-RELAY.md)", "total_runs": 330},
  "tests": {"_src": "automatic test suite (tests/), all passing", "count": 245},
  "calc": {
    "_src": "ESTIMATE inputs. Defaults are deliberately modest assumptions, not measurements. weeks_per_month = 52 / 12.",
    "default_sessions": 40, "default_cost": 0.5, "default_share_pct": 20, "weeks_per_month": 4.33, "weeks_per_year": 52, "months_per_year": 12
  },
  "example": {
    "_src": "example text copied from docs/RESULTS-COCHANGE.md and the demo; illustrative, not a statistic",
    "ticket": 12, "commits_total": 11, "commits_a": 9, "commits_b": 7
  }
};
