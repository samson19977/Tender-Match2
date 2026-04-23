#!/usr/bin/env python3
"""
matcher.py — CPI Tender Matcher | Full Pipeline CLI
AIMS KTT Hackathon · T2.2 · Multilingual Grant & Tender Matcher

Usage:
  python matcher.py --profile 02 --topk 5
  python matcher.py --all --topk 5 --lang fr
  python matcher.py --profile 07 --topk 5 --lang fr

Author: Samson Niyizurugero
"""

import os
import sys
import json
import argparse
import time
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from src.parser import load_tenders, load_profiles
from src.ranker import TenderRanker, get_top_disqualifier
from src.summarizer import generate_summary, generate_summary_md, generate_individual_summary_md
from src.utils import (
    ensure_dir, get_profile_language, format_budget,
    print_banner, compute_mrr, compute_recall, load_gold_matches, save_json
)


# ─── Pipeline ─────────────────────────────────────────────────────────────────

def run_pipeline(
    profile: dict,
    ranker: TenderRanker,
    top_k: int = 5,
    language: str = None,
    save_summaries: bool = True,
    verbose: bool = True,
) -> list:
    """
    Full pipeline: rank → explain → save.
    
    Args:
        profile: business profile dict
        ranker: pre-built TenderRanker instance
        top_k: number of results
        language: override language (None = use profile language)
        save_summaries: write .md files to summaries/
        verbose: print results to console
    
    Returns:
        List of ranked match dicts
    """
    lang = language or get_profile_language(profile)
    profile_id = profile.get("id", "00")

    if verbose:
        print_banner(f"Profile {profile_id}: {profile.get('name')} ({profile.get('sector')})")
        print(f"  Country: {profile.get('country')} | Language: {lang.upper()}")
        print(f"  Needs: {profile.get('needs_text', '')[:80]}...")
        print()

    # Step 1: Rank
    t0 = time.time()
    matches = ranker.rank(profile, top_k=top_k)
    rank_time = time.time() - t0

    if verbose:
        print(f"  ⏱  Ranked {len(ranker.tenders)} tenders in {rank_time:.2f}s\n")
        print(f"  {'#':<3} {'Tender ID':<8} {'Score':<7} {'Sector':<12} {'Budget':<12} {'Lang':<5} Title")
        print("  " + "-" * 90)

    for rank_idx, match in enumerate(matches, 1):
        # Attach rank for summarizer
        match["rank"] = rank_idx

        if verbose:
            budget_str = format_budget(match.get("budget", 0))
            title_short = match["title"][:45] + "..." if len(match["title"]) > 45 else match["title"]
            print(f"  #{rank_idx:<2} {match['tender_id']:<8} {match['score']:<7.4f} "
                  f"{match['sector']:<12} {budget_str:<12} {match['language'].upper():<5} {title_short}")

    if verbose:
        print()

    # Step 2: Generate summaries
    if save_summaries:
        ensure_dir("summaries")
        # One .md per profile (overview of all matches)
        md_content = generate_summary_md(profile, matches, language=lang)
        summary_path = f"summaries/profile_{profile_id}_{lang}.md"
        with open(summary_path, "w", encoding="utf-8") as f:
            f.write(md_content)
        if verbose:
            print(f"  📄 Profile summary saved: {summary_path}")

        # One .md per (profile, tender) pair — required by spec
        for match in matches:
            tid = match["tender_id"]
            disq = get_top_disqualifier(profile, match)
            individual_md = generate_individual_summary_md(
                profile=profile,
                match=match,
                rank=match["rank"],
                language=lang,
                disqualifier=disq,
            )
            pair_path = f"summaries/profile_{profile_id}_{tid}_{lang}.md"
            with open(pair_path, "w", encoding="utf-8") as f:
                f.write(individual_md)
        if verbose:
            print(f"  📄 {len(matches)} individual (profile, tender) summaries saved to summaries/")

    # Step 3: Verbose score breakdown
    if verbose:
        print(f"\n  Score Breakdown (Profile {profile_id}):")
        for match in matches:
            bd = match["breakdown"]
            disq = get_top_disqualifier(profile, match)
            print(f"    {match['tender_id']}: tfidf={bd['tfidf_similarity']:.3f} "
                  f"sector={bd['sector_match']:.3f} budget={bd['budget_score']:.3f} "
                  f"urgency={bd['urgency_score']:.3f} → total={match['score']:.4f}")
            print(f"      ⚠  Biggest disqualifier: {disq}")

    return matches


