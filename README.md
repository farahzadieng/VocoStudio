# VOCO

VOCO is a local, Persian web application for audio enhancement and processing. It is forked from [ClearVoice](https://github.com/modelscope/ClearerVoice-Studio) and provides a simpler interface for running its audio models.

Upload an audio file, choose a suitable model, and download the processed result.

## Features

- Speech enhancement and noise reduction
- Speech separation
- Speech restoration and super-resolution
- Target speaker extraction
- Simple model choices such as fast/lightweight or advanced
- Local operation on macOS, Apple Silicon, Windows, and CPU
- Uses pre-downloaded models from the `checkpoints/` directory
- Drag-and-drop upload and one-click output download

## Run locally

Install the dependencies:

```bash
uv sync
```
