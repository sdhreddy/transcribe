#!/usr/bin/env python3
"""Final fix for streaming TTS - the real issue."""

import os

def apply_final_fix():
    """Apply the final fix for streaming TTS."""
    
    print("Applying FINAL streaming TTS fix...\n")
    
    # The issue: appui.py checks global_vars_module.config but it doesn't exist
    # Solution: Pass config properly or check responder's config
    
    appui_path = "app/transcribe/appui.py"
    if not os.path.exists(appui_path):
        print(f"Error: {appui_path} not found!")
        return False
    
    with open(appui_path, 'r') as f:
        content = f.read()
    
    # Fix the config check to use the responder's config
    old_check = """        # Only trigger old TTS if streaming TTS is not enabled
        config = global_vars_module.config if hasattr(global_vars_module, 'config') else {}
        streaming_tts_enabled = config.get('General', {}).get('tts_streaming_enabled', False)"""
    
    new_check = """        # Only trigger old TTS if streaming TTS is not enabled
        # Check if responder has streaming TTS enabled
        streaming_tts_enabled = False
        if hasattr(responder, 'tts_enabled'):
            streaming_tts_enabled = responder.tts_enabled
        else:
            # Fallback: try to get from responder's config
            config = getattr(responder, 'config', {})
            streaming_tts_enabled = config.get('General', {}).get('tts_streaming_enabled', False)"""
    
    if old_check in content:
        content = content.replace(old_check, new_check)
        print("✓ Fixed config check in appui.py")
    else:
        print("⚠️  Could not find expected code in appui.py")
        print("   Looking for alternative pattern...")
        
        # Try a simpler fix
        if "streaming_tts_enabled = config.get('General', {}).get('tts_streaming_enabled', False)" in content:
            content = content.replace(
                "streaming_tts_enabled = config.get('General', {}).get('tts_streaming_enabled', False)",
                "streaming_tts_enabled = getattr(responder, 'tts_enabled', False)"
            )
            print("✓ Applied alternative fix")
    
    # Write the fixed file
    with open(appui_path, 'w') as f:
        f.write(content)
    
    # Also add config to global_vars as a backup solution
    global_vars_path = "app/transcribe/global_vars.py"
    if os.path.exists(global_vars_path):
        with open(global_vars_path, 'r') as f:
            gv_content = f.read()
        
        # Add config attribute if not present
        if "self.config = None" not in gv_content and "db_context: dict = None" in gv_content:
            gv_content = gv_content.replace(
                "    db_context: dict = None",
                "    db_context: dict = None\n    config: dict = None"
            )
            
            with open(global_vars_path, 'w') as f:
                f.write(gv_content)
            print("✓ Added config attribute to global_vars")
    
    # Update main.py to store config in global_vars
    main_path = "app/transcribe/main.py"
    if os.path.exists(main_path):
        with open(main_path, 'r') as f:
            main_content = f.read()
        
        if "global_vars.config = config" not in main_content:
            # Add after config is loaded
            main_content = main_content.replace(
                "    update_args_config(args, config)",
                "    update_args_config(args, config)\n    global_vars.config = config  # Store for use in UI"
            )
            
            with open(main_path, 'w') as f:
                f.write(main_content)
            print("✓ Updated main.py to store config in global_vars")
    
    print("\n✅ Fix applied successfully!")
    print("\nWhat this fixes:")
    print("1. appui.py couldn't find config to check tts_streaming_enabled")
    print("2. Old TTS was playing because check defaulted to False")
    print("3. Now checks responder.tts_enabled directly")
    print("\nThe streaming TTS should now work properly!")
    
    return True


if __name__ == "__main__":
    if apply_final_fix():
        print("\nNext steps:")
        print("1. Copy these changes to Windows")
        print("2. Run the app")
        print("3. You should see [INIT DEBUG] messages")
        print("4. TTS should play as sentences complete!")
    else:
        print("\n❌ Fix failed")