#!/usr/bin/env python
"""Test runner for voice discrimination tests.

This script runs all voice discrimination tests and generates reports.
"""

import os
import sys
import subprocess
import json
from pathlib import Path
from datetime import datetime
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(message)s'
)
logger = logging.getLogger(__name__)


def ensure_dependencies():
    """Check and install required dependencies."""
    required = ['pyannote.audio', 'speechbrain', 'scipy']
    missing = []
    
    for package in required:
        try:
            __import__(package.replace('.', '_'))
        except ImportError:
            missing.append(package)
    
    if missing:
        logger.info(f"Installing missing dependencies: {missing}")
        subprocess.check_call([sys.executable, '-m', 'pip', 'install'] + missing)


def run_tests():
    """Run all voice discrimination tests."""
    logger.info("="*80)
    logger.info("VOICE DISCRIMINATION TEST SUITE")
    logger.info("="*80)
    
    # Ensure test logs directory exists
    log_dir = Path(__file__).parent / "logs"
    log_dir.mkdir(exist_ok=True)
    
    # Check for voice profile
    if not os.path.exists("my_voice.npy"):
        logger.warning("Voice profile my_voice.npy not found!")
        logger.info("Please run: python scripts/make_voiceprint.py --record")
        return False
    
    # Check for voice recordings
    voice_dir = Path("voice_recordings")
    if not voice_dir.exists():
        logger.warning(f"Voice recordings directory not found: {voice_dir}")
        logger.info("Please create 'voice_recordings' folder with test audio files")
        return False
    
    audio_files = list(voice_dir.glob("*.wav"))
    audio_files.extend(list(voice_dir.glob("*.mp3")))
    audio_files.extend(list(voice_dir.glob("*.m4a")))
    
    if not audio_files:
        logger.warning("No audio files found in voice_recordings directory")
        return False
    
    logger.info(f"Found {len(audio_files)} audio files")
    logger.info("Files: " + ", ".join(f.name for f in audio_files))
    
    # Run the test suite
    test_file = Path(__file__).parent / "test_voice_filter_e2e.py"
    cmd = [sys.executable, str(test_file)]
    
    logger.info("\nRunning tests...")
    result = subprocess.run(cmd, capture_output=True, text=True)
    
    # Print output
    print(result.stdout)
    if result.stderr:
        print("ERRORS:", result.stderr)
    
    # Load and display results
    results_file = log_dir / "test_results.json"
    if results_file.exists():
        with open(results_file) as f:
            results = json.load(f)
        
        logger.info("\n" + "="*80)
        logger.info("TEST SUMMARY")
        logger.info("="*80)
        
        for test_result in results.get("results", []):
            test_name = test_result.get("test", "Unknown")
            logger.info(f"\nTest: {test_name}")
            
            if test_name == "voice_recordings_discrimination":
                details = test_result.get("details", [])
                correct = sum(1 for d in details if d.get("verdict") == "CORRECT")
                wrong = sum(1 for d in details if d.get("verdict") == "WRONG")
                errors = sum(1 for d in details if d.get("verdict") == "ERROR")
                
                logger.info(f"Files tested: {test_result.get('total_files', 0)}")
                logger.info(f"Correct: {correct}")
                logger.info(f"Wrong: {wrong}")
                logger.info(f"Errors: {errors}")
                
                if details:
                    accuracy = correct / len(details) * 100
                    logger.info(f"Accuracy: {accuracy:.1f}%")
                
                # Show details for wrong predictions
                if wrong > 0:
                    logger.info("\nIncorrect predictions:")
                    for d in details:
                        if d.get("verdict") == "WRONG":
                            logger.info(f"  - {d['file']}: distance={d['distance']:.3f}, "
                                      f"should_respond={d['should_ai_respond']}")
            
            elif test_name == "threshold_analysis":
                optimal = test_result.get("optimal_threshold")
                logger.info(f"Optimal threshold: {optimal}")
                
                logger.info("\nThreshold analysis:")
                for r in test_result.get("results", []):
                    logger.info(f"  Threshold {r['threshold']:.2f}: {r['accuracy']:.1%}")
    
    return result.returncode == 0


def generate_report():
    """Generate a detailed HTML report."""
    log_dir = Path(__file__).parent / "logs"
    results_file = log_dir / "test_results.json"
    
    if not results_file.exists():
        logger.warning("No test results found")
        return
    
    with open(results_file) as f:
        results = json.load(f)
    
    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Voice Discrimination Test Report</title>
        <style>
            body {{ font-family: Arial, sans-serif; margin: 20px; }}
            .pass {{ color: green; }}
            .fail {{ color: red; }}
            .warn {{ color: orange; }}
            table {{ border-collapse: collapse; width: 100%; margin: 20px 0; }}
            th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
            th {{ background-color: #f2f2f2; }}
            .summary {{ background-color: #f0f0f0; padding: 10px; margin: 10px 0; }}
        </style>
    </head>
    <body>
        <h1>Voice Discrimination Test Report</h1>
        <p>Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
    """
    
    for test_result in results.get("results", []):
        test_name = test_result.get("test", "Unknown")
        html += f"<h2>{test_name}</h2>"
        
        if test_name == "voice_recordings_discrimination":
            details = test_result.get("details", [])
            if details:
                html += "<table>"
                html += "<tr><th>File</th><th>Distance</th><th>Is User</th><th>Should Respond</th><th>Result</th></tr>"
                
                for d in details:
                    if "error" in d:
                        html += f"<tr><td>{d['file']}</td><td colspan='4' class='fail'>Error: {d['error']}</td></tr>"
                    else:
                        result_class = "pass" if d['verdict'] == "CORRECT" else "fail"
                        html += f"""<tr>
                            <td>{d['file']}</td>
                            <td>{d['distance']:.4f}</td>
                            <td>{d['is_user_voice']}</td>
                            <td>{d['should_ai_respond']}</td>
                            <td class='{result_class}'>{d['verdict']}</td>
                        </tr>"""
                
                html += "</table>"
    
    html += "</body></html>"
    
    report_file = log_dir / f"report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html"
    with open(report_file, 'w') as f:
        f.write(html)
    
    logger.info(f"\nReport generated: {report_file}")
    
    # Try to open in browser
    try:
        import webbrowser
        webbrowser.open(f"file://{report_file.absolute()}")
    except:
        pass


if __name__ == "__main__":
    logger.info("Voice Discrimination Test Runner")
    logger.info(f"Working directory: {os.getcwd()}")
    
    # Ensure dependencies
    ensure_dependencies()
    
    # Run tests
    success = run_tests()
    
    # Generate report
    generate_report()
    
    sys.exit(0 if success else 1)