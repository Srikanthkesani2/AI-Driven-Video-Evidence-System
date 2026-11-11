import os
import sys
from pathlib import Path
import pytest

# Append root directory to python execution path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

@pytest.fixture
def mock_video_path(tmp_path):
    video = tmp_path / "test_crime.mp4"
    video.write_bytes(b"MOCK VIDEO BINARIES")
    return video
