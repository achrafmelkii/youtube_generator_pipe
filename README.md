# AI-Powered Animated Documentary Video Generator

A modular, production-ready Python pipeline that transforms a topic into a complete animated YouTube episode: script → visual prompts → images → voiceover → final video.

**Key Features:**
- 📝 AI-generated long-form documentary scripts (10-15 minutes)
- 🎬 Automatic decomposition into facts, chunks, and visual beats
- 🎨 Consistent visual style via locked style keywords (flat-vector animation)
- 🔊 Multi-provider TTS (ElevenLabs, Azure, OpenAI, local Coqui)
- 🖼️ Multi-provider image generation (DALL-E, Flux, local Stable Diffusion)
- 🎥 ffmpeg-based video assembly with Ken Burns effects
- 💾 Full caching & resumable pipeline (no re-generating expensive stages)
- 🔧 Human-in-the-loop checkpoints (review script/visuals before spending money)

---

## Project Structure

```
d:\Videos_generator/
├── config/
│   ├── channel_concept.json      # Reusable channel identity
│   └── style_guide.json           # Locked visual keywords
├── series/
│   └── cars/
│       ├── series_concept.json
│       └── episodes/
│           └── toyota/
│               ├── episode.json       # Full pipeline state
│               ├── script.md          # Human-readable script
│               └── assets/
│                   ├── images/        # Generated images
│                   ├── audio/         # TTS audio chunks
│                   └── final_video.mp4
├── src/
│   ├── schema.py                  # Pydantic data models
│   ├── llm_client.py              # LLM wrapper + caching
│   ├── main.py                    # CLI orchestrator
│   └── pipeline/
│       ├── 01_generate_script.py  # Stage 1: Full script
│       ├── 02_decompose_facts.py  # Stage 2: Eras/facts
│       ├── 03_decompose_chunks.py # Stage 3: Visual beats
│       ├── 04_generate_visual_prompts.py  # Stage 4: Image prompts
│       ├── 05_generate_images.py  # Stage 5: Images
│       ├── 06_generate_tts.py     # Stage 6: Voiceover
│       └── 07_assemble_video.py   # Stage 7: Final video
├── .cache/                        # LLM/image/audio cache
├── requirements.txt
└── README.md (this file)
```

---

## Installation

### 1. Clone / Setup

```bash
cd d:\Videos_generator
```

### 2. Install Python Dependencies

```bash
pip install -r requirements.txt
```

### 3. Install ffmpeg (Required for video assembly)

**Windows (using Chocolatey):**
```bash
choco install ffmpeg
```

**macOS (using Homebrew):**
```bash
brew install ffmpeg
```

**Linux (Ubuntu/Debian):**
```bash
sudo apt install ffmpeg
```

### 4. Set API Keys

Create a `.env` file in the project root or set environment variables:

```bash
# For Claude/LLM generation
export ANTHROPIC_API_KEY=your_anthropic_key

# For image generation
export OPENAI_API_KEY=your_openai_key        # For DALL-E

# For TTS
export ELEVENLABS_API_KEY=your_elevenlabs_key
```

---

## Quick Start

### 1. Create a New Episode

```bash
python src/main.py new-episode --series cars --topic Toyota
```

This scaffolds `series/cars/episodes/toyota/episode.json`.

### 2. Run the Complete Pipeline

```bash
python src/main.py run-all --series cars --episode toyota
```

This runs all stages (script → facts → chunks → visual prompts).

**Or run individual stages:**

```bash
# Stage 1: Generate script
python src/main.py run-stage --series cars --episode toyota --stage script

# Stage 2: Decompose into facts (eras)
python src/main.py run-stage --series cars --episode toyota --stage facts

# Stage 3: Decompose into chunks (visual beats)
python src/main.py run-stage --series cars --episode toyota --stage chunks

# Stage 4: Generate visual prompts (image generation ready)
python src/main.py run-stage --series cars --episode toyota --stage visual_prompts
```

### 3. Review Outputs (Before Spending Money)

After Stage 4, review the generated visual prompts:

```bash
# Check the CSV review file
cat series/cars/episodes/toyota/visual_prompts_review.csv
```

Edit the episode JSON directly if you want to adjust prompts before image generation.

### 4. Generate Images & Audio

Once you're happy with the prompts and script, proceed with expensive stages:

