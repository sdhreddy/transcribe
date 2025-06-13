# Baseline Build - 99% Voice Filter Accuracy

## Build Information
- **Commit Hash**: b351446a00dcd8813d9da0c2eb65933520d818eb
- **Branch**: disc-clean
- **Date**: June 13, 2025
- **Voice Filter Accuracy**: 99% (blocks user voice, responds to colleagues)

## Key Configuration
- **Voice Filter Threshold**: 0.625
- **Inverted Logic**: True (AI responds only to colleagues)
- **Min Window**: 2.0 seconds

## Test Results
- Primary User: Correctly ignored (confidence ~0.4-0.6)
- Colleague voices: Correctly responded to (confidence ~0.0 to -0.05)

## Known Working Features
1. Voice discrimination with Pyannote embeddings
2. YAML boolean parsing fix
3. Duplicate transcript prevention
4. GPT request cancellation
5. Audio buffer for soft speech
6. Buffer management

## To Restore This Build
```bash
git checkout b351446a00dcd8813d9da0c2eb65933520d818eb
```

## Backup Instructions
1. Create a backup branch:
   ```bash
   git checkout -b baseline-99percent-accuracy b351446a00dcd8813d9da0c2eb65933520d818eb
   git push origin baseline-99percent-accuracy
   ```

2. Create a full backup:
   ```bash
   tar -czf transcribe-baseline-20250613.tar.gz --exclude=venv --exclude=.git .
   ```