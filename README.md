# Note Detector

A command-line tool for detecting and analyzing musical notes in audio files.

## Description

Note Detector is a Python application that processes audio files (WAV format) to identify musical notes. It can analyze recordings of instruments, vocals, or any tonal audio to identify the predominant notes and their frequencies. The tool can also play reference tones for comparison.

## Features

- Detect predominant musical notes in audio files
- Convert frequencies to standard musical notation (e.g., A4, C#5)
- Play detected notes or reference tones
- Process multiple audio files at once
- Option to output only the note names

## Installation

### Prerequisites

The following Python packages are required:

```
numpy
librosa
sounddevice
```

### Install Dependencies

```bash
pip install numpy librosa sounddevice
```

## Usage

```bash
python note-detector.py [options] path/to/file.wav|path/to/directory [more_paths ...]
```

### Options

- `--notes-only`: Output just the note names without additional information
- `--play`: Play each detected note after analysis
- `--play-file`: Play the original audio file before analysis

### Examples

Analyze a single audio file:
```bash
python note-detector.py sample.wav
```

Analyze all WAV files in a directory:
```bash
python note-detector.py path/to/samples/
```

Analyze multiple files and directories:
```bash
python note-detector.py --notes-only sample1.wav sample_directory/ sample2.wav
```

Analyze files with audio playback:
```bash
python note-detector.py --play --play-file sample.wav
```

## How It Works

The tool uses the librosa library to perform spectral analysis on audio files. It identifies the predominant frequencies in the audio, maps those frequencies to musical notes using the equal-tempered scale, and displays the results in a user-friendly format.