```bash
# Stage 5: Generate images (uses DALL-E, Flux, or local SD)
python src/pipeline/05_generate_images.py series/cars/episodes/toyota/episode.json --provider openai

# Stage 6: Generate voiceover (uses ElevenLabs, Azure, OpenAI, or Coqui)
python src/pipeline/06_generate_tts.py series/cars/episodes/toyota/episode.json --provider elevenlabs

# Stage 7: Assemble final video
python src/pipeline/07_assemble_video.py series/cars/episodes/toyota/episode.json
```

### 5. Final Video

Your assembled video is at:
```
series/cars/episodes/toyota/toyota_final.mp4
```

---

## Pipeline Stages Explained

### Stage 1: Generate Script
**Input:** Topic (e.g., "Toyota")
**Output:** Full 1500-2200 word documentary script + title/thumbnail/intro scene

Uses Claude to generate a narrative structured into ERA sections.

**Human checkpoint:** Review `script.md` for accuracy and pacing before proceeding.

### Stage 2: Decompose Facts
**Input:** Full script with ERA sections
**Output:** Structured `Fact[]` objects (chronological/thematic eras)

Parses ERA headers from the script.

### Stage 3: Decompose Chunks
**Input:** Each Fact's narration text
**Output:** Small visual beats (Chunks, ~5-15 seconds each)

Each chunk maps 1:1 to one generated image.

### Stage 4: Visual Prompts
**Input:** Chunks + style guide
**Output:** Image generation prompts with locked style keywords

Injects consistent visual style into every prompt for coherence.

**Human checkpoint:** Review `visual_prompts_review.csv`. Edit prompts if needed before image generation.

### Stage 5: Generate Images
**Input:** Visual prompts
**Output:** PNG images (one per chunk)

Calls your chosen image API (DALL-E, Flux, local SD). Expensive!

**Note:** Caching prevents re-generation of identical prompts.

### Stage 6: Generate TTS
**Input:** Narration text per chunk
**Output:** MP3 audio + actual duration per chunk

The actual TTS duration becomes ground truth for how long each image displays.

### Stage 7: Assemble Video
**Input:** Images + audio files
**Output:** Final MP4 with Ken Burns zoom effects

Uses ffmpeg to:
- Apply subtle Ken Burns zoom to each image
- Sync with TTS duration
- Concatenate all chunks
- Mux video + audio

---

## Configuration

### `config/channel_concept.json`
Defines the channel's identity (tone, theme, visual style). This is injected into every LLM prompt for consistency.

```json
{
  "channel_name": "Iconic Entities Explained",
  "theme": "Breaking down...",
  "tone": ["informative", "direct", "entertaining"],
  "visual_style": {
    "character_design": "Simple vector-art avatars...",
    "render_style": "flat-vector"
  },
  "voice_style": "Energetic narrator..."
}
```

### `config/style_guide.json`
Locked visual constants. **Same keywords injected into every image prompt** → visual consistency.

```json
{
  "locked_keywords": [
    "flat-vector art style",
    "minimalist design",
    "bright vibrant colors",
    ...
  ],
  "color_hex_codes": { ... },
  "font_name": "Inter Bold",
  "animation_style": "Ken Burns zoom..."
}
```

### `series/cars/series_concept.json`
Defines a series and its episodes.

```json
{
  "series_name": "Car Companies",
  "episodes": [
    { "topic": "Toyota", "title_idea": "Every Toyota Era Explained..." },
    { "topic": "Ford", "title_idea": "How Ford Changed Cars..." }
  ]
}
```

---

## Caching & Cost Control

All expensive operations (LLM, image generation, TTS) are cached locally:

- **LLM cache:** `.cache/llm/` — Claude responses hashed by prompt
- **Image cache:** `.cache/images/` — Images hashed by prompt
- **Audio cache:** `.cache/audio/` — Audio hashed by text

**Result:** Running the same episode twice costs ~90% less on the second run!

### Force Regeneration

To force regeneration (skip cache), modify the code:
```python
response = llm_client.prompt(..., use_cache=False)
```

---

## Image Generation Providers

### DALL-E 3 (OpenAI)
```bash
python src/pipeline/05_generate_images.py episode.json --provider openai
```

**Pros:** High quality, consistent style
**Cons:** $0.04–0.10 per image

### Flux (via Anthropic)
```bash
python src/pipeline/05_generate_images.py episode.json --provider flux
```

**Pros:** Very high quality, fast
**Cons:** Requires Anthropic API credits

### Local Stable Diffusion
Requires running local SD server (e.g., via ComfyUI or WebUI):
```bash
python src/pipeline/05_generate_images.py episode.json --provider local_sd
```

**Pros:** Free (after initial setup), offline, unlimited
**Cons:** Requires GPU, setup complexity

---

## TTS Providers

