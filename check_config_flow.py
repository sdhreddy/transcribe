#!/usr/bin/env python3
"""Check how config flows to GPTResponder."""

import os
import sys
import yaml

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def check_config_loading():
    """Check how config is loaded in the app."""
    print("=== Config Flow Check ===\n")
    
    # 1. Load config the same way the app does
    print("1. Loading parameters.yaml...")
    try:
        from app.transcribe import configuration
        
        # This is how the app loads config
        config = configuration.Config().get_data()
        
        general = config.get('General', {})
        print("   Config loaded successfully")
        print(f"   tts_streaming_enabled: {general.get('tts_streaming_enabled')}")
        print(f"   tts_provider: {general.get('tts_provider')}")
        print(f"   continuous_read: {general.get('continuous_read')}")
        
    except Exception as e:
        print(f"   Error loading config: {e}")
        return False
    
    # 2. Check how responder would be created
    print("\n2. Checking responder creation...")
    try:
        from app.transcribe.gpt_responder import OpenAIResponder
        from app.transcribe.conversation import Conversation
        
        # Dummy conversation
        class DummyGlobals:
            pass
        
        dummy_globals = DummyGlobals()
        convo = Conversation(dummy_globals)
        
        print("   Creating OpenAIResponder with config...")
        
        # Temporarily capture logs
        import logging
        import io
        log_capture = io.StringIO()
        handler = logging.StreamHandler(log_capture)
        handler.setLevel(logging.INFO)
        
        # Get the logger
        logger = logging.getLogger('tsutils.app_logging.gpt_responder')
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)
        
        # Create responder (this should trigger our debug logs)
        responder = OpenAIResponder(
            config=config,
            convo=convo,
            response_file_name="test.txt",
            save_to_file=False
        )
        
        # Get captured logs
        log_contents = log_capture.getvalue()
        logger.removeHandler(handler)
        
        print("\n3. Captured initialization logs:")
        if log_contents:
            print(log_contents)
        else:
            print("   No logs captured - logging might not be configured")
        
        # Check responder state
        print("\n4. Responder state:")
        print(f"   tts_enabled: {getattr(responder, 'tts_enabled', 'NOT SET')}")
        print(f"   Has tts attribute: {hasattr(responder, 'tts')}")
        print(f"   Has player attribute: {hasattr(responder, 'player')}")
        print(f"   Has sent_q attribute: {hasattr(responder, 'sent_q')}")
        
        return True
        
    except Exception as e:
        print(f"   Error creating responder: {e}")
        import traceback
        traceback.print_exc()
        return False


def check_logging_setup():
    """Check if logging is configured."""
    print("\n\n=== Logging Configuration Check ===\n")
    
    try:
        from tsutils import app_logging
        
        # Check if logger exists
        logger = app_logging.get_module_logger('gpt_responder')
        print(f"1. Logger exists: {logger is not None}")
        print(f"2. Logger level: {logger.level}")
        print(f"3. Logger has handlers: {len(logger.handlers) > 0}")
        
        # Try to log something
        print("\n4. Testing log output...")
        logger.info("[TEST] This is a test log message")
        
    except Exception as e:
        print(f"Error checking logging: {e}")


if __name__ == "__main__":
    check_config_loading()
    check_logging_setup()
    
    print("\n" + "="*50)
    print("\nKey findings:")
    print("- If tts_enabled is False, streaming TTS is not initializing")
    print("- If no logs are captured, logging might be misconfigured")
    print("- Check if the app's logging is set to INFO level")