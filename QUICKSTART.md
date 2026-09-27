# Quick Start Guide

## 5-Minute Setup

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Install ffmpeg
- **Windows:** `choco install ffmpeg`
- **macOS:** `brew install ffmpeg`
- **Linux:** `apt install ffmpeg`

### 3. Set API Key
```bash
export ANTHROPIC_API_KEY=your_key_here
```

### 4. Create Your First Episode
```bash
python src/main.py new-episode --series cars --topic Toyota
```

### 5. Generate Script (Free!)
```bash
python src/main.py run-stage --series cars --episode toyota --stage script
```

Check the result:
```bash
cat series/cars/episodes/toyota/script.md
```

### 6. Decompose & Review (Still Free!)
```bash
# Stages 2-4 are all text-based and use cached LLM calls
python src/main.py run-all --series cars --episode toyota
```

Check visual prompts:
```bash
cat series/cars/episodes/toyota/visual_prompts_review.csv
```

### 7. Generate Images (Costs Money!)
```bash
# First time: ~$0.05-0.10 per image
python src/pipeline/05_generate_images.py series/cars/episodes/toyota/episode.json --provider openai
```

### 8. Generate Voiceover
```bash
# ~$0.30 per 1000 characters
python src/pipeline/06_generate_tts.py series/cars/episodes/toyota/episode.json --provider elevenlabs
```

### 9. Assemble Final Video
```bash
python src/pipeline/07_assemble_video.py series/cars/episodes/toyota/episode.json
```

### 10. Watch Your Video!
```bash
series/cars/episodes/toyota/toyota_final.mp4
```

---

## What Each Stage Costs

| Stage | Cost | Time | Cacheable |
|-------|------|------|-----------|
| 1. Script | ~$0.01 | 30s | Yes |
| 2. Facts | Free | 5s | N/A |
| 3. Chunks | ~$0.05 | 10s | Yes |
| 4. Visual Prompts | ~$0.10 | 20s | Yes |
| 5. Images | $2-5 | 2-3 min | Yes |
| 6. TTS | $1-2 | 1 min | Yes |
| 7. Assemble | Free | 2 min | N/A |
| **Total** | **$3-8** | **~7 min** | **High** |

---

## Pro Tips

### Tip 1: Review Before Spending
Stop after Stage 4 (visual prompts) and review outputs. Edit `episode.json` if you want different prompts.

### Tip 2: Caching Saves Money
Run the same episode twice:
- First run: Full cost
- Second run: ~10% cost (cached)

### Tip 3: Batch Processing
Process multiple episodes with:
```bash
for topic in Toyota Ford BMW Ferrari; do
  python src/main.py new-episode --series cars --topic "$topic"
  python src/main.py run-all --series cars --episode ${topic,,}
done
```

### Tip 4: Local Image Generation
Save costs by using local Stable Diffusion. Requires GPU but then it's free!
```bash
python src/pipeline/05_generate_images.py episode.json --provider local_sd
```

### Tip 5: Tweak Style Guide
Edit `config/style_guide.json` to change visual consistency across all images. Re-run Stage 4 to regenerate prompts with new style.

---

## Troubleshooting

**Q: "No module named anthropic"**  
A: `pip install anthropic`

**Q: "ffmpeg not found"**  
A: Install ffmpeg (see Setup section)

**Q: API rate limit**  
A: Cache is your friend. Outputs are already cached from first run.

**Q: Images look inconsistent**  
A: Edit `locked_keywords` in `config/style_guide.json` and re-run Stage 4.

---

## Next Steps

1. **Explore:** Check `series/cars/episodes/toyota/episode.json` to see the full pipeline state
2. **Customize:** Edit prompts, style guide, channel concept
3. **Automate:** Build batch scripts for entire series
4. **Extend:** Add subtitles, background music, custom fonts in Stage 7

For full details, see [README.md](README.md)
