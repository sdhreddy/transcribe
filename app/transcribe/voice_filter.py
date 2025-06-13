"""Voice filtering using Pyannote speaker embeddings for inverted logic.
AI responds only to colleagues, not to primary user.
"""

import os
import logging
import numpy as np
from pathlib import Path
from typing import Optional, Tuple
import warnings

# Suppress warnings
warnings.filterwarnings("ignore")

logger = logging.getLogger(__name__)

try:
    import torch
    import torchaudio
    from pyannote.audio import Inference
    from scipy.spatial.distance import cosine
    PYANNOTE_AVAILABLE = True
except ImportError as e:
    logger.warning(f"Pyannote dependencies not available: {e}")
    PYANNOTE_AVAILABLE = False

class VoiceFilter:
    """Voice filter using Pyannote speaker embeddings for accurate voice identification."""
    
    def __init__(self, profile_path: str = "my_voice.npy", threshold: float = 0.25, min_window: float = 2.0):
        """Initialize voice filter with user's voice profile.
        
        Args:
            profile_path: Path to saved voice embedding (.npy file)
            threshold: Cosine distance threshold for voice matching (lower = stricter)
            min_window: Minimum audio duration in seconds to accumulate before making decision
        """
        self.profile_path = profile_path
        self.threshold = threshold
        self.user_embedding = None
        self.inference = None
        self.min_window = min_window
        # Audio buffer for accumulating short segments
        self.audio_buffer = []
        self.buffer_duration = 0.0
        self.buffer_sample_rate = None
        
        if not PYANNOTE_AVAILABLE:
            logger.error("Pyannote not available. Voice filtering disabled.")
            return
            
        # Initialize model
        self._initialize_model()
        
        # Load user voice profile
        if os.path.exists(profile_path):
            self.load_profile(profile_path)
        else:
            logger.warning(f"Voice profile not found at {profile_path}")
    
    def _initialize_model(self):
        """Initialize Pyannote speaker embedding model."""
        try:
            # Check for HuggingFace token
            hf_token = self._get_hf_token()
            if not hf_token:
                logger.error("HuggingFace token not found. Voice filtering disabled.")
                return
            
            # Initialize inference with explicit model
            self.inference = Inference(
                "pyannote/embedding",
                window="whole",
                use_auth_token=hf_token
            )
            logger.info("Pyannote model initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize Pyannote model: {e}")
            self.inference = None
    
    def _get_hf_token(self) -> Optional[str]:
        """Get HuggingFace token from environment or file."""
        # Try environment variable first
        token = os.environ.get("HF_TOKEN")
        if token:
            return token
        
        # Try file in home directory
        token_file = Path.home() / ".huggingface_token"
        if token_file.exists():
            return token_file.read_text().strip()
        
        # Try Windows-specific location
        win_token_file = Path.home() / "huggingface_token.txt"
        if win_token_file.exists():
            return win_token_file.read_text().strip()
        
        return None
    
    def load_profile(self, profile_path: str):
        """Load saved voice profile."""
        try:
            self.user_embedding = np.load(profile_path)
            logger.info(f"Loaded voice profile from {profile_path}")
            logger.info(f"Embedding shape: {self.user_embedding.shape}")
        except Exception as e:
            logger.error(f"Failed to load voice profile: {e}")
            self.user_embedding = None
    
    def save_profile(self, embedding: np.ndarray, profile_path: str = None):
        """Save voice profile to file."""
        if profile_path is None:
            profile_path = self.profile_path
        
        try:
            np.save(profile_path, embedding)
            logger.info(f"Saved voice profile to {profile_path}")
        except Exception as e:
            logger.error(f"Failed to save voice profile: {e}")
    
    def extract_embedding(self, audio_path: str) -> Optional[np.ndarray]:
        """Extract speaker embedding from audio file."""
        if not self.inference:
            return None
        
        try:
            # Get embedding using Pyannote
            embedding = self.inference(audio_path)
            return embedding
        
        except Exception as e:
            logger.error(f"Failed to extract embedding: {e}")
            return None
    
    def extract_embedding_from_array(self, audio_data: np.ndarray, sample_rate: int) -> Optional[np.ndarray]:
        """Extract speaker embedding from audio array."""
        if not self.inference:
            return None
        
        try:
            # Save to temporary file (Pyannote requires file input)
            import tempfile
            # Create temp file and close it immediately to avoid locking issues
            tmp_fd, tmp_path = tempfile.mkstemp(suffix=".wav")
            os.close(tmp_fd)  # Close file descriptor immediately
            
            try:
                # Convert to torch tensor and save
                if audio_data.dtype != np.float32:
                    audio_data = audio_data.astype(np.float32)
                
                # Normalize if needed
                if np.abs(audio_data).max() > 1.0:
                    audio_data = audio_data / 32768.0
                
                tensor = torch.from_numpy(audio_data).unsqueeze(0)
                torchaudio.save(tmp_path, tensor, sample_rate)
                
                # Extract embedding
                embedding = self.inference(tmp_path)
                
                return embedding
                
            finally:
                # Clean up - with retry for Windows
                try:
                    os.unlink(tmp_path)
                except Exception:
                    # If deletion fails, it's okay - temp files will be cleaned up later
                    pass
            
        except Exception as e:
            logger.error(f"Failed to extract embedding from array: {e}")
            return None
    
    def is_user_voice(self, audio_data: np.ndarray, sample_rate: int) -> Tuple[bool, float]:
        """Check if audio contains user's voice.
        
        Returns:
            Tuple of (is_user_voice, confidence_score)
            Returns (None, 0.0) if not enough audio accumulated yet
        """
        if not PYANNOTE_AVAILABLE or self.user_embedding is None or self.inference is None:
            return False, 0.0
        
        try:
            # Add to buffer
            self.audio_buffer.append(audio_data)
            self.buffer_duration += len(audio_data) / sample_rate
            self.buffer_sample_rate = sample_rate
            
            # Check if we have enough audio
            if self.buffer_duration < self.min_window:
                logger.debug(f"Buffering audio: {self.buffer_duration:.2f}s / {self.min_window}s")
                return None, 0.0  # Signal to keep buffering
            
            # Concatenate all buffered audio
            full_audio = np.concatenate(self.audio_buffer)
            
            # Clear buffer for next detection
            self.audio_buffer = []
            self.buffer_duration = 0.0
            
            # Extract embedding from full audio
            embedding = self.extract_embedding_from_array(full_audio, sample_rate)
            if embedding is None:
                return False, 0.0
            
            # Calculate cosine distance
            distance = cosine(self.user_embedding, embedding)
            
            # Check if within threshold
            is_user = distance < self.threshold
            confidence = 1.0 - distance
            
            logger.debug(f"Voice check: distance={distance:.3f}, threshold={self.threshold}, is_user={is_user}")
            
            return is_user, confidence
            
        except Exception as e:
            logger.error(f"Error in voice check: {e}")
            # Clear buffer on error
            self.audio_buffer = []
            self.buffer_duration = 0.0
            return False, 0.0
    
    def clear_buffer(self):
        """Clear the audio buffer."""
        self.audio_buffer = []
        self.buffer_duration = 0.0
        logger.debug("Voice filter buffer cleared")
    
    def should_respond(self, is_user_voice: bool, inverted: bool = True) -> bool:
        """Determine if AI should respond based on voice detection and logic setting.
        
        Args:
            is_user_voice: Whether the voice belongs to the primary user
            inverted: If True, respond only to non-users (colleagues)
        
        Returns:
            True if AI should respond, False otherwise
        """
        if inverted:
            # Inverted logic: respond only to colleagues (not user)
            return not is_user_voice
        else:
            # Normal logic: respond only to user
            return is_user_voice