def run_all_profiles(
    tenders: list,
    profiles: list,
    top_k: int = 5,
    language: str = None,
    verbose: bool = True,
) -> dict:
    """Run matcher for all profiles and return predictions dict."""
    ranker = TenderRanker(tenders)
    all_results = {}

    total_start = time.time()
    for profile in profiles:
        lang = language or get_profile_language(profile)
        matches = run_pipeline(profile, ranker, top_k=top_k, language=lang, verbose=verbose)
        all_results[profile["id"]] = matches

    total_time = time.time() - total_start
    print_banner(f"✅ All {len(profiles)} profiles processed in {total_time:.1f}s")

    return all_results


def evaluate(profiles: list, all_results: dict, top_k: int = 5):
    """Compute and print MRR@k and Recall@k."""
    try:
        gold = load_gold_matches()
    except FileNotFoundError:
        print("  [WARN] data/gold_matches.csv not found — skipping evaluation")
        return

    predictions = {
        pid: [m["tender_id"] for m in matches]
        for pid, matches in all_results.items()
    }

    mrr = compute_mrr(gold, predictions, k=top_k)
    recall = compute_recall(gold, predictions, k=top_k)

    print_banner(f"📊 Evaluation Results (k={top_k})")
    print(f"  MRR@{top_k}    : {mrr:.4f}")
    print(f"  Recall@{top_k} : {recall:.4f}")

    # Show failure cases
    print(f"\n  Failure Cases (profile vs gold):")
    shown = 0
    for pid, gold_tids in gold.items():
        pred_list = predictions.get(pid, [])[:top_k]
        gold_set = set(gold_tids)
        hits = set(pred_list) & gold_set
        if not hits and shown < 3:
            print(f"    Profile {pid}: predicted={pred_list} | gold={gold_tids} | hits=0")
            shown += 1


# ─── CLI ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="CPI Tender Matcher — AIMS KTT Hackathon T2.2",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python matcher.py --profile 02 --topk 5
  python matcher.py --profile 07 --topk 5 --lang fr
  python matcher.py --all --topk 5
  python matcher.py --all --eval
        """
    )
    parser.add_argument("--profile", type=str, help="Profile ID (e.g., 02, 07)")
    parser.add_argument("--all", action="store_true", help="Run all profiles")
    parser.add_argument("--topk", type=int, default=5, help="Number of top matches (default: 5)")
    parser.add_argument("--lang", type=str, choices=["en", "fr"], help="Output language override")
    parser.add_argument("--eval", action="store_true", help="Run evaluation after matching")
    parser.add_argument("--tenders-dir", type=str, default="data/tenders", help="Tenders directory")
    parser.add_argument("--profiles-path", type=str, default="data/profiles.json", help="Profiles JSON")
    parser.add_argument("--quiet", action="store_true", help="Suppress verbose output")

    args = parser.parse_args()

    if not args.profile and not args.all:
        parser.print_help()
        sys.exit(1)

    print_banner("CPI Tender Matcher — AIMS KTT Hackathon T2.2")
    print(f"  Author: Samson Niyizurugero")
    print(f"  Tenders dir : {args.tenders_dir}")
    print(f"  Profiles    : {args.profiles_path}")
    print()

    # Load data
    tenders = load_tenders(args.tenders_dir)
    profiles = load_profiles(args.profiles_path)

    verbose = not args.quiet

    if args.all:
        all_results = run_all_profiles(tenders, profiles, top_k=args.topk, language=args.lang, verbose=verbose)
        if args.eval:
            evaluate(profiles, all_results, top_k=args.topk)
    else:
        # Single profile
        profile_map = {p["id"]: p for p in profiles}
        pid = args.profile.zfill(2)
        if pid not in profile_map:
            print(f"  [ERROR] Profile '{pid}' not found. Available: {list(profile_map.keys())}")
            sys.exit(1)
        profile = profile_map[pid]
        ranker = TenderRanker(tenders)
        run_pipeline(profile, ranker, top_k=args.topk, language=args.lang, verbose=verbose)


if __name__ == "__main__":
    main()
