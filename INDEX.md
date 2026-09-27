# Project Index & Quick Navigation

## 📚 Start Here (In Order)

1. **[QUICKSTART.md](QUICKSTART.md)** ← **START HERE** (5 minutes)
   - Installation
   - Your first episode
   - Cost breakdown
   - Pro tips

2. **[README.md](README.md)** ← Full Reference (30 minutes)
   - Feature overview
   - Architecture
   - Configuration guide
   - Provider options
   - Troubleshooting

3. **[PROJECT_SUMMARY.md](PROJECT_SUMMARY.md)** ← Architecture Deep-Dive (20 minutes)
   - What's been built
   - Technical stack
   - Cost model
   - Code statistics
   - Example workflows

4. **[DEVELOPMENT.md](DEVELOPMENT.md)** ← Extension Guide (15 minutes)
   - How to add custom providers
   - New effects (subtitles, music, effects)
   - Parallel processing
   - Testing patterns
   - Database integration

---

## 🎯 By Use Case

### **I just want to generate my first video**
1. Read: QUICKSTART.md
2. Run: `python src/main.py new-episode --series cars --topic Toyota`
3. Follow the 5-minute guide

### **I want to understand the architecture**
1. Read: PROJECT_SUMMARY.md (Architecture section)
2. Browse: `src/schema.py` (data model)
3. Browse: `src/main.py` (orchestration)

### **I want to customize the system**
1. Read: README.md (Configuration section)
2. Edit: `config/channel_concept.json` and `config/style_guide.json`
3. Read: DEVELOPMENT.md (if adding new features)

### **I want to add a new series**
1. Create: `series/my_series/series_concept.json`
2. Run: `python src/main.py new-episode --series my_series --topic "My Topic"`
3. Done! No code changes needed.

### **I want to use different image/TTS providers**
1. Read: README.md (Image Generation Providers section)
2. Run: `python src/pipeline/05_generate_images.py episode.json --provider flux`
3. Or: `python src/pipeline/06_generate_tts.py episode.json --provider coqui`

### **I want to extend with new features**
1. Read: DEVELOPMENT.md (full guide)
2. Example topics: subtitles, background music, 3D effects, batch processing

---

## 📁 File Structure Reference

### Configuration Files (Edit these!)
```
config/
├── channel_concept.json       → Channel tone, theme, visual style
└── style_guide.json           → Locked visual keywords for consistency
```

### Series Definitions (Add these for new series!)
```
series/
├── cars/
│   ├── series_concept.json    → "Car Companies" series + episodes
│   └── episodes/
│       └── toyota/
│           ├── episode.json   → Full pipeline state (auto-generated)
│           ├── script.md      → Human-readable script
│           └── assets/        → Images, audio, final video
├── tech/
│   └── series_concept.json    → "Tech Companies" series (example)
└── history/
    └── series_concept.json    → "Historical Events" series (example)
```

### Source Code (Don't edit unless extending!)
```
src/
├── schema.py                  → Pydantic data models (core)
├── llm_client.py              → LLM wrapper + caching (core)
├── main.py                    → CLI orchestrator (core)
└── pipeline/
    ├── 01_generate_script.py  → Full script generation
    ├── 02_decompose_facts.py  → Split into eras
    ├── 03_decompose_chunks.py → Split into visual beats
    ├── 04_generate_visual_prompts.py → Create image prompts
    ├── 05_generate_images.py  → Generate images
    ├── 06_generate_tts.py     → Generate voiceover
    └── 07_assemble_video.py   → Assemble final video
```

### Documentation (You are here!)
```
├── QUICKSTART.md              → 5-minute setup guide
├── README.md                  → Full reference manual
├── PROJECT_SUMMARY.md         → Architecture & statistics
├── DEVELOPMENT.md             → How to extend
├── INDEX.md                   → This file
├── requirements.txt           → Python dependencies
└── .gitignore                 → Git exclusions
```

---

## 🔧 Common Commands

### Episode Management
```bash
# Create new episode
python src/main.py new-episode --series cars --topic Toyota

# Show episode status
python src/main.py status --series cars --episode toyota

# Run individual stage
python src/main.py run-stage --series cars --episode toyota --stage script
python src/main.py run-stage --series cars --episode toyota --stage facts
python src/main.py run-stage --series cars --episode toyota --stage chunks
python src/main.py run-stage --series cars --episode toyota --stage visual_prompts

# Run all text-only stages (free!)
python src/main.py run-all --series cars --episode toyota
```

