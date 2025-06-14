#!/usr/bin/env python3
"""
VoiceFilter - Speaker-aware filtering using pyannote embeddings.
Filters out the primary user's voice while allowing others through.
"""

import numpy as np
import torch
import logging
from pathlib import Path
from typing import Union, Optional, Tuple
from scipy.spatial.distance import cosine
import threading
import time

logger = logging.getLogger(__name__)

class VoiceFilter:
    """
    Filter audio based on speaker embeddings.
    Uses pyannote to identify if audio belongs to the primary user.
    """
    
    def __init__(self, 
                 profile_path: str = "my_voice.npy",
                 similarity_threshold: float = 0.75,
                 cache_duration: float = 1.0):
        """
        Initialize VoiceFilter.
        
        Args:
            profile_path: Path to saved voice embedding (.npy file)
            similarity_threshold: Cosine similarity threshold (0.0-1.0)
            cache_duration: Duration to cache embeddings (seconds)
        """
        self.profile_path = Path(profile_path)
        self.similarity_threshold = similarity_threshold
        self.cache_duration = cache_duration
        
        # Load reference embedding
        if self.profile_path.exists():
            self.reference_embedding = np.load(self.profile_path)
            logger.info(f"Loaded voice profile from {profile_path}")
            logger.info(f"Reference embedding shape: {self.reference_embedding.shape}")
        else:
            logger.warning(f"Voice profile not found at {profile_path}")
            self.reference_embedding = None
        
        # Initialize model (lazy loading)
        self._model = None
        self._audio_processor = None
        
        # Embedding cache to reduce computation
        self._cache = {}
        self._cache_lock = threading.Lock()
        self._last_cache_clear = time.time()
        
    def _load_model(self):
        """Lazy load the speaker embedding model."""
        if self._model is None:
            try:
                # Try SpeechBrain model (no auth required)
                from speechbrain.inference.speaker import EncoderClassifier
                
                logger.info("Loading SpeechBrain speaker embedding model...")
                self._model = EncoderClassifier.from_hparams(
                    source="speechbrain/spkrec-ecapa-voxceleb",
                    savedir="pretrained_models/spkrec-ecapa-voxceleb"
                )
                logger.info("Model loaded successfully")
                
            except Exception as e:
                logger.error(f"Failed to load speaker embedding model: {e}")
                raise
    
    def is_user(self, audio: Union[np.ndarray, torch.Tensor], 
                sample_rate: int = 16000) -> Tuple[bool, float]:
        """
        Check if audio belongs to the primary user.
        
        Args:
            audio: Audio waveform (numpy array or torch tensor)
            sample_rate: Sample rate of the audio
            
        Returns:
            Tuple of (is_user, similarity_score)
        """
        if self.reference_embedding is None:
            logger.warning("No reference embedding loaded, allowing all audio")
            return False, 0.0
        
        try:
            # Ensure model is loaded
            self._load_model()
            
            # Convert to tensor if needed
            if isinstance(audio, np.ndarray):
                audio = torch.from_numpy(audio).float()
            
            # Ensure correct shape (batch, time)
            if audio.dim() == 1:
                audio = audio.unsqueeze(0)
            
            # Resample if needed
            if sample_rate != 16000:
                import torchaudio
                audio = torchaudio.functional.resample(audio, sample_rate, 16000)
            
            # Generate embedding using SpeechBrain
            # Need to save audio temporarily
            import tempfile
            import soundfile as sf
            import os
            
            with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as tmp_file:
                if isinstance(audio, torch.Tensor):
                    audio_np = audio.cpu().numpy()
                else:
                    audio_np = audio
                    
                # Ensure 1D
                if audio_np.ndim > 1:
                    audio_np = audio_np.squeeze()
                    
                sf.write(tmp_file.name, audio_np, sample_rate)
                
                # Generate embedding
                embeddings = self._model.encode_batch_from_file(tmp_file.name)
                embedding = embeddings.squeeze().cpu().numpy()
                
                # Clean up
                os.unlink(tmp_file.name)
            
            # Calculate similarity
            similarity = 1 - cosine(embedding, self.reference_embedding)
            
            # Make decision
            is_user = similarity >= self.similarity_threshold
            
            logger.debug(f"Similarity: {similarity:.3f}, Is user: {is_user}")
            
            return is_user, similarity
            
        except Exception as e:
            logger.error(f"Error in voice filtering: {e}")
            # On error, allow audio through
            return False, 0.0
    
    def clear_cache(self):
        """Clear the embedding cache."""
        with self._cache_lock:
            self._cache.clear()
            self._last_cache_clear = time.time()
    
    def update_threshold(self, new_threshold: float):
        """Update the similarity threshold."""
        self.similarity_threshold = new_threshold
        logger.info(f"Updated similarity threshold to {new_threshold}")
    
    def get_stats(self) -> dict:
        """Get statistics about the voice filter."""
        return {
            "profile_loaded": self.reference_embedding is not None,
            "similarity_threshold": self.similarity_threshold,
            "cache_size": len(self._cache),
            "model_loaded": self._model is not None
        }


class MockVoiceFilter:
    """Mock voice filter for testing without pyannote dependencies."""
    
    def __init__(self, always_allow=True):
        self.always_allow = always_allow
        logger.info("Using MockVoiceFilter for testing")
    
    def is_user(self, audio, sample_rate=16000):
        """Mock implementation - always returns configured value."""
        return not self.always_allow, 0.5
    
    def get_stats(self):
        """Mock stats."""
        return {
            "profile_loaded": True,
            "similarity_threshold": 0.75,
            "cache_size": 0,
            "model_loaded": True,
            "mock": True
        }