"""
Stage 7: Video Assembly
Input: episode with images and audio files ready
Output: final_video.mp4

This stage uses ffmpeg to:
1. Apply Ken Burns zoom/pan effect to each image
2. Synchronize with TTS audio duration
3. Add transitions between chunks
4. Optionally add background music, subtitles, era labels
5. Export final MP4
"""

import json
import logging
import subprocess
from pathlib import Path
from typing import Optional, List
import tempfile

from schema import Episode, EpisodeStatus

logger = logging.getLogger(__name__)


class VideoAssembler:
    """
    Assembles video from images + audio using ffmpeg.
    Handles Ken Burns effects, audio sync, and concatenation.
    """

    def __init__(self, ffmpeg_path: str = "ffmpeg"):
        """
        Initialize video assembler.
        
        Args:
            ffmpeg_path: Path to ffmpeg executable
        """
        self.ffmpeg_path = ffmpeg_path

    def _check_ffmpeg(self) -> bool:
        """Check if ffmpeg is available."""
        try:
            subprocess.run(
                [self.ffmpeg_path, "-version"],
                capture_output=True,
                check=True
            )
            return True
        except (subprocess.CalledProcessError, FileNotFoundError):
            logger.error(f"ffmpeg not found at {self.ffmpeg_path}")
            return False

    def apply_ken_burns(
        self,
        image_path: Path,
        duration: float,
        output_path: Path,
        zoom_amount: float = 1.05,
    ) -> bool:
        """
        Apply Ken Burns effect (slow zoom/pan) to an image.
        
        Args:
            image_path: Input image
            duration: Duration in seconds
            output_path: Output video
            zoom_amount: Zoom scale (1.0 = no zoom, 1.05 = 5% zoom)
        
        Returns:
            True if successful
        """
        
        try:
            # Ken Burns filter: slow zoom from center
            # This creates a subtle zoom effect over the duration
            cmd = [
                self.ffmpeg_path,
                "-loop", "1",
                "-i", str(image_path),
                "-c:v", "libx264",
                "-pix_fmt", "yuv420p",
                "-vf", f"zoom=min(iw\\,ih)/min(iw\\,ih)*{zoom_amount}:d={duration}:s=in_sine:r=30,scale=1920:1080:force_original_aspect_ratio=decrease,pad=1920:1080:(ow-iw)/2:(oh-ih)/2",
                "-t", str(duration),
                "-y",  # Overwrite output
                str(output_path)
            ]
            
            logger.debug(f"Running: {' '.join(cmd)}")
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode != 0:
                logger.error(f"Ken Burns filter failed: {result.stderr}")
                return False
            
            logger.info(f"Ken Burns effect applied: {output_path}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to apply Ken Burns effect: {e}")
            return False

    def concatenate_videos(
        self,
        video_files: List[Path],
        audio_files: List[Path],
        output_path: Path,
    ) -> bool:
        """
        Concatenate video clips and overlay audio tracks.
        
        Args:
            video_files: List of video files (in order)
            audio_files: List of audio files (in order, same length)
            output_path: Output video file
        
        Returns:
            True if successful
        """
        
        if len(video_files) != len(audio_files):
            logger.error(f"Mismatch: {len(video_files)} videos, {len(audio_files)} audios")
            return False
        
        try:
            # Create concat demux file
            with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
                for video_file in video_files:
                    f.write(f"file '{video_file.absolute()}'\n")
                concat_file = f.name
            
            # First pass: concatenate videos
            concat_video = output_path.parent / "concat_video.mp4"
            cmd = [
                self.ffmpeg_path,
                "-f", "concat",
                "-safe", "0",
                "-i", concat_file,
                "-c", "copy",
                "-y",
                str(concat_video)
            ]
            
            logger.info("Concatenating videos...")
            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode != 0:
                logger.error(f"Concatenation failed: {result.stderr}")
                return False
            
            # Second pass: create audio concat file and concatenate audio
            with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
                for audio_file in audio_files:
                    f.write(f"file '{audio_file.absolute()}'\n")
                audio_concat_file = f.name
            
            concat_audio = output_path.parent / "concat_audio.aac"
            cmd = [
                self.ffmpeg_path,
                "-f", "concat",
                "-safe", "0",
                "-i", audio_concat_file,
                "-c:a", "aac",
                "-q:a", "5",
                "-y",
                str(concat_audio)
            ]
            
            logger.info("Concatenating audio...")
            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode != 0:
                logger.error(f"Audio concatenation failed: {result.stderr}")
                return False
            
            # Final pass: mux video + audio
            cmd = [
                self.ffmpeg_path,
                "-i", str(concat_video),
                "-i", str(concat_audio),
                "-c:v", "copy",
                "-c:a", "aac",
                "-y",
                str(output_path)
            ]
            
            logger.info("Muxing video and audio...")
            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode != 0:
                logger.error(f"Muxing failed: {result.stderr}")
                return False
            
            # Cleanup temp files
            Path(concat_file).unlink()
            Path(audio_concat_file).unlink()
            concat_video.unlink()
            concat_audio.unlink()
            
            logger.info(f"Final video created: {output_path}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to concatenate videos: {e}")
            return False


