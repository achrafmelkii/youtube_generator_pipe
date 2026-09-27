"""
Main orchestrator for the documentary video generator pipeline.
Provides CLI interface for running individual stages or complete pipeline.

Usage:
  python main.py new-episode --series cars --topic Toyota
  python main.py run-stage --episode toyota --stage script
  python main.py run-stage --episode toyota --stage facts
  python main.py run-stage --episode toyota --stage chunks
  python main.py run-stage --episode toyota --stage visual_prompts
  python main.py run-all --episode toyota --series cars
"""

import argparse
import json
import logging
import sys
from pathlib import Path
from typing import Optional

import sys
sys.path.insert(0, str(Path(__file__).parent))

from schema import (
    Episode, EpisodeMeta, SeriesConcept, ChannelConcept, EpisodeStatus
)
from llm_client import LLMClient
from pipeline.01_generate_script import (
    generate_script, load_channel_concept as load_channel_for_script,
    save_episode_json, save_script_markdown
)
from pipeline.02_decompose_facts import decompose_facts
from pipeline.03_decompose_chunks import decompose_all_chunks
from pipeline.04_generate_visual_prompts import (
    generate_visual_prompts, load_style_guide, export_visual_prompts_csv
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def get_episode_path(series: str, episode_id: str) -> Path:
    """Get the path to an episode's JSON file."""
    return Path(f"series/{series}/episodes/{episode_id}/episode.json")


def load_episode(series: str, episode_id: str) -> Episode:
    """Load episode from disk."""
    episode_path = get_episode_path(series, episode_id)
    if not episode_path.exists():
        raise FileNotFoundError(f"Episode not found: {episode_path}")
    
    with open(episode_path, 'r') as f:
        data = json.load(f)
    return Episode(**data)


def save_episode(episode: Episode, series: str) -> None:
    """Save episode to disk."""
    episode_path = get_episode_path(series, episode.episode_id)
    save_episode_json(episode, str(episode_path))


def cmd_new_episode(args) -> None:
    """Create a new episode scaffold."""
    series = args.series
    topic = args.topic
    
    # Load series concept to get title idea
    series_concept_path = Path(f"series/{series}/series_concept.json")
    if not series_concept_path.exists():
        logger.error(f"Series concept not found: {series_concept_path}")
        sys.exit(1)
    
    with open(series_concept_path, 'r') as f:
        series_data = json.load(f)
    series_concept = SeriesConcept(**series_data)
    
    # Find episode title idea
    title_idea = topic
    for ep in series_concept.episodes:
        if ep.get("topic") == topic:
            title_idea = ep.get("title_idea", topic)
            break
    
    # Create episode
    episode_id = topic.lower().replace(" ", "_")
    episode = Episode(
        episode_id=episode_id,
        series_name=series,
        topic=topic,
        meta=EpisodeMeta(
            title=title_idea,
            thumbnail_concept="",
            intro_scene=""
        )
    )
    
    # Save scaffold
    save_episode(episode, series)
    
    episode_path = get_episode_path(series, episode_id)
    logger.info(f"✓ Created episode scaffold: {episode_path}")
    logger.info(f"  Topic: {topic}")
    logger.info(f"  Series: {series}")
    print(f"\n✓ Episode created: {episode_id}")
    print(f"  Next: python main.py run-stage --episode {episode_id} --series {series} --stage script")


def cmd_run_stage(args) -> None:
    """Run a specific pipeline stage."""
    series = args.series
    episode_id = args.episode
    stage = args.stage
    
    logger.info(f"Running stage '{stage}' for episode '{episode_id}'")
    
    # Load episode
    episode = load_episode(series, episode_id)
    
    # Initialize clients
    llm_client = LLMClient(
        model="claude-3-5-sonnet-20241022",
        cache_dir=".cache/llm"
    )
    channel_concept = ChannelConcept.model_validate_json(
        Path("config/channel_concept.json").read_text()
    )
    
    # Run stage
    if stage == "script":
        logger.info("Generating script...")
        episode = generate_script(episode, channel_concept, llm_client)
        save_episode(episode, series)
        
        # Also save human-readable script
        script_path = get_episode_path(series, episode_id).parent / "script.md"
        save_script_markdown(episode, str(script_path))
        print(f"\n✓ Script generated")
        print(f"  Script: {script_path}")
        
    elif stage == "facts":
        logger.info("Decomposing into facts...")
        episode = decompose_facts(episode)
        save_episode(episode, series)
        print(f"\n✓ Decomposed into {len(episode.facts)} facts")
        
    elif stage == "chunks":
        logger.info("Decomposing into chunks...")
        episode = decompose_all_chunks(episode, llm_client)
        save_episode(episode, series)
        total_chunks = sum(len(f.chunks) for f in episode.facts)
        print(f"\n✓ Decomposed into {total_chunks} chunks")
        
    elif stage == "visual_prompts":
        logger.info("Generating visual prompts...")
        style_guide = json.loads(Path("config/style_guide.json").read_text())
        episode = generate_visual_prompts(episode, llm_client, style_guide)
        save_episode(episode, series)
        
        # Export CSV for review
        csv_path = get_episode_path(series, episode_id).parent / "visual_prompts_review.csv"
        export_visual_prompts_csv(episode, str(csv_path))
        print(f"\n✓ Visual prompts generated")
        print(f"  Review: {csv_path}")
        
    else:
        logger.error(f"Unknown stage: {stage}")
        print(f"\nAvailable stages: script, facts, chunks, visual_prompts")
        sys.exit(1)
    
    logger.info(f"Stage '{stage}' completed with status: {episode.status}")


def cmd_run_all(args) -> None:
    """Run the complete pipeline."""
    series = args.series
    episode_id = args.episode
    
    logger.info(f"Running complete pipeline for {episode_id} ({series})")
    
    stages = [
        ("script", "Generating script"),
        ("facts", "Decomposing into facts"),
        ("chunks", "Decomposing into chunks"),
        ("visual_prompts", "Generating visual prompts"),
    ]
    
    for stage, description in stages:
        logger.info(f"\n--- {description} ---")
        args_for_stage = argparse.Namespace(
            series=series,
            episode=episode_id,
            stage=stage
        )
        try:
            cmd_run_stage(args_for_stage)
        except Exception as e:
            logger.error(f"Pipeline failed at stage '{stage}': {e}")
            sys.exit(1)
    
    print(f"\n✓ Pipeline complete!")
    print(f"  Episode: {episode_id}")
    print(f"  Series: {series}")


def cmd_status(args) -> None:
    """Show status of an episode."""
    series = args.series
    episode_id = args.episode
    
    episode = load_episode(series, episode_id)
    
    print(f"\n=== Episode Status ===")
    print(f"ID: {episode.episode_id}")
    print(f"Topic: {episode.topic}")
    print(f"Series: {episode.series_name}")
    print(f"Status: {episode.status}")
    print(f"Updated: {episode.updated_at}")
    
    if episode.full_script:
        print(f"\n✓ Script: Generated ({len(episode.full_script)} chars)")
    else:
        print(f"\n✗ Script: Not generated")
    
    if episode.facts:
        total_chunks = sum(len(f.chunks) for f in episode.facts)
        print(f"✓ Facts: {len(episode.facts)} facts, {total_chunks} chunks")
        for fact in episode.facts:
            status_str = "✓" if fact.chunks else "✗"
            print(f"  {status_str} {fact.era_label}: {len(fact.chunks)} chunks")
    else:
        print(f"✗ Facts: Not decomposed")
    
    if episode.error_message:
        print(f"\n⚠ Error: {episode.error_message}")


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="AI-Powered Animated Documentary Video Generator",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python main.py new-episode --series cars --topic Toyota
  python main.py run-stage --episode toyota --series cars --stage script
  python main.py run-all --episode toyota --series cars
  python main.py status --episode toyota --series cars
        """
    )
    
    subparsers = parser.add_subparsers(dest="command", help="Command to run")
    
    # new-episode command
    new_ep = subparsers.add_parser("new-episode", help="Create new episode scaffold")
    new_ep.add_argument("--series", required=True, help="Series name")
    new_ep.add_argument("--topic", required=True, help="Episode topic")
    new_ep.set_defaults(func=cmd_new_episode)
    
    # run-stage command
    run_stage = subparsers.add_parser("run-stage", help="Run specific pipeline stage")
    run_stage.add_argument("--episode", required=True, help="Episode ID")
    run_stage.add_argument("--series", required=True, help="Series name")
    run_stage.add_argument(
        "--stage",
        required=True,
        choices=["script", "facts", "chunks", "visual_prompts"],
        help="Stage to run"
    )
    run_stage.set_defaults(func=cmd_run_stage)
    
    # run-all command
    run_all = subparsers.add_parser("run-all", help="Run complete pipeline")
    run_all.add_argument("--episode", required=True, help="Episode ID")
    run_all.add_argument("--series", required=True, help="Series name")
    run_all.set_defaults(func=cmd_run_all)
    
    # status command
    status = subparsers.add_parser("status", help="Show episode status")
    status.add_argument("--episode", required=True, help="Episode ID")
    status.add_argument("--series", required=True, help="Series name")
    status.set_defaults(func=cmd_status)
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        sys.exit(1)
    
    try:
        args.func(args)
    except Exception as e:
        logger.error(f"Error: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
