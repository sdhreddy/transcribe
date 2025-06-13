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
    
    def __init__(self, profile_path: str = "my_voice.npy", threshold: float = 0.25):
        """Initialize voice filter with user's voice profile.
        
        Args:
            profile_path: Path to saved voice embedding (.npy file)
            threshold: Cosine distance threshold for voice matching (lower = stricter)
        """
        self.profile_path = profile_path
        self.threshold = threshold
        self.user_embedding = None
        self.inference = None
        
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
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
                # Convert to torch tensor and save
                if audio_data.dtype != np.float32:
                    audio_data = audio_data.astype(np.float32)
                
                # Normalize if needed
                if np.abs(audio_data).max() > 1.0:
                    audio_data = audio_data / 32768.0
                
                tensor = torch.from_numpy(audio_data).unsqueeze(0)
                torchaudio.save(tmp.name, tensor, sample_rate)
                
                # Extract embedding
                embedding = self.inference(tmp.name)
                
                # Clean up
                os.unlink(tmp.name)
                
            return embedding
            
        except Exception as e:
            logger.error(f"Failed to extract embedding from array: {e}")
            return None
    
    def is_user_voice(self, audio_data: np.ndarray, sample_rate: int) -> Tuple[bool, float]:
        """Check if audio contains user's voice.
        
        Returns:
            Tuple of (is_user_voice, confidence_score)
        """
        if not PYANNOTE_AVAILABLE or self.user_embedding is None or self.inference is None:
            return False, 0.0
        
        try:
            # Extract embedding from audio
            embedding = self.extract_embedding_from_array(audio_data, sample_rate)
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
            return False, 0.0
    
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