### Image Generation
```bash
# Using DALL-E
python src/pipeline/05_generate_images.py series/cars/episodes/toyota/episode.json --provider openai

# Using Flux
python src/pipeline/05_generate_images.py series/cars/episodes/toyota/episode.json --provider flux

# Using local Stable Diffusion
python src/pipeline/05_generate_images.py series/cars/episodes/toyota/episode.json --provider local_sd
```

### TTS Generation
```bash
# Using ElevenLabs
python src/pipeline/06_generate_tts.py series/cars/episodes/toyota/episode.json --provider elevenlabs

# Using OpenAI
python src/pipeline/06_generate_tts.py series/cars/episodes/toyota/episode.json --provider openai

# Using Azure
python src/pipeline/06_generate_tts.py series/cars/episodes/toyota/episode.json --provider azure

# Using local Coqui
python src/pipeline/06_generate_tts.py series/cars/episodes/toyota/episode.json --provider coqui
```

### Video Assembly
```bash
# Assemble final video from images + audio
python src/pipeline/07_assemble_video.py series/cars/episodes/toyota/episode.json
```

---

## 🏗️ System Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                          USER INPUT                             │
│               Topic, Channel, Series, Providers                 │
└────────────────────────┬────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│                      MAIN ORCHESTRATOR                          │
│                   (src/main.py - CLI)                           │
│  ─ new-episode, run-stage, run-all, status                     │
└────────────────────────┬────────────────────────────────────────┘
                         │
        ┌────────────────┼────────────────┐
        │                │                │
        ▼                ▼                ▼
  ┌──────────────┐ ┌────────────┐ ┌─────────────┐
  │ Schema.py    │ │LLMClient.py│ │  Config     │
  │ (data model) │ │ (wrapper)  │ │  (YAML/JSON)│
  └──────────────┘ └────────────┘ └─────────────┘
        │
        ▼
┌─────────────────────────────────────────────────────────────────┐
│                    PIPELINE STAGES (7)                          │
├─────────────────────────────────────────────────────────────────┤
│ [1] Generate Script    → Full 1500-2200 word script            │
│ [2] Decompose Facts    → Split into eras                        │
│ [3] Decompose Chunks   → Split into visual beats (~5-15s each) │
│ [4] Visual Prompts     → Create image generation prompts        │
│ [5] Generate Images    → Call image API                         │
│ [6] Generate TTS       → Call TTS API                           │
│ [7] Assemble Video     → Use ffmpeg                             │
└────────────────────────┬────────────────────────────────────────┘
                         │
        ┌────────────────┼────────────────┐
        │                │                │
        ▼                ▼                ▼
   ┌────────────┐  ┌──────────┐  ┌───────────┐
   │   Cache    │  │  Assets  │  │  Output   │
   │ (LLM/img)  │  │(img/mp3) │  │(MP4 video)│
   └────────────┘  └──────────┘  └───────────┘
```

---

## 🎬 Data Flow Example: Toyota Episode

```
Input: Topic="Toyota"
  │
  ├─→ Stage 1: Script Generation
  │   Input:  "Toyota", channel_concept.json
  │   Output: full_script (1800 words, 4-6 ERA sections)
  │   Cost:   $0.01
  │   Time:   30s
  │
  ├─→ Stage 2: Fact Decomposition
  │   Input:  full_script with "=== ERA X: ..." headers
  │   Output: facts[] = [Fact(era_label="Founding", year_range="1937-1950", ...),
  │                      Fact(era_label="Growth", year_range="1950-1970", ...),
  │                      ...]
  │   Cost:   Free
  │   Time:   5s
  │
  ├─→ Stage 3: Chunk Decomposition
  │   Input:  facts[].narration_text
  │   Output: facts[].chunks[] = [Chunk(narration="Kiichiro Toyoda founded...", ...),
  │                                Chunk(narration="Post-war recovery...", ...),
  │                                ...]
  │           ~40 chunks total
  │   Cost:   $0.05
  │   Time:   10s
  │
  ├─→ Stage 4: Visual Prompts
  │   Input:  chunks[] + style_guide.locked_keywords
  │   Output: chunks[].visual_prompt = "flat-vector art style, minimalist design,
  │                                      1937 Japanese automotive factory,
  │                                      assembly line innovation, ..."
  │   Cost:   $0.10
  │   Time:   20s
  │
  │   📋 HUMAN CHECKPOINT: Review visual_prompts_review.csv
  │
  ├─→ Stage 5: Image Generation (Expensive!)
  │   Input:  chunks[].visual_prompt (40 prompts)
  │   Output: chunks[].asset_paths.image = "assets/images/fact_1_chunk_1.png"
  │   Cost:   $2-5 ($0.04-0.10 per image × 40)
  │   Time:   2-3 min
  │   Cache:  Yes (by prompt hash)
  │
  ├─→ Stage 6: TTS Generation (Expensive!)
  │   Input:  chunks[].narration_text (40 narrations)
  │   Output: chunks[].asset_paths.audio = "assets/audio/fact_1_chunk_1.mp3"
  │           chunks[].duration_estimate_sec = 8.5 (from TTS)
  │   Cost:   $1-2 (~$0.30 per 1000 chars × 1500 words)
  │   Time:   1 min
  │   Cache:  Yes (by text hash)
  │
  ├─→ Stage 7: Video Assembly (Free!)
  │   Input:  Images (PNGs) + Audio (MP3s) + durations
  │   Process:
  │     For each chunk:
  │       1. Apply Ken Burns zoom to image (2% over duration)
  │       2. Trim to exact audio duration
  │     Concatenate all video clips
  │     Mux with concatenated audio
  │     Export MP4
  │   Output: series/cars/episodes/toyota/toyota_final.mp4
  │   Cost:   Free (ffmpeg)
  │   Time:   2 min
  │   Cache:  No (but files cached if re-run)
  │
  └─→ ✨ FINAL: toyota_final.mp4 (12 min, 1080p)
      Total cost: ~$3-8
      Total time: ~7 minutes
      Cached rerun: ~$0.30 cost, ~1 min time
