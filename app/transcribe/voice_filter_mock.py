#!/usr/bin/env python3
"""
Mock VoiceFilter for testing without real speaker embeddings.
This simulates speaker discrimination for development/testing.
"""

import numpy as np
import logging
from pathlib import Path
from typing import Tuple, Union
import torch

logger = logging.getLogger(__name__)

class MockVoiceFilter:
    """
    Mock voice filter that simulates speaker discrimination.
    Uses audio characteristics to simulate different speakers.
    """
    
    def __init__(self, 
                 profile_path: str = "my_voice.npy",
                 similarity_threshold: float = 0.75):
        """Initialize mock voice filter."""
        
        self.profile_path = Path(profile_path)
        self.similarity_threshold = similarity_threshold
        
        # Load or create mock embedding
        if self.profile_path.exists():
            self.reference_embedding = np.load(self.profile_path)
            logger.info(f"Loaded mock voice profile from {profile_path}")
        else:
            # Create one if it doesn't exist
            self.reference_embedding = np.random.randn(512)
            self.reference_embedding /= np.linalg.norm(self.reference_embedding)
            np.save(self.profile_path, self.reference_embedding)
            logger.info(f"Created mock voice profile at {profile_path}")
            
        logger.info("Using MockVoiceFilter for testing")
        logger.warning("This is for TESTING only - replace with real VoiceFilter for production")
        
    def is_user(self, audio: Union[np.ndarray, torch.Tensor], 
                sample_rate: int = 16000) -> Tuple[bool, float]:
        """
        Mock implementation that simulates speaker detection.
        Uses simple audio characteristics to differentiate speakers.
        """
        
        try:
            # Convert to numpy if needed
            if isinstance(audio, torch.Tensor):
                audio_np = audio.cpu().numpy()
            else:
                audio_np = audio
                
            # Flatten if needed
            if audio_np.ndim > 1:
                audio_np = audio_np.flatten()
                
            # Simulate speaker characteristics using audio features
            # This is a MOCK - real implementation uses proper embeddings
            
            # Feature 1: Average energy
            energy = np.sqrt(np.mean(audio_np**2))
            
            # Feature 2: Zero crossing rate (rough pitch indicator)
            zero_crossings = np.sum(np.diff(np.sign(audio_np)) != 0) / len(audio_np)
            
            # Feature 3: Spectral characteristics (simplified)
            # High energy + low zero crossings = deeper voice (mock "primary user")
            # Low energy + high zero crossings = higher voice (mock "colleague")
            
            # Create mock similarity score based on features
            # This is completely artificial but creates testable behavior
            if energy > 0.1 and zero_crossings < 0.3:
                # Characteristics of "primary user" (deeper voice)
                similarity = 0.85 + np.random.uniform(-0.05, 0.05)
            elif energy < 0.05:
                # Very quiet - uncertain
                similarity = 0.5 + np.random.uniform(-0.1, 0.1)
            else:
                # Different characteristics (colleague voices)
                similarity = 0.4 + np.random.uniform(-0.1, 0.1)
                
            # Ensure similarity is in valid range
            similarity = np.clip(similarity, 0.0, 1.0)
            
            # Make decision
            is_user = similarity >= self.similarity_threshold
            
            logger.debug(f"[MOCK] Energy: {energy:.3f}, ZCR: {zero_crossings:.3f}, "
                        f"Similarity: {similarity:.3f}, Is user: {is_user}")
            
            return is_user, similarity
            
        except Exception as e:
            logger.error(f"Error in mock voice filtering: {e}")
            # On error, allow audio through
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
            "model_loaded": True,
            "mock": True
        }

# For compatibility, create alias
VoiceFilter = MockVoiceFilter