"""
Stage 2: Fact Decomposition
Input: full script with labeled ERA sections
Output: episode.facts[] populated with fact_id, era_label, year_range, summary, narration_text

This stage parses the script's ERA sections into structured Fact objects.
"""

import json
import logging
import re
from pathlib import Path
from typing import List, Optional

from schema import Episode, Fact, FactStatus, EpisodeStatus

logger = logging.getLogger(__name__)


def extract_eras_from_script(script_body: str) -> List[dict]:
    """
    Extract ERA sections from script body.
    Expects format:
        === ERA 1: [Era Name] (Year Range) ===
        [narration text]
        
        === ERA 2: [Era Name] (Year Range) ===
        [narration text]
    """
    
    # Pattern to match ERA headers
    era_pattern = r"=+\s*ERA\s+(\d+):\s*([^(]+)\s*\(([^)]+)\)\s*=+"
    sections = re.split(era_pattern, script_body)
    
    eras = []
    
    # Skip the first element if it's just header junk
    for i in range(1, len(sections), 4):
        if i + 2 < len(sections):
            era_num = sections[i].strip()
            era_name = sections[i + 1].strip()
            year_range = sections[i + 2].strip()
            narration_text = sections[i + 3].strip() if i + 3 < len(sections) else ""
            
            eras.append({
                "era_num": era_num,
                "era_label": era_name,
                "year_range": year_range,
                "narration_text": narration_text,
            })
    
    return eras


def decompose_facts(
    episode: Episode,
) -> Episode:
    """
    Decompose the full script into Fact objects (eras).
    
    Args:
        episode: Episode with full_script populated
    
    Returns:
        Updated episode with facts[] populated
    """
    
    if not episode.full_script:
        logger.error(f"Episode {episode.episode_id} has no full_script. Run Stage 1 first.")
        episode.error_message = "Missing full_script"
        episode.status = EpisodeStatus.FAILED
        return episode

    logger.info(f"Decomposing script into facts for {episode.episode_id}")

    try:
        eras = extract_eras_from_script(episode.full_script)
        
        if not eras:
            logger.warning(
                f"No ERA sections found in script for {episode.episode_id}. "
                "Falling back to simple paragraph splitting."
            )
            # Fallback: split by double newlines
            paragraphs = [p.strip() for p in episode.full_script.split("\n\n") if p.strip()]
            eras = [
                {
                    "era_num": str(i + 1),
                    "era_label": f"Chapter {i + 1}",
                    "year_range": "TBD",
                    "narration_text": para,
                }
                for i, para in enumerate(paragraphs)
            ]

        # Convert eras to Fact objects
        episode.facts = []
        for era in eras:
            fact = Fact(
                fact_id=f"fact_{era['era_num'].lower()}",
                era_label=era["era_label"],
                year_range=era["year_range"],
                summary="",  # Will be filled in later if needed
                narration_text=era["narration_text"],
                chunks=[],
                status=FactStatus.PENDING,
            )
            episode.facts.append(fact)

        episode.status = EpisodeStatus.FACTS_DECOMPOSED
        logger.info(f"Decomposed into {len(episode.facts)} facts")
        return episode

    except Exception as e:
        logger.error(f"Failed to decompose facts for {episode.episode_id}: {e}")
        episode.error_message = str(e)
        episode.status = EpisodeStatus.FAILED
        raise


if __name__ == "__main__":
    import sys
    
    logging.basicConfig(level=logging.INFO)

    if len(sys.argv) < 2:
        print("Usage: python 02_decompose_facts.py <episode_json_path>")
        sys.exit(1)

    episode_path = sys.argv[1]
    
    # Load episode
    with open(episode_path, 'r') as f:
        episode_data = json.load(f)
    episode = Episode(**episode_data)

    # Decompose
    episode = decompose_facts(episode)

    # Save
    with open(episode_path, 'w') as f:
        json.dump(episode.model_dump(), f, indent=2, default=str)

    print(f"\n✓ Decomposed into {len(episode.facts)} facts")
    for fact in episode.facts:
        print(f"  - {fact.era_label} ({fact.year_range})")
