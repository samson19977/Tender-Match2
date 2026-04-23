#!/usr/bin/env python3
"""
src/utils.py — Shared Utilities
"""

import os
import json
from pathlib import Path


def ensure_dir(path: str):
    """Create directory if it doesn't exist."""
    Path(path).mkdir(parents=True, exist_ok=True)


def save_json(data, path: str):
    """Save data as JSON."""
    ensure_dir(str(Path(path).parent))
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def load_json(path: str):
    """Load JSON file."""
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def get_profile_language(profile: dict) -> str:
    """Get primary language for a profile."""
    langs = profile.get("languages", ["en"])
    return langs[0] if langs else "en"


def format_budget(amount: int) -> str:
    """Format budget as readable string."""
    if amount >= 1_000_000:
        return f"USD {amount/1_000_000:.1f}M"
    elif amount >= 1_000:
        return f"USD {amount:,}"
    elif amount == 0:
        return "Budget TBD"
    else:
        return f"USD {amount}"


def print_banner(text: str, width: int = 60):
    """Print a styled banner."""
    print("\n" + "=" * width)
    print(f"  {text}")
    print("=" * width)


def compute_mrr(gold_matches: dict, predictions: dict, k: int = 5) -> float:
    """
    Compute Mean Reciprocal Rank @ k.
    
    Args:
        gold_matches: {profile_id: [tender_id, ...]} (ordered by relevance)
        predictions: {profile_id: [tender_id, ...]} (ordered by model rank)
        k: cutoff
    
    Returns:
        MRR@k score (0–1)
    """
    rr_sum = 0.0
    count = 0
    for profile_id, gold_tids in gold_matches.items():
        gold_set = set(gold_tids)
        pred_list = predictions.get(profile_id, [])[:k]
        for rank_idx, tid in enumerate(pred_list, 1):
            if tid in gold_set:
                rr_sum += 1.0 / rank_idx
                break
        count += 1
    return rr_sum / count if count > 0 else 0.0


def compute_recall(gold_matches: dict, predictions: dict, k: int = 5) -> float:
    """
    Compute Recall @ k.
    
    Args:
        gold_matches: {profile_id: [tender_id, ...]}
        predictions: {profile_id: [tender_id, ...]}
        k: cutoff
    
    Returns:
        Recall@k score (0–1)
    """
    recall_sum = 0.0
    count = 0
    for profile_id, gold_tids in gold_matches.items():
        gold_set = set(gold_tids)
        pred_list = predictions.get(profile_id, [])[:k]
        hits = len(set(pred_list) & gold_set)
        recall_sum += hits / len(gold_set) if gold_set else 0.0
        count += 1
    return recall_sum / count if count > 0 else 0.0


def load_gold_matches(gold_path: str = "data/gold_matches.csv") -> dict:
    """Load gold matches from CSV. Returns {profile_id: [tender_ids]}."""
    gold = {}
    with open(gold_path, "r") as f:
        lines = f.read().strip().split("\n")
    for line in lines[1:]:  # skip header
        parts = line.split(",")
        if len(parts) >= 2:
            pid, tid = parts[0].strip(), parts[1].strip()
            gold.setdefault(pid, []).append(tid)
    return gold
