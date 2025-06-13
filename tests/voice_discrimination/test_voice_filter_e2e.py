#!/usr/bin/env python
"""End-to-end test suite for voice discrimination feature.

Tests voice filtering with real voice samples to ensure:
- User's voice is correctly identified and filtered (inverted logic)
- Colleagues' voices trigger AI responses
- Proper handling of different speakers (male/female)
"""

import os
import sys
import unittest
import logging
import numpy as np
import json
from pathlib import Path
from datetime import datetime

# Add parent directories to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../app/transcribe')))

from app.transcribe.voice_filter import VoiceFilter

# Configure logging
log_dir = Path(__file__).parent / "logs"
log_dir.mkdir(exist_ok=True)
log_file = log_dir / f"voice_test_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"

logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_file),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class VoiceDiscriminationTests(unittest.TestCase):
    """End-to-end tests for voice discrimination feature."""
    
    @classmethod
    def setUpClass(cls):
        """Set up test environment once for all tests."""
        cls.voice_recordings_dir = Path("voice_recordings")
        cls.test_results = {
            "test_time": datetime.now().isoformat(),
            "results": []
        }
        
        # Check if voice recordings directory exists
        if not cls.voice_recordings_dir.exists():
            logger.error(f"Voice recordings directory not found: {cls.voice_recordings_dir}")
            cls.voice_recordings_dir = None
    
    def setUp(self):
        """Set up for each test."""
        self.voice_filter = VoiceFilter()
        
    def test_01_voice_profile_exists(self):
        """Test that user's voice profile exists."""
        profile_path = "my_voice.npy"
        exists = os.path.exists(profile_path)
        
        result = {
            "test": "voice_profile_exists",
            "passed": exists,
            "profile_path": profile_path
        }
        self.test_results["results"].append(result)
        
        if not exists:
            logger.warning(f"Voice profile not found at {profile_path}")
            logger.info("Creating voice profile from Windows location...")
            # Try common Windows locations
            win_paths = [
                "C:/Users/sdhre/transcribe/my_voice.npy",
                "my_voice.npy",
                "app/transcribe/my_voice.npy"
            ]
            for path in win_paths:
                if os.path.exists(path):
                    logger.info(f"Found profile at {path}")
                    import shutil
                    shutil.copy(path, profile_path)
                    exists = True
                    break
        
        self.assertTrue(exists, "Voice profile my_voice.npy not found")
    
    def test_02_voice_filter_initialization(self):
        """Test voice filter initializes correctly."""
        self.assertIsNotNone(self.voice_filter, "Voice filter should be initialized")
        
        # Check if model is loaded
        has_model = self.voice_filter.inference is not None
        
        result = {
            "test": "voice_filter_initialization",
            "passed": has_model,
            "has_inference_model": has_model,
            "has_user_embedding": self.voice_filter.user_embedding is not None
        }
        self.test_results["results"].append(result)
        
        if not has_model:
            logger.error("Voice filter model not initialized. Check HuggingFace token.")
        
        self.assertTrue(has_model, "Voice filter model should be loaded")
    
    def test_03_test_voice_recordings(self):
        """Test voice discrimination with actual voice recordings."""
        if not self.voice_recordings_dir or not self.voice_recordings_dir.exists():
            self.skipTest("Voice recordings directory not found")
        
        # Find all audio files
        audio_files = list(self.voice_recordings_dir.glob("*.wav"))
        audio_files.extend(list(self.voice_recordings_dir.glob("*.mp3")))
        audio_files.extend(list(self.voice_recordings_dir.glob("*.m4a")))
        
        logger.info(f"Found {len(audio_files)} audio files to test")
        
        results = []
        for audio_file in audio_files:
            logger.info(f"\n{'='*60}")
            logger.info(f"Testing: {audio_file.name}")
            
            # Extract embedding
            try:
                embedding = self.voice_filter.extract_embedding(str(audio_file))
                if embedding is None:
                    logger.error(f"Failed to extract embedding from {audio_file.name}")
                    continue
                
                # Compare with user's voice
                if self.voice_filter.user_embedding is not None:
                    from scipy.spatial.distance import cosine
                    distance = cosine(self.voice_filter.user_embedding, embedding)
                    is_user = distance < self.voice_filter.threshold
                    should_respond = self.voice_filter.should_respond(is_user, inverted=True)
                    
                    result = {
                        "file": audio_file.name,
                        "distance": float(distance),
                        "threshold": self.voice_filter.threshold,
                        "is_user_voice": is_user,
                        "should_ai_respond": should_respond,
                        "verdict": "CORRECT" if self._is_expected_result(audio_file.name, should_respond) else "WRONG"
                    }
                    
                    results.append(result)
                    
                    logger.info(f"Distance: {distance:.4f} (threshold: {self.voice_filter.threshold})")
                    logger.info(f"Is user voice: {is_user}")
                    logger.info(f"Should AI respond: {should_respond}")
                    logger.info(f"Verdict: {result['verdict']}")
                    
                else:
                    logger.error("No user embedding loaded")
                    
            except Exception as e:
                logger.error(f"Error processing {audio_file.name}: {e}")
                results.append({
                    "file": audio_file.name,
                    "error": str(e),
                    "verdict": "ERROR"
                })
        
        # Summary
        test_result = {
            "test": "voice_recordings_discrimination",
            "total_files": len(audio_files),
            "processed": len(results),
            "details": results
        }
        self.test_results["results"].append(test_result)
        
        # Count correct vs wrong
        correct = sum(1 for r in results if r.get("verdict") == "CORRECT")
        wrong = sum(1 for r in results if r.get("verdict") == "WRONG")
        errors = sum(1 for r in results if r.get("verdict") == "ERROR")
        
        logger.info(f"\n{'='*60}")
        logger.info(f"SUMMARY: Correct: {correct}, Wrong: {wrong}, Errors: {errors}")
        
        # At least 75% should be correct
        if len(results) > 0:
            accuracy = correct / len(results)
            logger.info(f"Accuracy: {accuracy:.1%}")
            self.assertGreaterEqual(accuracy, 0.75, f"Accuracy {accuracy:.1%} is below 75%")
    
    def test_04_threshold_analysis(self):
        """Analyze optimal threshold for voice discrimination."""
        if not self.voice_recordings_dir or not self.voice_recordings_dir.exists():
            self.skipTest("Voice recordings directory not found")
        
        audio_files = list(self.voice_recordings_dir.glob("*.wav"))
        thresholds = [0.15, 0.20, 0.25, 0.30, 0.35, 0.40]
        
        logger.info("\nThreshold Analysis:")
        logger.info("="*80)
        
        analysis_results = []
        
        for threshold in thresholds:
            self.voice_filter.threshold = threshold
            correct_count = 0
            total_count = 0
            
            for audio_file in audio_files:
                try:
                    embedding = self.voice_filter.extract_embedding(str(audio_file))
                    if embedding is not None and self.voice_filter.user_embedding is not None:
                        from scipy.spatial.distance import cosine
                        distance = cosine(self.voice_filter.user_embedding, embedding)
                        is_user = distance < threshold
                        should_respond = not is_user  # Inverted logic
                        
                        expected = self._is_expected_result(audio_file.name, should_respond)
                        if expected:
                            correct_count += 1
                        total_count += 1
                        
                except Exception as e:
                    logger.error(f"Error with {audio_file.name}: {e}")
            
            if total_count > 0:
                accuracy = correct_count / total_count
                analysis_results.append({
                    "threshold": threshold,
                    "accuracy": accuracy,
                    "correct": correct_count,
                    "total": total_count
                })
                logger.info(f"Threshold {threshold:.2f}: {accuracy:.1%} ({correct_count}/{total_count})")
        
        # Find optimal threshold
        if analysis_results:
            optimal = max(analysis_results, key=lambda x: x["accuracy"])
            logger.info(f"\nOptimal threshold: {optimal['threshold']:.2f} with {optimal['accuracy']:.1%} accuracy")
            
            test_result = {
                "test": "threshold_analysis",
                "thresholds_tested": thresholds,
                "results": analysis_results,
                "optimal_threshold": optimal['threshold']
            }
            self.test_results["results"].append(test_result)
    
    def _is_expected_result(self, filename: str, should_respond: bool) -> bool:
        """Determine if the result matches expected behavior."""
        # Assume files with "user" or "me" in name are user's voice
        # All others are colleagues
        filename_lower = filename.lower()
        is_user_file = "user" in filename_lower or "me" in filename_lower or "my" in filename_lower
        
        # With inverted logic:
        # - User files should NOT trigger response (should_respond = False)
        # - Colleague files SHOULD trigger response (should_respond = True)
        expected = not is_user_file
        
        return should_respond == expected
    
    @classmethod
    def tearDownClass(cls):
        """Save test results after all tests."""
        results_file = Path(__file__).parent / "logs" / "test_results.json"
        with open(results_file, 'w') as f:
            json.dump(cls.test_results, f, indent=2)
        logger.info(f"\nTest results saved to: {results_file}")


def run_diagnostic_test():
    """Run a quick diagnostic test of voice filter."""
    logger.info("\n" + "="*80)
    logger.info("VOICE FILTER DIAGNOSTIC TEST")
    logger.info("="*80)
    
    vf = VoiceFilter()
    
    # Check HF token
    token = vf._get_hf_token()
    logger.info(f"HuggingFace token found: {'Yes' if token else 'No'}")
    
    # Check model
    logger.info(f"Model loaded: {'Yes' if vf.inference else 'No'}")
    
    # Check profile
    logger.info(f"Voice profile loaded: {'Yes' if vf.user_embedding is not None else 'No'}")
    if vf.user_embedding is not None:
        logger.info(f"Embedding shape: {vf.user_embedding.shape}")
    
    # Check threshold
    logger.info(f"Threshold: {vf.threshold}")
    
    logger.info("="*80 + "\n")


if __name__ == "__main__":
    # Run diagnostic first
    run_diagnostic_test()
    
    # Run tests
    unittest.main(verbosity=2)