### ElevenLabs
```bash
python src/pipeline/06_generate_tts.py episode.json --provider elevenlabs
```
**Pros:** Natural voice quality, multiple voices
**Cons:** ~$0.30 per 1000 characters

### Azure Cognitive Services
```bash
python src/pipeline/06_generate_tts.py episode.json --provider azure
```
**Pros:** Competitive pricing
**Cons:** Requires Azure setup

### OpenAI TTS
```bash
python src/pipeline/06_generate_tts.py episode.json --provider openai
```
**Pros:** Fast, simple
**Cons:** Basic voice quality

### Coqui (Local)
```bash
python src/pipeline/06_generate_tts.py episode.json --provider coqui
```
**Pros:** Free, offline, local
**Cons:** Requires GPU, setup

---

## Adding a New Series

1. Create a new series directory:
   ```bash
   mkdir -p series/my_series
   ```

2. Create `series/my_series/series_concept.json`:
   ```json
   {
     "series_name": "My Series",
     "episodes": [
       { "topic": "Topic 1", "title_idea": "Title 1" },
       { "topic": "Topic 2", "title_idea": "Title 2" }
     ]
   }
   ```

3. Run:
   ```bash
   python src/main.py new-episode --series my_series --topic "Topic 1"
   python src/main.py run-all --series my_series --episode topic_1
   ```

**No code changes needed!** Configuration and data only.

---

## Troubleshooting

### ffmpeg not found
Install ffmpeg:
- Windows: `choco install ffmpeg`
- macOS: `brew install ffmpeg`
- Linux: `apt install ffmpeg`

### API key errors
Make sure environment variables are set:
```bash
export ANTHROPIC_API_KEY=sk-ant-...
export OPENAI_API_KEY=sk-...
```

### "No ERA sections found"
The script generation didn't produce ERA headers. Check:
- `series/cars/episodes/toyota/script.md` content
- Adjust the prompt in `01_generate_script.py`

### Audio duration is wrong
Install pydub:
```bash
pip install pydub
```

### Video assembly fails
- Ensure ffmpeg is installed and on PATH
- Check that all images and audio files exist
- Verify paths in `episode.json`

---

## Example: Complete Toyota Episode

```bash
# 1. Create episode
python src/main.py new-episode --series cars --topic Toyota

# 2. Run pipeline (stages 1-4, text-only, cheap)
python src/main.py run-all --series cars --episode toyota

# 3. Review outputs
cat series/cars/episodes/toyota/script.md
cat series/cars/episodes/toyota/visual_prompts_review.csv

# 4. (Optional) Edit visual prompts if needed
vim series/cars/episodes/toyota/episode.json

# 5. Generate images (costs ~$2-5 for 30-40 images)
python src/pipeline/05_generate_images.py series/cars/episodes/toyota/episode.json --provider openai

# 6. Generate voiceover (costs ~$1-2 for 12 min audio)
python src/pipeline/06_generate_tts.py series/cars/episodes/toyota/episode.json --provider elevenlabs

# 7. Assemble video
python src/pipeline/07_assemble_video.py series/cars/episodes/toyota/episode.json

# 8. Done!
echo series/cars/episodes/toyota/toyota_final.mp4
```

**Total cost:** ~$3–7 per 12-minute episode (mostly images + TTS)
**Total time:** ~5 minutes (mostly API calls, cached on reruns)

---

## Advanced Features (Future)

- [ ] Parallel batch generation (multiple episodes at once)
- [ ] Subtitle generation and burn-in
- [ ] Background music bed (ducked under narration)
- [ ] Era-label lower-third text overlays
- [ ] Custom thumbnail generation
- [ ] Video quality profiles (720p, 1080p, 4K)
- [ ] Platform-specific outputs (YouTube, TikTok, Instagram)

---

## Environment Variables Reference

```bash
# LLM
ANTHROPIC_API_KEY          # Claude API
OPENAI_API_KEY             # OpenAI (DALL-E, TTS)

# TTS
ELEVENLABS_API_KEY         # ElevenLabs
AZURE_SPEECH_KEY           # Azure Cognitive Services
AZURE_REGION               # Azure region (default: eastus)

# Local Services
SD_SERVER_URL              # Local SD server URL (default: http://localhost:7860)
```

---

## License

This project is provided as-is for educational and commercial use.

---

## Support & Contributions

For issues, questions, or contributions, check:
- `series/*/episodes/*/episode.json` — Full pipeline state
- `.cache/llm/` — Prompt hashes and responses
- Stage scripts themselves — Well-commented for extension

Happy generating! 🎬
