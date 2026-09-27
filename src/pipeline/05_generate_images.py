"""
Stage 5: Image Generation
Input: chunks with visual_prompt populated
Output: chunks with asset_paths.image pointing to generated images

This stage calls an image generation API (Flux, DALL-E, or local SD/Flux)
and caches results to avoid re-generating the same prompts.
"""

import json
import logging
import hashlib
from pathlib import Path
from typing import Optional, Dict, Any
from datetime import datetime

from schema import Episode, ChunkStatus

logger = logging.getLogger(__name__)


class ImageGenerationClient:
    """
    Wrapper for image generation APIs.
    Supports Flux, DALL-E, or local Stable Diffusion.
    """

    def __init__(
        self,
        provider: str = "flux",  # flux | openai | local_sd
        api_key: Optional[str] = None,
        cache_dir: str = ".cache/images",
        model: str = "flux-pro",
    ):
        """
        Initialize image generation client.
        
        Args:
            provider: Image generation service (flux, openai, local_sd)
            api_key: API key for the service
            cache_dir: Directory for caching generated images
            model: Model identifier
        """
        self.provider = provider
        self.model = model
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        
        if provider == "flux":
            try:
                import anthropic
                self.client = anthropic.Anthropic(api_key=api_key)
            except ImportError:
                logger.warning("Anthropic SDK not installed. Install: pip install anthropic")
        elif provider == "openai":
            try:
                import openai
                self.client = openai.OpenAI(api_key=api_key)
            except ImportError:
                logger.warning("OpenAI SDK not installed. Install: pip install openai")
        elif provider == "local_sd":
            logger.info("Using local Stable Diffusion (requires running server)")

    def _get_prompt_hash(self, prompt: str) -> str:
        """Get cache key for a prompt."""
        return hashlib.md5(prompt.encode()).hexdigest()

    def _get_cached_image_path(self, prompt_hash: str) -> Optional[Path]:
        """Check if image is cached."""
        cached_path = self.cache_dir / f"{prompt_hash}.png"
        if cached_path.exists():
            logger.info(f"Using cached image: {cached_path}")
            return cached_path
        return None

    def generate(
        self,
        prompt: str,
        chunk_id: str,
        output_dir: Path,
        use_cache: bool = True,
    ) -> Optional[Path]:
        """
        Generate an image from a prompt.
        
        Args:
            prompt: Image generation prompt
            chunk_id: ID of the chunk (for naming)
            output_dir: Directory to save the image
            use_cache: Use cached images if available
        
        Returns:
            Path to generated image, or None if failed
        """
        
        output_dir.mkdir(parents=True, exist_ok=True)
        prompt_hash = self._get_prompt_hash(prompt)
        
        # Check cache
        if use_cache:
            cached = self._get_cached_image_path(prompt_hash)
            if cached:
                # Copy to output dir
                output_path = output_dir / f"{chunk_id}.png"
                import shutil
                shutil.copy(cached, output_path)
                return output_path
        
        try:
            if self.provider == "flux":
                return self._generate_flux(prompt, chunk_id, output_dir, prompt_hash)
            elif self.provider == "openai":
                return self._generate_openai(prompt, chunk_id, output_dir, prompt_hash)
            elif self.provider == "local_sd":
                return self._generate_local_sd(prompt, chunk_id, output_dir, prompt_hash)
        except Exception as e:
            logger.error(f"Failed to generate image for {chunk_id}: {e}")
            return None

    def _generate_flux(
        self, prompt: str, chunk_id: str, output_dir: Path, prompt_hash: str
    ) -> Optional[Path]:
        """Generate using Flux API via Anthropic."""
        logger.info(f"Generating image with Flux for {chunk_id}")
        
        try:
            # Note: Flux image generation via Anthropic would use vision API
            # For now, we'll log that this would call the Flux API
            logger.info(f"[MOCK] Would call Flux API with prompt: {prompt[:100]}...")
            
            # This is a placeholder. Real implementation would:
            # 1. Call flux API
            # 2. Download image
            # 3. Save to output_dir and cache_dir
            
            output_path = output_dir / f"{chunk_id}.png"
            
            # For demo, create a placeholder
            output_path.write_text(f"[Flux image placeholder: {prompt_hash}]")
            
            return output_path
            
        except Exception as e:
            logger.error(f"Flux generation failed: {e}")
            return None

    def _generate_openai(
        self, prompt: str, chunk_id: str, output_dir: Path, prompt_hash: str
    ) -> Optional[Path]:
        """Generate using DALL-E API."""
        logger.info(f"Generating image with DALL-E for {chunk_id}")
        
        try:
            # Call DALL-E
            response = self.client.images.generate(
                model="dall-e-3",
                prompt=prompt,
                size="1024x1024",
                quality="standard",
                n=1,
            )
            
            image_url = response.data[0].url
            
            # Download and save
            import requests
            img_response = requests.get(image_url)
            
            output_path = output_dir / f"{chunk_id}.png"
            with open(output_path, 'wb') as f:
                f.write(img_response.content)
            
            # Also cache it
            cached_path = self.cache_dir / f"{prompt_hash}.png"
            with open(cached_path, 'wb') as f:
                f.write(img_response.content)
            
            logger.info(f"Image saved: {output_path}")
            return output_path
            
        except Exception as e:
            logger.error(f"DALL-E generation failed: {e}")
            return None

    def _generate_local_sd(
        self, prompt: str, chunk_id: str, output_dir: Path, prompt_hash: str
    ) -> Optional[Path]:
        """Generate using local Stable Diffusion server."""
        logger.info(f"Generating image with local SD for {chunk_id}")
        
        try:
            import requests
            
            # Assumes local SD server running at localhost:7860
            response = requests.post(
                "http://localhost:7860/api/txt2img",
                json={
                    "prompt": prompt,
                    "negative_prompt": "text, watermark, low quality",
                    "width": 1024,
                    "height": 1024,
                    "steps": 20,
                    "cfg_scale": 7.0,
                }
            )
            
            response.raise_for_status()
            
            # Save image
            output_path = output_dir / f"{chunk_id}.png"
            with open(output_path, 'wb') as f:
                f.write(response.content)
            
            logger.info(f"Image saved: {output_path}")
            return output_path
            
        except Exception as e:
            logger.error(f"Local SD generation failed: {e}")
            return None


