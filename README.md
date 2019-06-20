﻿# Swear Removal

The Swear Removal project utilizes Google's Speech to Text API to find swear words in an audio file and replace it with silence.

## Usage in Python File

```python
from model.SwearRemovalModel import main

folder = "../temp_folder"
file_name = "trial_audio.wav"
main(file_name, folder)
```