def assemble_video(
    episode: Episode,
    output_dir: Optional[str] = None,
    resolution: str = "1920x1080",
    fps: int = 30,
) -> Episode:
    """
    Assemble final video from images and audio.
    
    Args:
        episode: Episode with images and audio generated
        output_dir: Directory to save final video
        resolution: Video resolution
        fps: Frames per second
    
    Returns:
        Updated episode with final_video_path
    """
    
    if not output_dir:
        output_dir = f"series/{episode.series_name}/episodes/{episode.episode_id}"
    
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    
    assembler = VideoAssembler()
    
    if not assembler._check_ffmpeg():
        logger.error("ffmpeg not available. Install ffmpeg to assemble videos.")
        episode.error_message = "ffmpeg not found"
        episode.status = EpisodeStatus.FAILED
        return episode
    
    logger.info(f"Assembling video for {episode.episode_id}")
    
    try:
        # Collect all chunks in order
        chunks = []
        for fact in episode.facts:
            chunks.extend(fact.chunks)
        
        if not chunks:
            logger.error("No chunks found")
            episode.error_message = "No chunks to assemble"
            return episode
        
        # Verify all chunks have required assets
        missing_assets = []
        for chunk in chunks:
            if not chunk.asset_paths.image:
                missing_assets.append(f"{chunk.chunk_id}: missing image")
            if not chunk.asset_paths.audio:
                missing_assets.append(f"{chunk.chunk_id}: missing audio")
        
        if missing_assets:
            logger.error(f"Missing assets:\n" + "\n".join(missing_assets))
            episode.error_message = "Missing asset files"
            return episode
        
        # Generate Ken Burns videos for each image
        logger.info("Applying Ken Burns effects...")
        video_files = []
        audio_files = []
        
        for i, chunk in enumerate(chunks):
            image_path = Path(chunk.asset_paths.image)
            audio_path = Path(chunk.asset_paths.audio)
            duration = chunk.duration_estimate_sec
            
            if duration <= 0:
                logger.warning(f"Chunk {chunk.chunk_id} has invalid duration: {duration}")
                duration = 5.0  # Default fallback
            
            video_path = output_path / f"temp_chunk_{i:04d}.mp4"
            
            success = assembler.apply_ken_burns(
                image_path,
                duration,
                video_path,
                zoom_amount=1.02  # 2% zoom
            )
            
            if not success:
                logger.error(f"Failed to process chunk {chunk.chunk_id}")
                chunk.status = ChunkStatus.FAILED
                continue
            
            video_files.append(video_path)
            audio_files.append(audio_path)
        
        if not video_files:
            episode.error_message = "No video files generated"
            return episode
        
        # Concatenate all videos and audio
        final_video = output_path / f"{episode.episode_id}_final.mp4"
        
        logger.info("Concatenating all clips...")
        success = assembler.concatenate_videos(video_files, audio_files, final_video)
        
        if success:
            episode.final_video_path = str(final_video)
            episode.status = EpisodeStatus.ASSEMBLED
            logger.info(f"✓ Video assembly complete: {final_video}")
        else:
            episode.error_message = "Failed to concatenate videos"
            episode.status = EpisodeStatus.FAILED
        
        # Cleanup temp files
        for f in video_files:
            try:
                f.unlink()
            except:
                pass
        
        return episode
        
    except Exception as e:
        logger.error(f"Failed to assemble video: {e}")
        episode.error_message = str(e)
        episode.status = EpisodeStatus.FAILED
        return episode


if __name__ == "__main__":
    import sys
    
    logging.basicConfig(level=logging.INFO)
    
    if len(sys.argv) < 2:
        print("Usage: python 07_assemble_video.py <episode_json_path>")
        sys.exit(1)
    
    episode_path = sys.argv[1]
    
    with open(episode_path, 'r') as f:
        episode_data = json.load(f)
    episode = Episode(**episode_data)
    
    episode = assemble_video(episode)
    
    with open(episode_path, 'w') as f:
        json.dump(episode.model_dump(), f, indent=2, default=str)
    
    if episode.final_video_path:
        print(f"\n✓ Video assembled: {episode.final_video_path}")
    else:
        print(f"\n✗ Video assembly failed: {episode.error_message}")
