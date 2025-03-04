import argparse
import math
import os
import platform
import re
import subprocess
import sys

import librosa
import numpy as np
import sounddevice as sd

GREEN = "\033[92m"
RED = "\033[91m"
RESET = "\033[0m"


def play_wav(path):
    system = platform.system().lower()
    try:
        if system == "darwin":  # macOS
            subprocess.run(["afplay", path])
        elif system == "windows":
            # Use PowerShell to play audio on Windows
            subprocess.run(
                [
                    "powershell",
                    "-c",
                    f"(New-Object Media.SoundPlayer '{path}').PlaySync()",
                ]
            )
        elif system == "linux":
            # Try different Linux audio players
            for cmd in ["aplay", "paplay", "play"]:
                try:
                    subprocess.run([cmd, path], stderr=subprocess.DEVNULL)
                    break
                except FileNotFoundError:
                    continue
            else:
                # If all commands fail, try using sounddevice as fallback
                y, sr = librosa.load(path, sr=None)
                sd.play(y, sr)
                sd.wait()
        else:
            # Unknown OS, try using sounddevice as fallback
            y, sr = librosa.load(path, sr=None)
            sd.play(y, sr)
            sd.wait()
    except Exception as e:
        print(f"Error playing audio: {e}")
        # Try fallback to sounddevice if primary method fails
        try:
            y, sr = librosa.load(path, sr=None)
            sd.play(y, sr)
            sd.wait()
        except Exception as e2:
            print(f"Fallback audio playback failed: {e2}")


def play_tone(freq, duration=2, sr=44100, amp=0.5):
    t = np.linspace(0, duration, int(sr * duration), endpoint=False)
    tone = amp * np.sin(2 * np.pi * freq * t)
    sd.play(tone, sr)
    sd.wait()