```

---

## 🔑 Key Design Decisions

| Decision | Rationale |
|----------|-----------|
| **JSON persistence** | Portable, version-control friendly, human-readable |
| **Resumable stages** | Each stage reads/writes disk, enabling cherry-picking |
| **Caching by hash** | Cheap re-runs, cost-effective iteration |
| **Multi-provider** | Flexibility, avoid vendor lock-in |
| **CLI-first** | Automation-friendly, scriptable, headless-compatible |
| **Style guide injection** | Ensures visual consistency across 40+ images |
| **Two human checkpoints** | Review before spending money on images/TTS |
| **ffmpeg for assembly** | Industry standard, free, platform-agnostic |
| **Pydantic models** | Type safety, validation, IDE support |

---

## 📊 Dependency Graph

```
main.py
  ├─→ schema.py                    (Data models)
  ├─→ llm_client.py                (LLM wrapper)
  ├─→ 01_generate_script.py
  │   ├─→ schema.py
  │   ├─→ llm_client.py
  │   └─→ config/channel_concept.json
  ├─→ 02_decompose_facts.py
  │   └─→ schema.py
  ├─→ 03_decompose_chunks.py
  │   ├─→ schema.py
  │   └─→ llm_client.py
  ├─→ 04_generate_visual_prompts.py
  │   ├─→ schema.py
  │   ├─→ llm_client.py
  │   └─→ config/style_guide.json
  ├─→ 05_generate_images.py
  │   └─→ schema.py
  ├─→ 06_generate_tts.py
  │   └─→ schema.py
  └─→ 07_assemble_video.py
      └─→ schema.py
```

---

## 🎓 Learning Path

**Complete Beginner:**
1. QUICKSTART.md (run first episode)
2. README.md (understand features)
3. Look at `series/cars/episodes/toyota/episode.json` (see data structure)
4. Edit `config/channel_concept.json` (try customizing)

**Intermediate:**
1. Read PROJECT_SUMMARY.md (architecture)
2. Study `src/schema.py` (data model)
3. Study `src/main.py` (orchestration)
4. Run individual stages with `--stage`

**Advanced:**
1. Read DEVELOPMENT.md (extension)
2. Add custom image provider
3. Add custom TTS provider
4. Implement new effects
5. Set up database backend

---

## ✅ Checklist: Before First Run

- [ ] Read QUICKSTART.md
- [ ] Install Python 3.8+
- [ ] `pip install -r requirements.txt`
- [ ] Install ffmpeg (system package)
- [ ] Set ANTHROPIC_API_KEY environment variable
- [ ] `python src/main.py new-episode --series cars --topic Toyota`
- [ ] `python src/main.py run-all --series cars --episode toyota`
- [ ] Check `series/cars/episodes/toyota/script.md`
- [ ] Review `visual_prompts_review.csv`
- [ ] ✨ Ready for expensive stages!

---

## 🎉 You're All Set!

Pick a starting point:
- **First time?** → [QUICKSTART.md](QUICKSTART.md)
- **Want details?** → [README.md](README.md)
- **Want to extend?** → [DEVELOPMENT.md](DEVELOPMENT.md)
- **Want architecture?** → [PROJECT_SUMMARY.md](PROJECT_SUMMARY.md)

Happy generating! 🎬
