"""Wires the audio pipeline and rendering engine together and runs the app.

ENGINE and AUDIO_FILE are fixed, version-controlled choices, not runtime
options — committing to one engine tier and one audio file is a project
decision, not something to toggle per run.
"""

from collections.abc import Callable
import numpy as np
from audio.pipeline import AudioPipeline
from engines.base_engine import BaseEngine
from engines.pyglet_engine import PygletEngine


# Set this to whichever engine tier your project uses. See the README for
# how/why this is a one-time project decision, not a runtime toggle.
ENGINE: type[BaseEngine] = PygletEngine

AUDIO_FILE = "audio/audio (3).mp3"
WINDOW_WIDTH = 1280
WINDOW_HEIGHT = 720
WINDOW_TITLE = "CLASS-2a Project"
TARGET_FPS = 60


def run_engine_only() -> None:
    """Runs the chosen engine with no audio pipeline involved.

    Optional helper for checking your engine in isolation — run_full_app()
    already falls back to a blank feature source until AudioPipeline is
    implemented, so you don't need this to get started.
    """
    engine = ENGINE(width=WINDOW_WIDTH, height=WINDOW_HEIGHT, title=WINDOW_TITLE, target_fps=TARGET_FPS)
    engine.run(feature_source=lambda: {})


NOT_IMPLEMENTED_MESSAGE = "AudioPipeline not implemented yet -- running with a blank feature source."


def tolerate_not_implemented(get_features: Callable[[], dict]) -> Callable[[], dict]:
    """Wraps get_features so a NotImplementedError yields {} for that frame.

    The message is printed once, not every frame. Only NotImplementedError is
    caught — any other exception (e.g. running off the end of the audio)
    still propagates so you can see it.
    """
    warned = False

    def feature_source() -> dict:
        nonlocal warned
        try:
            return get_features()
        except NotImplementedError:
            if not warned:
                print(NOT_IMPLEMENTED_MESSAGE)
                warned = True
            return {}

    return feature_source


def run_full_app():
    engine = ENGINE(width=WINDOW_WIDTH, height=WINDOW_HEIGHT, title=WINDOW_TITLE, target_fps=TARGET_FPS)

    pipeline = AudioPipeline(file_path=AUDIO_FILE)
    feature_source = tolerate_not_implemented(pipeline.get_features)
    try:
        signal = pipeline.load()
        print(signal)
        print(f"Loaded signal with {len(signal)} samples at {pipeline.sample_rate} Hz.") # type: ignore
        pipeline.get_features()  # type: ignore
        pipeline.get_tempo()  # type: ignore
        pipeline.get_peak()  # type: ignore
        pipeline.get_rms()  # type: ignore
        pipeline.get_window()  # type: ignore
        print("Signal length:", len(signal))  # type: ignore
        print("Mean_amplitude", amplitude := pipeline.get_features()["Mean_amplitude"])  # type: ignore
        print("Highest_amplitude", highest_amplitude := pipeline.get_features()["Highest_amplitude"])  # type: ignore
        print("Lowest_amplitude", lowest_amplitude := pipeline.get_features()["Lowest_amplitude"])  # type: ignore
        duration = len(signal) / pipeline.sample_rate # type: ignore
        print(f"Duration: {duration:.2f} seconds")  # type: ignore
        print(type(pipeline.signal))
        print(pipeline.fourier_transform())  # type: ignore
        pipeline.get_bands()  # type: ignore
        print(pipeline.get_bands())  # type: ignore
    except NotImplementedError:
        print(NOT_IMPLEMENTED_MESSAGE)
        feature_source = lambda: {}


    engine.run(feature_source=feature_source) # type: ignore


if __name__ == "__main__":
    run_full_app()
