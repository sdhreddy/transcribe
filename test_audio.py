import sys
  sys.path.append('sdk')
  import audio_recorder as ar
  inputs, outputs = ar.list_audio_devices()
  print(f'Input devices: {inputs}')
  print(f'Output devices: {outputs}')
