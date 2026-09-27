"""
Stage 6: TTS Voiceover Generation
Input: chunks with narration_text
Output: chunks with asset_paths.audio and duration_estimate_sec

This stage generates audio files per chunk using a TTS service
(ElevenLabs, Azure, Google, or local Coqui).
The actual TTS duration becomes the ground truth for how long
each image stays on screen during video assembly.
"""

import json
import logging
import hashlib
from pathlib import Path
from typing import Optional, Tuple
import io

from schema import Episode, ChunkStatus

logger = logging.getLogger(__name__)


class TTSClient:
    """
    Wrapper for TTS services.
    Supports ElevenLabs, Azure, Google, OpenAI, or local Coqui.
    """

    def __init__(
        self,
        provider: str = "elevenlabs",  # elevenlabs | azure | google | openai | coqui
        api_key: Optional[str] = None,
        cache_dir: str = ".cache/audio",
        voice_id: str = "default",
    ):
        """
        Initialize TTS client.
        
        Args:
            provider: TTS service provider
            api_key: API key for the service
            cache_dir: Directory for caching audio files
            voice_id: Voice identifier (specific to provider)
        """
        self.provider = provider
        self.voice_id = voice_id
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        
        if provider == "elevenlabs":
            try:
                import elevenlabs
                self.client = elevenlabs.ElevenLabs(api_key=api_key)
            except ImportError:
                logger.warning("elevenlabs SDK not installed. Install: pip install elevenlabs")
        elif provider == "azure":
            try:
                import azure.cognitiveservices.speech as speechsdk
                self.speech_config = speechsdk.SpeechConfig(api_key=api_key, region="eastus")
            except ImportError:
                logger.warning("azure-cognitiveservices-speech not installed")
        elif provider == "openai":
            try:
                import openai
                self.client = openai.OpenAI(api_key=api_key)
            except ImportError:
                logger.warning("openai SDK not installed")
        elif provider == "coqui":
            logger.info("Using Coqui TTS (local/offline)")
        else:
            logger.warning(f"Unknown TTS provider: {provider}")

    def _get_prompt_hash(self, text: str) -> str:
        """Get cache key for text."""
        return hashlib.md5(text.encode()).hexdigest()

    def _get_cached_audio_path(self, text_hash: str) -> Optional[Path]:
        """Check if audio is cached."""
        cached_path = self.cache_dir / f"{text_hash}.mp3"
        if cached_path.exists():
            logger.info(f"Using cached audio for hash {text_hash}")
            return cached_path
        return None

    def _get_duration(self, audio_path: Path) -> float:
        """Get duration of audio file in seconds."""
        try:
            from pydub import AudioSegment
            audio = AudioSegment.from_mp3(str(audio_path))
            return len(audio) / 1000.0  # Convert ms to seconds
        except ImportError:
            logger.warning("pydub not installed. Install: pip install pydub")
            # Rough estimate: ~150 words per minute = 2.5 words per second
            word_count = len(audio_path.stem.split())
            return word_count / 2.5
        except Exception as e:
            logger.warning(f"Could not determine audio duration: {e}")
            return 0.0

    def generate(
        self,
        text: str,
        chunk_id: str,
        output_dir: Path,
        use_cache: bool = True,
    ) -> Tuple[Optional[Path], float]:
        """
        Generate TTS audio from text.
        
        Args:
            text: Text to synthesize
            chunk_id: Chunk ID (for naming)
            output_dir: Directory to save audio
            use_cache: Use cached audio if available
        
        Returns:
            Tuple of (path to audio file, duration in seconds), or (None, 0.0) if failed
        """
        
        output_dir.mkdir(parents=True, exist_ok=True)
        text_hash = self._get_prompt_hash(text)
        
        # Check cache
        if use_cache:
            cached = self._get_cached_audio_path(text_hash)
            if cached:
                duration = self._get_duration(cached)
                # Copy to output dir
                output_path = output_dir / f"{chunk_id}.mp3"
                import shutil
                shutil.copy(cached, output_path)
                return output_path, duration
        
        try:
            if self.provider == "elevenlabs":
                return self._generate_elevenlabs(text, chunk_id, output_dir, text_hash)
            elif self.provider == "azure":
                return self._generate_azure(text, chunk_id, output_dir, text_hash)
            elif self.provider == "openai":
                return self._generate_openai(text, chunk_id, output_dir, text_hash)
            elif self.provider == "coqui":
                return self._generate_coqui(text, chunk_id, output_dir, text_hash)
        except Exception as e:
            logger.error(f"Failed to generate TTS for {chunk_id}: {e}")
            return None, 0.0

    def _generate_elevenlabs(
        self, text: str, chunk_id: str, output_dir: Path, text_hash: str
    ) -> Tuple[Optional[Path], float]:
        """Generate using ElevenLabs API."""
        logger.info(f"Generating TTS with ElevenLabs for {chunk_id}")
        
        try:
            # Call ElevenLabs
            audio_data = self.client.generate(
                text=text,
                voice=self.voice_id or "Rachel",
                model="eleven_monolingual_v1"
            )
            
            # Save audio
            output_path = output_dir / f"{chunk_id}.mp3"
            with open(output_path, 'wb') as f:
                for chunk in audio_data:
                    f.write(chunk)
            
            # Cache it
            cached_path = self.cache_dir / f"{text_hash}.mp3"
            import shutil
            shutil.copy(output_path, cached_path)
            
            duration = self._get_duration(output_path)
            logger.info(f"Audio saved: {output_path} ({duration:.2f}s)")
            return output_path, duration
            
        except Exception as e:
            logger.error(f"ElevenLabs generation failed: {e}")
            return None, 0.0

    def _generate_azure(
        self, text: str, chunk_id: str, output_dir: Path, text_hash: str
    ) -> Tuple[Optional[Path], float]:
        """Generate using Azure Cognitive Services."""
        logger.info(f"Generating TTS with Azure for {chunk_id}")
        
        try:
            import azure.cognitiveservices.speech as speechsdk
            
            self.speech_config.speech_synthesis_voice_name = "en-US-AriaNeural"
            
            output_path = output_dir / f"{chunk_id}.mp3"
            audio_config = speechsdk.audio.AudioOutputConfig(filename=str(output_path))
            
            synthesizer = speechsdk.SpeechSynthesizer(
                speech_config=self.speech_config, audio_config=audio_config
            )
            
            result = synthesizer.speak_text(text)
            
            if result.reason == speechsdk.ResultReason.SynthesizingAudioCompleted:
                duration = self._get_duration(output_path)
                logger.info(f"Audio saved: {output_path} ({duration:.2f}s)")
                
                # Cache it
                cached_path = self.cache_dir / f"{text_hash}.mp3"
                import shutil
                shutil.copy(output_path, cached_path)
                
                return output_path, duration
            else:
                logger.error(f"Azure TTS failed: {result.error_details}")
                return None, 0.0
                
        except Exception as e:
            logger.error(f"Azure generation failed: {e}")
            return None, 0.0

    def _generate_openai(
        self, text: str, chunk_id: str, output_dir: Path, text_hash: str
    ) -> Tuple[Optional[Path], float]:
        """Generate using OpenAI TTS API."""
        logger.info(f"Generating TTS with OpenAI for {chunk_id}")
        
        try:
            response = self.client.audio.speech.create(
                model="tts-1",
                voice="alloy",
                input=text,
            )
            
            output_path = output_dir / f"{chunk_id}.mp3"
            response.stream_to_file(str(output_path))
            
            duration = self._get_duration(output_path)
            logger.info(f"Audio saved: {output_path} ({duration:.2f}s)")
            
            # Cache it
            cached_path = self.cache_dir / f"{text_hash}.mp3"
            import shutil
            shutil.copy(output_path, cached_path)
            
            return output_path, duration
            
        except Exception as e:
            logger.error(f"OpenAI generation failed: {e}")
            return None, 0.0

    def _generate_coqui(
        self, text: str, chunk_id: str, output_dir: Path, text_hash: str
    ) -> Tuple[Optional[Path], float]:
        """Generate using local Coqui TTS."""
        logger.info(f"Generating TTS with Coqui for {chunk_id}")
        
        try:
            from TTS.api import TTS
            
            tts = TTS(model_name="tts_models/en/ljspeech/glow-tts", progress_bar=False)
            
            output_path = output_dir / f"{chunk_id}.wav"
            tts.tts_to_file(text=text, file_path=str(output_path))
            
            # Convert WAV to MP3
            import subprocess
            mp3_path = output_path.with_suffix('.mp3')
            subprocess.run([
                'ffmpeg', '-i', str(output_path), '-q:a', '9', '-n', str(mp3_path)
            ], check=False, capture_output=True)
            
            if mp3_path.exists():
                duration = self._get_duration(mp3_path)
                logger.info(f"Audio saved: {mp3_path} ({duration:.2f}s)")
                return mp3_path, duration
            
            return None, 0.0
            
        except ImportError:
            logger.error("Coqui TTS not installed. Install: pip install tts")
            return None, 0.0
        except Exception as e:
            logger.error(f"Coqui generation failed: {e}")
            return None, 0.0


