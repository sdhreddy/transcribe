#!/usr/bin/env python
"""Voice threshold tuning and analysis tool.

This script helps find the optimal threshold for voice discrimination
by testing various thresholds against your voice recordings.
"""

import os
import sys
import numpy as np
import logging
from pathlib import Path
from datetime import datetime
import matplotlib.pyplot as plt
from scipy.spatial.distance import cosine

# Add parent directories to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))
from app.transcribe.voice_filter import VoiceFilter

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class VoiceThresholdTuner:
    """Tool for tuning voice discrimination threshold."""
    
    def __init__(self, voice_recordings_dir="voice_recordings"):
        self.voice_recordings_dir = Path(voice_recordings_dir)
        self.voice_filter = VoiceFilter()
        self.results = []
        
    def analyze_all_files(self):
        """Analyze all voice files and calculate distances."""
        if not self.voice_recordings_dir.exists():
            logger.error(f"Voice recordings directory not found: {self.voice_recordings_dir}")
            return
        
        # Find all audio files
        audio_files = []
        for ext in ['*.wav', '*.mp3', '*.m4a']:
            audio_files.extend(self.voice_recordings_dir.glob(ext))
        
        if not audio_files:
            logger.error("No audio files found")
            return
        
        logger.info(f"Analyzing {len(audio_files)} audio files...")
        
        if self.voice_filter.user_embedding is None:
            logger.error("No user voice profile loaded!")
            return
        
        # Analyze each file
        for audio_file in audio_files:
            try:
                logger.info(f"Processing: {audio_file.name}")
                
                # Extract embedding
                embedding = self.voice_filter.extract_embedding(str(audio_file))
                if embedding is None:
                    logger.error(f"Failed to extract embedding from {audio_file.name}")
                    continue
                
                # Calculate distance
                distance = cosine(self.voice_filter.user_embedding, embedding)
                
                # Determine if this is user's voice based on filename
                is_user_file = any(x in audio_file.name.lower() for x in ['user', 'me', 'my'])
                
                result = {
                    'file': audio_file.name,
                    'distance': distance,
                    'is_user_file': is_user_file,
                    'speaker_type': 'User' if is_user_file else 'Colleague'
                }
                self.results.append(result)
                
                logger.info(f"  Distance: {distance:.4f} ({result['speaker_type']})")
                
            except Exception as e:
                logger.error(f"Error processing {audio_file.name}: {e}")
    
    def find_optimal_threshold(self):
        """Find the optimal threshold that best separates user from colleagues."""
        if not self.results:
            logger.error("No results to analyze. Run analyze_all_files() first.")
            return None
        
        # Separate user and colleague distances
        user_distances = [r['distance'] for r in self.results if r['is_user_file']]
        colleague_distances = [r['distance'] for r in self.results if not r['is_user_file']]
        
        if not user_distances:
            logger.error("No user voice samples found")
            return None
        
        if not colleague_distances:
            logger.error("No colleague voice samples found")
            return None
        
        logger.info(f"\nUser voice distances: {user_distances}")
        logger.info(f"Colleague voice distances: {colleague_distances}")
        
        # Find threshold that maximizes separation
        min_colleague_dist = min(colleague_distances)
        max_user_dist = max(user_distances)
        
        if max_user_dist < min_colleague_dist:
            # Perfect separation possible
            optimal_threshold = (max_user_dist + min_colleague_dist) / 2
            logger.info(f"\nPerfect separation possible!")
            logger.info(f"User distances: {min(user_distances):.4f} - {max_user_dist:.4f}")
            logger.info(f"Colleague distances: {min_colleague_dist:.4f} - {max(colleague_distances):.4f}")
        else:
            # Overlap exists, find best threshold
            logger.warning("\nOverlap detected between user and colleague voices")
            
            # Test different thresholds
            thresholds = np.linspace(0.1, 0.5, 50)
            best_accuracy = 0
            optimal_threshold = 0.25
            
            for threshold in thresholds:
                correct = 0
                total = len(self.results)
                
                for result in self.results:
                    is_user = result['distance'] < threshold
                    if (is_user and result['is_user_file']) or (not is_user and not result['is_user_file']):
                        correct += 1
                
                accuracy = correct / total
                if accuracy > best_accuracy:
                    best_accuracy = accuracy
                    optimal_threshold = threshold
            
            logger.info(f"Best accuracy: {best_accuracy:.1%} at threshold {optimal_threshold:.3f}")
        
        return optimal_threshold
    
    def plot_analysis(self, save_path="voice_analysis.png"):
        """Create visualization of voice distances."""
        if not self.results:
            logger.error("No results to plot")
            return
        
        try:
            plt.figure(figsize=(12, 8))
            
            # Separate data
            user_data = [r for r in self.results if r['is_user_file']]
            colleague_data = [r for r in self.results if not r['is_user_file']]
            
            # Plot 1: Distance distribution
            plt.subplot(2, 1, 1)
            if user_data:
                user_dists = [r['distance'] for r in user_data]
                plt.scatter(range(len(user_dists)), user_dists, c='blue', label='User', s=100)
            
            if colleague_data:
                colleague_dists = [r['distance'] for r in colleague_data]
                offset = len(user_data) if user_data else 0
                plt.scatter(range(offset, offset + len(colleague_dists)), 
                          colleague_dists, c='red', label='Colleagues', s=100)
            
            # Add threshold line
            plt.axhline(y=self.voice_filter.threshold, color='green', linestyle='--', 
                       label=f'Current Threshold ({self.voice_filter.threshold})')
            
            # Find and plot optimal threshold
            optimal = self.find_optimal_threshold()
            if optimal:
                plt.axhline(y=optimal, color='orange', linestyle='--', 
                          label=f'Optimal Threshold ({optimal:.3f})')
            
            plt.xlabel('Sample Index')
            plt.ylabel('Cosine Distance')
            plt.title('Voice Distance Analysis')
            plt.legend()
            plt.grid(True, alpha=0.3)
            
            # Plot 2: Histogram
            plt.subplot(2, 1, 2)
            if user_data:
                plt.hist([r['distance'] for r in user_data], bins=20, alpha=0.5, 
                        label='User', color='blue')
            if colleague_data:
                plt.hist([r['distance'] for r in colleague_data], bins=20, alpha=0.5, 
                        label='Colleagues', color='red')
            
            plt.axvline(x=self.voice_filter.threshold, color='green', linestyle='--')
            if optimal:
                plt.axvline(x=optimal, color='orange', linestyle='--')
            
            plt.xlabel('Cosine Distance')
            plt.ylabel('Frequency')
            plt.title('Distance Distribution')
            plt.legend()
            plt.grid(True, alpha=0.3)
            
            plt.tight_layout()
            plt.savefig(save_path, dpi=150)
            logger.info(f"\nAnalysis plot saved to: {save_path}")
            
            # Also try to display
            plt.show()
            
        except Exception as e:
            logger.error(f"Error creating plot: {e}")
    
    def generate_report(self):
        """Generate a detailed analysis report."""
        if not self.results:
            logger.error("No results to report")
            return
        
        print("\n" + "="*80)
        print("VOICE DISCRIMINATION ANALYSIS REPORT")
        print("="*80)
        print(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"Current threshold: {self.voice_filter.threshold}")
        print(f"Total files analyzed: {len(self.results)}")
        
        # Statistics
        user_results = [r for r in self.results if r['is_user_file']]
        colleague_results = [r for r in self.results if not r['is_user_file']]
        
        print(f"\nUser voice samples: {len(user_results)}")
        print(f"Colleague voice samples: {len(colleague_results)}")
        
        if user_results:
            user_dists = [r['distance'] for r in user_results]
            print(f"\nUser voice statistics:")
            print(f"  Min distance: {min(user_dists):.4f}")
            print(f"  Max distance: {max(user_dists):.4f}")
            print(f"  Mean distance: {np.mean(user_dists):.4f}")
            print(f"  Std deviation: {np.std(user_dists):.4f}")
        
        if colleague_results:
            colleague_dists = [r['distance'] for r in colleague_results]
            print(f"\nColleague voice statistics:")
            print(f"  Min distance: {min(colleague_dists):.4f}")
            print(f"  Max distance: {max(colleague_dists):.4f}")
            print(f"  Mean distance: {np.mean(colleague_dists):.4f}")
            print(f"  Std deviation: {np.std(colleague_dists):.4f}")
        
        # Current performance
        print(f"\nCurrent threshold performance ({self.voice_filter.threshold}):")
        correct = 0
        for r in self.results:
            is_user = r['distance'] < self.voice_filter.threshold
            should_respond = not is_user  # Inverted logic
            expected_respond = not r['is_user_file']
            if should_respond == expected_respond:
                correct += 1
        
        accuracy = correct / len(self.results) * 100
        print(f"  Accuracy: {accuracy:.1f}% ({correct}/{len(self.results)})")
        
        # Recommendations
        optimal = self.find_optimal_threshold()
        if optimal and optimal != self.voice_filter.threshold:
            print(f"\nRECOMMENDATION: Change threshold from {self.voice_filter.threshold} to {optimal:.3f}")
            
            # Calculate improvement
            new_correct = 0
            for r in self.results:
                is_user = r['distance'] < optimal
                should_respond = not is_user
                expected_respond = not r['is_user_file']
                if should_respond == expected_respond:
                    new_correct += 1
            
            new_accuracy = new_correct / len(self.results) * 100
            print(f"This would improve accuracy from {accuracy:.1f}% to {new_accuracy:.1f}%")
        
        # Detailed results
        print("\n" + "-"*80)
        print("DETAILED RESULTS")
        print("-"*80)
        print(f"{'File':<30} {'Distance':<10} {'Type':<10} {'Current':<10} {'Optimal':<10}")
        print("-"*80)
        
        for r in sorted(self.results, key=lambda x: x['distance']):
            is_user_current = r['distance'] < self.voice_filter.threshold
            is_user_optimal = r['distance'] < optimal if optimal else is_user_current
            
            current_correct = (is_user_current == r['is_user_file'])
            optimal_correct = (is_user_optimal == r['is_user_file'])
            
            print(f"{r['file']:<30} {r['distance']:<10.4f} {r['speaker_type']:<10} "
                  f"{'✓' if current_correct else '✗':<10} {'✓' if optimal_correct else '✗':<10}")


def main():
    """Main function."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Voice threshold tuning tool")
    parser.add_argument('--voice-dir', default='voice_recordings', 
                       help='Directory containing voice recordings')
    parser.add_argument('--plot', action='store_true', 
                       help='Generate visualization plot')
    parser.add_argument('--profile', default='my_voice.npy',
                       help='Voice profile file')
    
    args = parser.parse_args()
    
    # Check voice profile
    if not os.path.exists(args.profile):
        logger.error(f"Voice profile not found: {args.profile}")
        logger.info("Please run: python scripts/make_voiceprint.py --record")
        return
    
    # Create tuner
    tuner = VoiceThresholdTuner(args.voice_dir)
    
    # Analyze files
    tuner.analyze_all_files()
    
    # Generate report
    tuner.generate_report()
    
    # Create plot if requested
    if args.plot:
        tuner.plot_analysis()


if __name__ == "__main__":
    main()