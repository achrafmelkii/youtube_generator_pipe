"""
Stage 1: Long-Form Script Generation
Input: topic + channel concept
Output: episode.full_script + episode.meta (title, thumbnail, intro scene)

This stage generates a full 1500-2200 word documentary script in chronological/thematic order.
"""

import json
import logging
from pathlib import Path
from typing import Optional, Dict, Any

from schema import Episode, EpisodeMeta, EpisodeStatus, ChannelConcept
from llm_client import LLMClient

logger = logging.getLogger(__name__)


def load_channel_concept(config_path: str = "config/channel_concept.json") -> ChannelConcept:
    """Load channel concept from JSON file."""
    with open(config_path, 'r') as f:
        data = json.load(f)
    return ChannelConcept(**data)


def generate_script(
    episode: Episode,
    channel_concept: ChannelConcept,
    llm_client: LLMClient,
) -> Episode:
    """
    Generate a full documentary script for an episode.
    
    Args:
        episode: Episode object (with topic filled in)
        channel_concept: Channel configuration
        llm_client: LLM client for prompting
    
    Returns:
        Updated episode with full_script and meta fields populated
    """
    
    # Build system prompt
    system_prompt = f"""You are an expert documentary screenwriter for animated educational content.
Your style: {', '.join(channel_concept.tone)}
Your channel theme: {channel_concept.theme}
Voice style: {channel_concept.voice_style}

You will generate a full documentary script that is:
- 1500-2200 words long (target ~12 minutes of spoken narration)
- Chronologically or thematically organized
- Engaging, informative, and entertaining
- Suitable for animated vector-art visualization
- Free of jargon; accessible to a general audience
"""

    # Build user prompt
    user_prompt = f"""Generate a complete documentary script about {episode.topic}.

DELIVERABLES (output as JSON):
{{
  "title": "SEO-optimized video title",
  "thumbnail_concept": "Description of thumbnail visual",
  "intro_scene": "15-30 second hook/opening scene description",
  "script_body": "Full script broken into ERA sections, clearly labeled like:\\n\\n=== ERA 1: [Era Name] ===\\n[narration text]\\n\\n=== ERA 2: [Era Name] ===\\n[narration text]\\n\\netc."
}}

GUIDELINES:
- Structure chronologically through major eras/phases of {episode.topic}
- Each ERA should be 2-4 paragraphs
- Use short, punchy sentences (8-15 words per sentence for pacing)
- Include specific facts, dates, and achievements
- End with a reflection on current/future relevance
- Make it compelling enough for casual YouTube viewers
"""

    logger.info(f"Generating script for episode: {episode.episode_id}")

    try:
        response = llm_client.prompt_structured(
            user_prompt=user_prompt,
            system_prompt=system_prompt,
            use_cache=True,
        )

        # Parse response
        episode.meta = EpisodeMeta(
            title=response.get("title", episode.topic),
            thumbnail_concept=response.get("thumbnail_concept", ""),
            intro_scene=response.get("intro_scene", ""),
        )
        episode.full_script = response.get("script_body", "")
        episode.status = EpisodeStatus.SCRIPT_GENERATED

        logger.info(f"Script generated successfully for {episode.episode_id}")
        return episode

    except Exception as e:
        logger.error(f"Failed to generate script for {episode.episode_id}: {e}")
        episode.error_message = str(e)
        episode.status = EpisodeStatus.FAILED
        raise


def save_episode_json(episode: Episode, output_path: str) -> None:
    """Save episode to JSON file."""
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, 'w') as f:
        json.dump(episode.model_dump(), f, indent=2, default=str)
    logger.info(f"Episode saved to {output_path}")


def save_script_markdown(episode: Episode, output_path: str) -> None:
    """Save just the script as human-readable markdown."""
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, 'w') as f:
        f.write(f"# {episode.meta.title}\n\n")
        f.write(f"**Topic:** {episode.topic}\n")
        f.write(f"**Series:** {episode.series_name}\n\n")
        f.write(f"## Thumbnail Concept\n{episode.meta.thumbnail_concept}\n\n")
        f.write(f"## Intro Scene\n{episode.meta.intro_scene}\n\n")
        f.write(f"## Full Script\n{episode.full_script}\n")
    logger.info(f"Script markdown saved to {output_path}")


if __name__ == "__main__":
    # Example usage
    import sys
    from pathlib import Path

    logging.basicConfig(level=logging.INFO)

    # Initialize clients
    channel_concept = load_channel_concept()
    llm_client = LLMClient(
        model="claude-3-5-sonnet-20241022",
        cache_dir=".cache/llm"
    )

    # Create episode
    episode = Episode(
        episode_id="toyota",
        series_name="cars",
        topic="Toyota",
        meta=EpisodeMeta(title="", thumbnail_concept="", intro_scene="")
    )

    # Generate script
    episode = generate_script(episode, channel_concept, llm_client)

    # Save outputs
    episode_path = "series/cars/episodes/toyota/episode.json"
    script_path = "series/cars/episodes/toyota/script.md"

    save_episode_json(episode, episode_path)
    save_script_markdown(episode, script_path)

    print(f"\n✓ Episode JSON saved to {episode_path}")
    print(f"✓ Script markdown saved to {script_path}")