def generate_tts(
    episode: Episode,
    output_dir: Optional[str] = None,
    provider: str = "elevenlabs",
    use_cache: bool = True,
) -> Episode:
    """
    Generate TTS audio for all chunks in an episode.
    
    Args:
        episode: Episode with chunks and narration text
        output_dir: Directory to save audio (defaults to episode assets dir)
        provider: TTS provider
        use_cache: Use cached audio
    
    Returns:
        Updated episode with audio paths and durations
    """
    
    if not output_dir:
        output_dir = f"series/{episode.series_name}/episodes/{episode.episode_id}/assets/audio"
    
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    
    client = TTSClient(provider=provider)
    
    logger.info(f"Generating TTS for {episode.episode_id} using {provider}")
    total_chunks = sum(len(f.chunks) for f in episode.facts)
    processed = 0
    
    for fact in episode.facts:
        for chunk in fact.chunks:
            if not chunk.narration_text:
                logger.warning(f"Chunk {chunk.chunk_id} has no narration_text")
                continue
            
            audio_path, duration = client.generate(
                text=chunk.narration_text,
                chunk_id=chunk.chunk_id,
                output_dir=output_path,
                use_cache=use_cache,
            )
            
            if audio_path:
                chunk.asset_paths.audio = str(audio_path)
                chunk.duration_estimate_sec = duration
                chunk.status = ChunkStatus.GENERATED
            else:
                chunk.status = ChunkStatus.FAILED
            
            processed += 1
            if processed % 5 == 0:
                logger.info(f"Progress: {processed}/{total_chunks}")
    
    logger.info(f"TTS generation complete")
    return episode


if __name__ == "__main__":
    import sys
    
    logging.basicConfig(level=logging.INFO)
    
    if len(sys.argv) < 2:
        print("Usage: python 06_generate_tts.py <episode_json_path> [--provider elevenlabs|azure|openai|coqui]")
        sys.exit(1)
    
    episode_path = sys.argv[1]
    provider = sys.argv[3] if len(sys.argv) > 3 and sys.argv[2] == "--provider" else "elevenlabs"
    
    with open(episode_path, 'r') as f:
        episode_data = json.load(f)
    episode = Episode(**episode_data)
    
    episode = generate_tts(episode, provider=provider)
    
    with open(episode_path, 'w') as f:
        json.dump(episode.model_dump(), f, indent=2, default=str)
    
    print(f"\n✓ TTS generated")
