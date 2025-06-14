#!/usr/bin/env python3
"""
VoiceFilter using pyannote embeddings.
This is the production version that uses the real voice-print.
"""

import numpy as np
import torch
import logging
from pathlib import Path
from typing import Union, Tuple
from scipy.spatial.distance import cosine
import tempfile
import soundfile as sf

logger = logging.getLogger(__name__)

class VoiceFilter:
    """
    Filter audio based on pyannote speaker embeddings.
    """
    
    def __init__(self, 
                 profile_path: str = "my_voice.npy",
                 similarity_threshold: float = 0.75):
        """
        Initialize VoiceFilter with pyannote embedding.
        
        Args:
            profile_path: Path to saved voice embedding (.npy file)
            similarity_threshold: Cosine similarity threshold (0.0-1.0)
        """
        self.profile_path = Path(profile_path)
        self.similarity_threshold = similarity_threshold
        
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
        self._inference = None
        
    def _load_model(self):
        """Lazy load the pyannote model."""
        if self._model is None:
            try:
                from pyannote.audio import Model, Inference
                import os
                
                logger.info("Loading pyannote embedding model...")
                auth_token = os.getenv("HUGGINGFACE_TOKEN")
                
                if auth_token:
                    self._model = Model.from_pretrained("pyannote/embedding", 
                                                      use_auth_token=auth_token)
                    self._inference = Inference(self._model, window="whole")
                    logger.info("Pyannote model loaded successfully")
                else:
                    logger.error("HUGGINGFACE_TOKEN not set, falling back to simple comparison")
                    
            except Exception as e:
                logger.error(f"Failed to load pyannote model: {e}")
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
            # For simple comparison without model (faster but less accurate)
            if self._model is None:
                # Try to load model
                try:
                    self._load_model()
                except:
                    # Fallback: use simple comparison without model
                    logger.warning("Using fallback comparison method")
                    
                    # For now, without the model, we'll be conservative
                    # and allow all audio through (is_user=False)
                    # This ensures the app works even without HuggingFace token
                    logger.info("Fallback mode: allowing audio through (no model)")
                    return False, 0.0
            
            # Use real pyannote model if available
            if isinstance(audio, np.ndarray):
                audio = torch.from_numpy(audio).float()
            
            if audio.dim() == 1:
                audio = audio.unsqueeze(0)
            
            # Generate embedding
            with torch.no_grad():
                embedding = self._inference({"waveform": audio, "sample_rate": sample_rate})
            
            # Convert to numpy
            if isinstance(embedding, torch.Tensor):
                embedding = embedding.cpu().numpy()
            else:
                embedding = np.array(embedding)
            
            # Flatten if needed
            if embedding.ndim > 1:
                embedding = embedding.flatten()
            
            # Calculate similarity
            similarity = 1 - cosine(embedding, self.reference_embedding)
            
            # Make decision
            is_user = similarity >= self.similarity_threshold
            
            logger.debug(f"[VOICE_FILTER] Similarity: {similarity:.3f}, Is user: {is_user}")
            
            return is_user, similarity
            
        except Exception as e:
            logger.error(f"Error in voice filtering: {e}")
            # On error, allow audio through (don't filter)
            return False, 0.0
    
    def update_threshold(self, new_threshold: float):
        """Update the similarity threshold."""
        self.similarity_threshold = new_threshold
        logger.info(f"Updated similarity threshold to {new_threshold}")
    
    def get_stats(self) -> dict:
        """Get statistics about the voice filter."""
        return {
            "profile_loaded": self.reference_embedding is not None,
            "similarity_threshold": self.similarity_threshold,
            "model_loaded": self._model is not None
        }