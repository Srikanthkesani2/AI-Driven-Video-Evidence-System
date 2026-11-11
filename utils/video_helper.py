from pathlib import Path
from typing import Optional
from utils.logger import logger

def generate_video_thumbnail(video_path: Path, output_dir: Path) -> Optional[str]:
    """Extracts the first frame of a video using OpenCV and saves it as a thumbnail image."""
    output_dir.mkdir(parents=True, exist_ok=True)
    thumbnail_path = output_dir / f"{video_path.stem}_thumb.jpg"
    
    logger.info(f"Generating video thumbnail for: {video_path.name}")
    
    try:
        import cv2
        cap = cv2.VideoCapture(str(video_path))
        if not cap.isOpened():
            logger.warning(f"Could not open video file {video_path} to extract frame.")
            return None
            
        success, frame = cap.read()
        if success:
            # Resize thumbnail for UI performance
            frame_resized = cv2.resize(frame, (320, 180))
            cv2.imwrite(str(thumbnail_path), frame_resized)
            cap.release()
            logger.info(f"Thumbnail saved successfully at: {thumbnail_path}")
            return f"/static/processed/{thumbnail_path.name}"
        cap.release()
    except Exception as e:
        logger.warning(f"Failed to generate video thumbnail using cv2: {e}")
        
    # Standard fallback path if video frame extraction fails or cv2 is missing
    # We return a placeholder indicator string
    return "/static/assets/video_placeholder.jpg"
