# Development Guide

## Extending the Pipeline

This guide explains how to extend the system with new features.

---

## Adding a Custom LLM Provider

Want to use GPT-4, Claude Opus, or another model?

Edit `src/llm_client.py`:

```python
def _call_custom_provider(self, user_prompt, system_prompt, json_mode):
    """Add your custom provider logic here."""
    response = my_provider_api.call(
        messages=[...],
        model=self.model,
        ...
    )
    return response.text
```

Then in the `prompt()` method:
```python
if self.provider == "custom":
    return self._call_custom_provider(...)
```

---

## Adding a New Image Generation Stage

Example: Generate animation keyframes instead of static images.

1. Create `src/pipeline/05b_generate_animation_keyframes.py`
2. Follow the same pattern as `05_generate_images.py`
3. Import and call from `src/main.py`

---

## Custom Video Assembly Effects

The Ken Burns effect is in `src/pipeline/07_assemble_video.py`.

To add new effects (e.g., parallax, 3D tilt):

```python
def apply_parallax_effect(self, image_path, depth_map_path, duration):
    """Add parallax effect based on depth map."""
    cmd = [
        self.ffmpeg_path,
        "-i", str(image_path),
        "-i", str(depth_map_path),
        "-filter_complex", "..."  # Your parallax filter
        ...
    ]
```

---

## Adding Subtitles

Extend `src/pipeline/07_assemble_video.py`:

```python
def add_subtitles(self, video_path, subtitle_path, output_path):
    """Burn subtitles into video."""
    cmd = [
        self.ffmpeg_path,
        "-i", str(video_path),
        "-vf", f"subtitles={subtitle_path}",
        str(output_path)
    ]
```

Generate subtitle VTT files in Stage 3:
```python
def generate_subtitles(episode):
    for fact in episode.facts:
        for chunk in fact.chunks:
            vtt = f"00:00:00,000 --> 00:00:{chunk.duration_estimate_sec},000\n{chunk.narration_text}\n"
```

---

## Adding Background Music

Extend `src/pipeline/07_assemble_video.py`:

```python
def add_background_music(self, video_path, music_path, output_path, music_volume=-15):
    """Add background music, ducked under narration."""
    cmd = [
        self.ffmpeg_path,
        "-i", str(video_path),
        "-i", str(music_path),
        "-filter_complex",
        f"[1:a]volume={10**(music_volume/20)}[music];[0:a][music]amix=inputs=2:duration=longest[a]",
        "-map", "0:v",
        "-map", "[a]",
        "-c:v", "copy",
        "-c:a", "aac",
        str(output_path)
    ]
```

---

## Adding Era Labels & Lower-Thirds

Generate text overlays dynamically:

```python
def add_era_labels(self, video_path, facts, output_path):
    """Add era labels as lower-third text."""
    # Create text file for each era timing
    # Use ffmpeg drawtext filter
```

---

## Parallel Batch Processing

Process multiple episodes simultaneously:

```python
from concurrent.futures import ThreadPoolExecutor

def batch_process(series, topics, max_workers=3):
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = [
            executor.submit(process_episode, series, topic)
            for topic in topics
        ]
        for future in futures:
            future.result()
```

---

## Adding Platform-Specific Outputs

Create versions optimized for different platforms:

```python
def export_for_platform(episode, platform="youtube"):
    if platform == "tiktok":
        resolution = "1080x1920"  # Portrait
        duration_limit = 600  # 10 min
    elif platform == "instagram":
        resolution = "1080x1350"  # Square-ish
        duration_limit = 300
    else:  # youtube
        resolution = "1920x1080"  # Landscape
        duration_limit = 3600
    
    # Re-render with platform specs
```

---

## Custom Prompt Engineering

Tweak the LLM prompts for better results:

Edit stage files:
- `01_generate_script.py` → `system_prompt` and `user_prompt`
- `03_decompose_chunks.py` → chunk decomposition logic
- `04_generate_visual_prompts.py` → visual prompt construction

Example: Add shot type hints to visual prompts:

```python
user_prompt = f"""Generate an image prompt for this scene.
...
SHOT TYPE HINT: {chunk.metadata.get('shot_type', 'wide')}
CAMERA MOVEMENT: {chunk.metadata.get('camera_movement', 'static')}
"""
```

---

## Database Integration

Currently everything is JSON on disk. To add a database:

```python
# Add to schema.py imports
from sqlalchemy import create_engine, Column, String, etc
from sqlalchemy.orm import Session

class EpisodeDB(Base):
    __tablename__ = "episodes"
    episode_id = Column(String, primary_key=True)
    series_name = Column(String)
    topic = Column(String)
    status = Column(String)
    data = Column(JSON)  # Full episode JSON

# Update main.py
def save_episode(episode, series):
    # Save to both JSON (for portability) and DB
    db_session.add(episode_to_db(episode))
    db_session.commit()
```

---

## Testing

Add tests to verify each stage:

```python
# tests/test_stages.py
import pytest
from src.schema import Episode, EpisodeMeta

def test_script_generation():
    episode = Episode(...)
    result = generate_script(episode, channel_concept, llm_client)
    assert result.full_script
    assert len(result.full_script) > 1000

def test_fact_decomposition():
    episode = Episode(full_script="=== ERA 1: Test (2000-2010) ===\nTest content")
    result = decompose_facts(episode)
    assert len(result.facts) > 0
```

Run:
```bash
pytest tests/
```

---

## Performance Profiling

Identify bottlenecks:

```python
import cProfile
import pstats

profiler = cProfile.Profile()
profiler.enable()

# Your pipeline code here
episode = run_all(...)

profiler.disable()
stats = pstats.Stats(profiler)
stats.sort_stats('cumulative')
stats.print_stats(10)  # Top 10
```

---

## Logging & Debugging

All stages use Python logging. Set level:

```python
logging.basicConfig(level=logging.DEBUG)  # More verbose
```

Or in code:
```python
logger.setLevel(logging.DEBUG)
```

Add breakpoints:
```python
import pdb
pdb.set_trace()  # Debugger stops here
```

---

## Contributing New Image Providers

Template for adding a new image service:

```python
# src/pipeline/05_generate_images.py

class MyImageProvider(ImageGenerationClient):
    def _generate_my_service(self, prompt, chunk_id, output_dir, prompt_hash):
        """Generate using MyService API."""
        # 1. Call API
        # 2. Download image
        # 3. Save + cache
        # 4. Return path
        pass
```

---

## Version Control

Keep configs and code separate:
- Version control: `src/`, `config/`, `README.md`
- .gitignore: `.cache/`, `series/*/episodes/*/assets/`, `.env`

```bash
git add src/ config/ *.md requirements.txt
git add -u  # Remove deleted files
git commit -m "Add feature X"
```

---

## Documentation Standards

For new stages/features, follow the pattern:

```python
"""
Stage X: Feature Name
Input: description
Output: description

This stage does X, Y, Z.
"""

def my_function(episode, param):
    """
    Brief description.
    
    Args:
        episode: Episode object
        param: Description
    
    Returns:
        Updated episode
    """
```

---

That's it! The system is designed to be extended. Questions? Check the main README or the stage implementations themselves.
