"""
Stage 3: Chunk Decomposition
Input: episode.facts[] with narration_text
Output: episode.facts[].chunks[] populated

Each Fact is split into small narration beats (Chunks), each ~5-15 seconds / 1-3 sentences.
These are the units that map 1:1 to generated images/clips.
"""

import json
import logging
from typing import List

from schema import Episode, Chunk, ChunkStatus, FactStatus, EpisodeStatus
from llm_client import LLMClient

logger = logging.getLogger(__name__)


def decompose_chunks_for_fact(
    fact_narration: str,
    fact_id: str,
    llm_client: LLMClient,
) -> List[Chunk]:
    """
    Break a fact's narration into short sequential chunks (visual beats).
    
    Args:
        fact_narration: Full narration text for one fact
        fact_id: ID of the parent fact
        llm_client: LLM client
    
    Returns:
        List of Chunk objects
    """
    
    system_prompt = """You are an expert at breaking down long-form narration into short visual beats.
Each beat should be 1-3 sentences, representing 5-15 seconds of spoken content.
Each beat will be paired with a single generated image or short animation clip."""

    user_prompt = f"""Break the following narration into short sequential chunks. Each chunk represents ONE visual moment.

Output as JSON array:
[
  {{
    "chunk_num": 1,
    "narration_text": "exact verbatim text from narration (don't rewrite)",
    "visual_focus": "what should be on screen to support this narration"
  }},
  ...
]

NARRATION:
{fact_narration}

GUIDELINES:
- Keep narration text verbatim, no rewrites
- 1-3 sentences per chunk
- Visual focus should be specific and actionable for image generation
- Aim for 4-8 chunks per fact depending on length
"""

    try:
        response = llm_client.prompt_structured(
            user_prompt=user_prompt,
            system_prompt=system_prompt,
            use_cache=True,
        )

        chunks = []
        for item in response:
            chunk_id = f"{fact_id}_chunk{item.get('chunk_num', 1)}"
            chunk = Chunk(
                chunk_id=chunk_id,
                narration_text=item.get("narration_text", ""),
                visual_prompt=None,  # Filled in later by Stage 4
                duration_estimate_sec=0.0,  # Filled in later by Stage 6 (TTS)
                status=ChunkStatus.PENDING,
            )
            chunks.append(chunk)

        return chunks

    except Exception as e:
        logger.error(f"Failed to decompose chunks for fact {fact_id}: {e}")
        raise


def decompose_all_chunks(
    episode: Episode,
    llm_client: LLMClient,
    parallel: bool = False,
) -> Episode:
    """
    Decompose all facts in an episode into chunks.
    
    Args:
        episode: Episode with facts[] populated
        llm_client: LLM client
        parallel: If True, process facts in parallel (future enhancement)
    
    Returns:
        Updated episode with chunks[] populated in each fact
    """
    
    if not episode.facts:
        logger.error(f"Episode {episode.episode_id} has no facts. Run Stage 2 first.")
        episode.error_message = "Missing facts"
        episode.status = EpisodeStatus.FAILED
        return episode

    logger.info(f"Decomposing {len(episode.facts)} facts into chunks for {episode.episode_id}")

    try:
        for fact in episode.facts:
            logger.info(f"Processing fact: {fact.fact_id} ({fact.era_label})")
            chunks = decompose_chunks_for_fact(
                fact.narration_text,
                fact.fact_id,
                llm_client,
            )
            fact.chunks = chunks
            fact.status = FactStatus.DECOMPOSED
            logger.info(f"  → {len(chunks)} chunks generated")

        episode.status = EpisodeStatus.CHUNKS_DECOMPOSED
        logger.info(f"All facts decomposed. Total chunks: {sum(len(f.chunks) for f in episode.facts)}")
        return episode

    except Exception as e:
        logger.error(f"Failed to decompose chunks for {episode.episode_id}: {e}")
        episode.error_message = str(e)
        episode.status = EpisodeStatus.FAILED
        raise


if __name__ == "__main__":
    import sys
    
    logging.basicConfig(level=logging.INFO)

    if len(sys.argv) < 2:
        print("Usage: python 03_decompose_chunks.py <episode_json_path>")
        sys.exit(1)

    episode_path = sys.argv[1]
    
    # Load episode
    with open(episode_path, 'r') as f:
        episode_data = json.load(f)
    episode = Episode(**episode_data)

    # Initialize LLM client
    llm_client = LLMClient(
        model="claude-3-5-sonnet-20241022",
        cache_dir=".cache/llm"
    )

    # Decompose
    episode = decompose_all_chunks(episode, llm_client)

    # Save
    with open(episode_path, 'w') as f:
        json.dump(episode.model_dump(), f, indent=2, default=str)

    total_chunks = sum(len(f.chunks) for f in episode.facts)
    print(f"\n✓ Decomposed into {total_chunks} total chunks:")
    for fact in episode.facts:
        print(f"  - {fact.era_label}: {len(fact.chunks)} chunks")
