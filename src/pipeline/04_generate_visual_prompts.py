"""
Stage 4: Visual Prompt Generation
Input: episode with chunks decomposed + channel concept + style guide
Output: visual_prompt string per chunk, ready for image generation model

This stage injects style guide keywords and era context into each chunk
to ensure visual consistency across the entire episode.
"""

import json
import logging
from pathlib import Path
from typing import Dict, Any

from schema import Episode, EpisodeStatus
from llm_client import LLMClient

logger = logging.getLogger(__name__)


def load_style_guide(config_path: str = "config/style_guide.json") -> Dict[str, Any]:
    """Load style guide from JSON file."""
    with open(config_path, 'r') as f:
        return json.load(f)


def generate_visual_prompts(
    episode: Episode,
    llm_client: LLMClient,
    style_guide: Dict[str, Any],
) -> Episode:
    """
    Generate image generation prompts for all chunks in the episode.
    
    The same style keywords are injected into every prompt to ensure
    visual consistency across the entire episode.
    
    Args:
        episode: Episode with chunks populated
        llm_client: LLM client
        style_guide: Style guide config
    
    Returns:
        Updated episode with visual_prompt filled in each chunk
    """
    
    if not episode.facts:
        logger.error(f"Episode {episode.episode_id} has no facts. Run Stage 3 first.")
        episode.error_message = "Missing facts/chunks"
        episode.status = EpisodeStatus.FAILED
        return episode

    logger.info(f"Generating visual prompts for {episode.episode_id}")

    # Build locked style keywords that will be injected into every prompt
    locked_style = " ".join(style_guide.get("locked_keywords", []))

    system_prompt = f"""You are an expert image prompt engineer for animated documentary content.
Your job is to create vivid, specific image generation prompts that will be used to create visual sequences.

VISUAL STYLE (ALWAYS INCLUDE IN EVERY PROMPT):
{locked_style}

GUIDELINES:
- Be specific and visual
- Include lighting, composition, and mood
- Reference the era/time period when relevant
- No text or narration in the description itself (text will be added separately)
- Optimize for flat-vector or cartoon rendering
- Make it actionable for an AI image model like Flux or DALL-E
"""

    try:
        total_chunks = sum(len(fact.chunks) for fact in episode.facts)
        processed = 0

        for fact in episode.facts:
            era_context = f"{fact.era_label} ({fact.year_range})"
            
            for chunk in fact.chunks:
                # Build focused prompt for this chunk
                user_prompt = f"""Generate an image prompt for this narration chunk.

ERA/CONTEXT: {era_context}
NARRATION: {chunk.narration_text}

Output ONLY the image prompt as a single paragraph, no JSON, no formatting. Make it concise (2-4 sentences).
Focus on what should be visually shown to support this narration.
"""

                response = llm_client.prompt(
                    user_prompt=user_prompt,
                    system_prompt=system_prompt,
                    json_mode=False,
                    use_cache=True,
                )

                chunk.visual_prompt = response.strip()
                processed += 1

                if processed % 5 == 0:
                    logger.info(f"Progress: {processed}/{total_chunks} chunks")

        episode.status = EpisodeStatus.VISUAL_PROMPTS_GENERATED
        logger.info(f"Generated visual prompts for all {total_chunks} chunks")
        return episode

    except Exception as e:
        logger.error(f"Failed to generate visual prompts for {episode.episode_id}: {e}")
        episode.error_message = str(e)
        episode.status = EpisodeStatus.FAILED
        raise


def export_visual_prompts_csv(episode: Episode, output_path: str) -> None:
    """
    Export all visual prompts to CSV for review.
    Useful for manual inspection before spending money on image generation.
    """
    import csv
    
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    
    with open(output_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow([
            "Fact ID",
            "Era Label",
            "Year Range",
            "Chunk ID",
            "Narration Text",
            "Visual Prompt"
        ])
        
        for fact in episode.facts:
            for chunk in fact.chunks:
                writer.writerow([
                    fact.fact_id,
                    fact.era_label,
                    fact.year_range,
                    chunk.chunk_id,
                    chunk.narration_text[:100],  # Truncate for readability
                    chunk.visual_prompt,
                ])
    
    logger.info(f"Visual prompts exported to {output_path}")


if __name__ == "__main__":
    import sys
    
    logging.basicConfig(level=logging.INFO)

    if len(sys.argv) < 2:
        print("Usage: python 04_generate_visual_prompts.py <episode_json_path>")
        sys.exit(1)

    episode_path = sys.argv[1]
    
    # Load episode
    with open(episode_path, 'r') as f:
        episode_data = json.load(f)
    episode = Episode(**episode_data)

    # Initialize clients
    llm_client = LLMClient(
        model="claude-3-5-sonnet-20241022",
        cache_dir=".cache/llm"
    )
    style_guide = load_style_guide()

    # Generate visual prompts
    episode = generate_visual_prompts(episode, llm_client, style_guide)

    # Save episode
    with open(episode_path, 'w') as f:
        json.dump(episode.model_dump(), f, indent=2, default=str)

    # Export CSV for review
    csv_path = Path(episode_path).parent / "visual_prompts_review.csv"
    export_visual_prompts_csv(episode, str(csv_path))

    print(f"\n✓ Visual prompts generated and saved")
    print(f"✓ Review prompts at: {csv_path}")