def freq_to_note_name(freq):
    midi = int(round(69 + 12 * math.log2(freq / 440.0)))
    notes = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]
    return notes[midi % 12] + str((midi // 12) - 1)


def note_letter(note):
    m = re.match(r"([A-G][#b]?)(\d+)", note)
    return m.group(1) if m else note


def process_file(path, notes_only_flag, play_file=False, play_detected=False):
    base = os.path.basename(path)
    m = re.search(r"-([A-G][#b]?\d)\.wav$", base, re.IGNORECASE)
    if not m:
        print(f"Skipping (no expected note): {path}")
        return
    expected = m.group(1).upper()
    print(f"Processing {path} (expected: {expected})")

    if play_file:
        print("Playing original audio file...")
        play_wav(path)

    try:
        y, sr = librosa.load(path, sr=None)
        f0, _, _ = librosa.pyin(
            y,
            fmin=float(librosa.note_to_hz("C2")),
            fmax=float(librosa.note_to_hz("C7")),
        )
    except Exception as e:
        print(RED + f"Error processing {path}: {e}" + RESET)
        return
    valid = f0[~np.isnan(f0)]
    if len(valid) == 0:
        detected_freq = 0
        detected_note = "None"
    else:
        detected_freq = np.median(valid)
        try:
            detected_note = freq_to_note_name(detected_freq)
        except Exception:
            detected_note = "Error"

    # Play the detected note if requested
    if play_detected and detected_freq > 0:
        print(f"Playing detected note {detected_note} at {detected_freq:.2f}Hz...")
        play_tone(detected_freq, duration=1)

    # Determine if mismatch is solely an octave difference.
    octave_only = False
    if detected_note.upper() != expected.upper():
        if note_letter(detected_note) == note_letter(expected):
            octave_only = True

    if detected_note.upper() == expected.upper():
        print(
            GREEN + f"Match: {base} -> {detected_note} at {detected_freq:.2f}Hz" + RESET
        )
        return
    elif octave_only and notes_only_flag:
        # If --notes-only is set and the mismatch is only an octave difference, skip review.
        print(
            GREEN
            + f"Octave-only mismatch (skipped review): {base} (expected {expected}, detected {detected_note})"
            + RESET
        )
        return
    elif octave_only:
        print(
            GREEN
            + f"Octave-only mismatch: {base} (expected {expected}, detected {detected_note})"
            + RESET
        )
    else:
        print(
            RED
            + f"Mismatch: {base} (expected {expected}, detected {detected_note} at {detected_freq:.2f}Hz)"
            + RESET
        )

    input("Press spacebar (then Enter) to review mismatch...")

    print("Playing original WAV file...")
    play_wav(path)
    try:
        expected_freq = librosa.note_to_hz(expected)
        print(
            f"Playing 2-second tone at expected frequency {expected_freq:.2f} Hz (expected note: {expected})..."
        )
        play_tone(expected_freq, duration=2)
    except Exception as e:
        print("Could not play expected tone:", e)
    print("Replaying original WAV file...")
    play_wav(path)
    if detected_freq > 0:
        print(
            f"Playing 2-second tone at detected frequency {detected_freq:.2f} Hz (detected note: {detected_note})..."
        )
        play_tone(detected_freq, duration=2)
    else:
        print("No valid detected frequency; skipping tone playback.")

    options = "[k]eep, [r]ename to detected note, [m]anually input"
    if not octave_only:
        options += ", [f]lag for review"
    options += ": "

    while True:
        choice = input("Choose action " + options).strip().lower()
        if choice == "k":
            print("Keeping filename as-is.")
            break
        elif choice == "r":
            new_note = detected_note
            new_base = re.sub(
                r"-([A-G][#b]?\d)(\.wav)$", f"-{new_note}\\2", base, flags=re.IGNORECASE
            )
            new_path = os.path.join(os.path.dirname(path), new_base)
            try:
                os.rename(path, new_path)
                print(GREEN + f"Renamed file to: {new_path}" + RESET)
            except Exception as e:
                print(RED + f"Error renaming file: {e}" + RESET)
            break
        elif choice == "m":
            manual_note = input("Enter correct note (e.g., A4): ").strip().upper()
            if re.match(r"^[A-G][#b]?\d$", manual_note):
                new_base = re.sub(
                    r"-([A-G][#b]?\d)(\.wav)$",
                    f"-{manual_note}\\2",
                    base,
                    flags=re.IGNORECASE,
                )
                new_path = os.path.join(os.path.dirname(path), new_base)
                try:
                    os.rename(path, new_path)
                    print(GREEN + f"Renamed file to: {new_path}" + RESET)
                except Exception as e:
                    print(RED + f"Error renaming file: {e}" + RESET)
                break
            else:
                print("Invalid note format. Try again.")
        elif choice == "f" and not octave_only:
            if not base.startswith("_"):
                new_base = "_" + base
                new_path = os.path.join(os.path.dirname(path), new_base)
                try:
                    os.rename(path, new_path)
                    print(RED + f"Flagged file for review: {new_path}" + RESET)
                except Exception as e:
                    print(RED + f"Error renaming file: {e}" + RESET)
            else:
                print("File is already flagged for review.")
            break
        else:
            print("Invalid choice. Please enter one of the offered options.")


def main():
    parser = argparse.ArgumentParser(
        description="Review WAV files for pitch mismatches."
    )
    parser.add_argument(
        "--notes-only",
        action="store_true",
        help="Skip interactive review for octave-only mismatches",
    )
    parser.add_argument(
        "--play", action="store_true", help="Play each detected note after analysis"
    )
    parser.add_argument(
        "--play-file",
        action="store_true",
        help="Play the original audio file before analysis",
    )
    parser.add_argument("paths", nargs="+", help="Files or directories to process")
    args = parser.parse_args()

    candidate_files = []

    # Process each path (file or directory)
    for path in args.paths:
        if os.path.isdir(path):
            # If path is a directory, find all .wav files in it
            print(f"Scanning directory: {path}")
            for root, _, files in os.walk(path):
                for file in files:
                    if file.lower().endswith(".wav") and "fx" not in file.lower():
                        candidate_files.append(os.path.join(root, file))
        elif os.path.isfile(path) and path.lower().endswith(".wav"):
            # If path is a .wav file, add it directly
            candidate_files.append(path)
        else:
            print(f"Skipping {path}: Not a valid directory or .wav file")

    total = len(candidate_files)
    if total == 0:
        print("No candidate WAV files found.")
        return
    print(f"Found {total} candidate files.")
    count = 0
    for path in candidate_files:
        count += 1
        percent = (count / total) * 100
        print(f"\nProcessing file {count} of {total} ({percent:.1f}% complete)")
        process_file(path, args.notes_only, args.play_file, args.play)


if __name__ == "__main__":
    main()