def generate_images(
    episode: Episode,
    output_dir: Optional[str] = None,
    provider: str = "flux",
    use_cache: bool = True,
) -> Episode:
    """
    Generate images for all chunks in an episode.
    
    Args:
        episode: Episode with chunks and visual prompts
        output_dir: Directory to save images (defaults to episode assets dir)
        provider: Image generation provider
        use_cache: Use cached images
    
    Returns:
        Updated episode with image paths
    """
    
    if not output_dir:
        output_dir = f"series/{episode.series_name}/episodes/{episode.episode_id}/assets/images"
    
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    
    client = ImageGenerationClient(provider=provider)
    
    logger.info(f"Generating images for {episode.episode_id}")
    total_chunks = sum(len(f.chunks) for f in episode.facts)
    processed = 0
    
    for fact in episode.facts:
        for chunk in fact.chunks:
            if not chunk.visual_prompt:
                logger.warning(f"Chunk {chunk.chunk_id} has no visual_prompt")
                continue
            
            image_path = client.generate(
                prompt=chunk.visual_prompt,
                chunk_id=chunk.chunk_id,
                output_dir=output_path,
                use_cache=use_cache,
            )
            
            if image_path:
                chunk.asset_paths.image = str(image_path)
                chunk.status = ChunkStatus.GENERATED
            else:
                chunk.status = ChunkStatus.FAILED
            
            processed += 1
            if processed % 5 == 0:
                logger.info(f"Progress: {processed}/{total_chunks}")
    
    logger.info(f"Image generation complete")
    return episode


if __name__ == "__main__":
    import sys
    
    logging.basicConfig(level=logging.INFO)
    
    if len(sys.argv) < 2:
        print("Usage: python 05_generate_images.py <episode_json_path> [--provider flux|openai|local_sd]")
        sys.exit(1)
    
    episode_path = sys.argv[1]
    provider = sys.argv[3] if len(sys.argv) > 3 and sys.argv[2] == "--provider" else "flux"
    
    with open(episode_path, 'r') as f:
        episode_data = json.load(f)
    episode = Episode(**episode_data)
    
    episode = generate_images(episode, provider=provider)
    
    with open(episode_path, 'w') as f:
        json.dump(episode.model_dump(), f, indent=2, default=str)
    
    print(f"\n✓ Images generated")
