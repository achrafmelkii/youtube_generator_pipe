"""
Core data models for the documentary video generator pipeline.
All structures are designed to be persisted as JSON for resumable, cacheable pipeline stages.
"""

from typing import List, Optional, Dict, Any
from enum import Enum
from pydantic import BaseModel, Field
from datetime import datetime


class ChunkStatus(str, Enum):
    """Status of a chunk through the pipeline."""
    PENDING = "pending"
    GENERATED = "generated"
    APPROVED = "approved"
    FAILED = "failed"


class FactStatus(str, Enum):
    """Status of a fact through the pipeline."""
    PENDING = "pending"
    DECOMPOSED = "decomposed"
    APPROVED = "approved"
    FAILED = "failed"


class EpisodeStatus(str, Enum):
    """Status of an episode through the pipeline."""
    INITIAL = "initial"
    SCRIPT_GENERATED = "script_generated"
    FACTS_DECOMPOSED = "facts_decomposed"
    CHUNKS_DECOMPOSED = "chunks_decomposed"
    VISUAL_PROMPTS_GENERATED = "visual_prompts_generated"
    IMAGES_GENERATED = "images_generated"
    TTS_GENERATED = "tts_generated"
    ASSEMBLED = "assembled"
    FAILED = "failed"


class VisualStyle(BaseModel):
    """Visual style configuration for the channel."""
    character_design: str = Field(
        description="Character design description (e.g., vector avatars, realistic, cartoon)"
    )
    scene_setup: str = Field(
        description="How scenes are composed (e.g., badge-based eras, timeline layout)"
    )
    color_palette: str = Field(
        description="Color palette description (e.g., vibrant, distinct per era)"
    )
    render_style: str = Field(
        description="Render style (cartoon, semi-realistic, flat-vector, etc.)"
    )


class ChannelConcept(BaseModel):
    """Reusable channel identity — injected into every prompt for consistency."""
    channel_name: str
    theme: str
    tone: List[str] = Field(description="Tone descriptors: informative, entertaining, etc.")
    visual_style: VisualStyle
    voice_style: str = Field(description="Voice and pacing descriptor for TTS")
    
    class Config:
        json_schema_extra = {
            "example": {
                "channel_name": "Iconic Entities",
                "theme": "Breaking down iconic real-world entities into animated guides",
                "tone": ["informative", "direct", "entertaining", "fast-paced"],
                "visual_style": {
                    "character_design": "Simple vector-art avatars in colored circles",
                    "scene_setup": "Badge-based eras with avatar changes",
                    "color_palette": "Vibrant, distinct per circle",
                    "render_style": "flat-vector"
                },
                "voice_style": "Energetic narrator, documentary pacing"
            }
        }


class StyleGuide(BaseModel):
    """Locked visual constants for consistency across all images in the series."""
    locked_keywords: List[str] = Field(
        description="Style keywords always injected into image prompts"
    )
    color_hex_codes: Dict[str, str] = Field(
        description="Color palette hex codes mapped to eras/themes"
    )
    font_name: str = Field(description="Primary font for text overlays")
    badge_aspect_ratio: str = Field(default="1:1", description="Width:height of era badges")
    animation_style: str = Field(description="Ken Burns effect parameters or similar")


class AssetPaths(BaseModel):
    """Asset file paths for a chunk."""
    image: Optional[str] = Field(default=None, description="Path to generated image")
    video_clip: Optional[str] = Field(default=None, description="Path to video clip (if applicable)")
    audio: Optional[str] = Field(default=None, description="Path to TTS audio file")
    subtitle: Optional[str] = Field(default=None, description="Path to subtitle file")


class Chunk(BaseModel):
    """A single narration beat (~5-15 seconds) paired with one visual."""
    chunk_id: str = Field(description="Unique chunk identifier within the episode")
    narration_text: str = Field(description="Exact voiceover text for this chunk")
    visual_prompt: Optional[str] = Field(
        default=None, description="Image generation prompt (injected with style guide)"
    )
    style_tags: List[str] = Field(
        default_factory=list, description="Inherited + chunk-specific style keywords"
    )
    duration_estimate_sec: float = Field(
        default=0.0, description="Estimated duration from TTS output"
    )
    asset_paths: AssetPaths = Field(default_factory=AssetPaths)
    status: ChunkStatus = Field(default=ChunkStatus.PENDING)
    error_message: Optional[str] = Field(default=None)


class Fact(BaseModel):
    """A major chronological/thematic section (era) of the episode."""
    fact_id: str = Field(description="Unique fact identifier within the episode")
    era_label: str = Field(description="Name of this era (e.g., 'Founding Era', 'Golden Age')")
    year_range: str = Field(description="Historical span (e.g., '1950-1970')")
    summary: str = Field(description="One-paragraph summary of this era's significance")
    narration_text: str = Field(
        description="Full narration text belonging to this fact (from the script)"
    )
    chunks: List[Chunk] = Field(default_factory=list, description="Sub-beats within this fact")
    status: FactStatus = Field(default=FactStatus.PENDING)
    error_message: Optional[str] = Field(default=None)


class EpisodeMeta(BaseModel):
    """Metadata for the episode."""
    title: str = Field(description="SEO-optimized video title")
    thumbnail_concept: str = Field(description="Concept for the thumbnail image")
    intro_scene: str = Field(description="Description of the opening 15-30 sec hook")


class Episode(BaseModel):
    """A single episode — one topic fully decomposed through the pipeline."""
    episode_id: str = Field(description="URL-slug for the episode (e.g., 'toyota')")
    series_name: str = Field(description="Parent series (e.g., 'cars')")
    topic: str = Field(description="Main topic (e.g., 'Toyota')")
    meta: EpisodeMeta = Field(description="Title, thumbnail, intro scene concepts")
    
    # Full script from Stage 1
    full_script: Optional[str] = Field(
        default=None, description="Full documentary script (10-15 min spoken)"
    )
    
    # Pipeline decomposition
    facts: List[Fact] = Field(default_factory=list, description="Chronological/thematic sections")
    
    # Status and metadata
    status: EpisodeStatus = Field(default=EpisodeStatus.INITIAL)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    # Asset outputs
    final_video_path: Optional[str] = Field(default=None)
    error_message: Optional[str] = Field(default=None)


class SeriesConcept(BaseModel):
    """A series concept — groups multiple episodes under a theme."""
    series_name: str = Field(description="Name of the series (e.g., 'Car Companies')")
    series_description: str = Field(description="Overview of the series theme and scope")
    episodes: List[Dict[str, str]] = Field(
        description="List of episodes: {topic, title_idea}"
    )
    
    class Config:
        json_schema_extra = {
            "example": {
                "series_name": "Car Companies",
                "series_description": "Evolution of iconic automotive manufacturers",
                "episodes": [
                    {"topic": "Toyota", "title_idea": "Every Toyota Era Explained in 12 Minutes"},
                    {"topic": "Ford", "title_idea": "How Ford Changed Cars Forever"}
                ]
            }
        }
