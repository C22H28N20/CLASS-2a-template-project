import librosa
import numpy as np
class AudioPipeline:
    """Loads an audio file and extracts features from it, frame by frame.

    Both load() and get_features() are stubs you must implement yourself —
    that's intentional, not an oversight. This unit is about the whole
    pipeline (data source -> feature extraction -> real-time rendering), not
    just feature extraction handed to you pre-solved.
    """

    def __init__(self, file_path: str, sample_rate: int = 22050, signal: np.ndarray | None = None) -> None:
        self.file_path = file_path
        self.sample_rate = sample_rate
        self.signal = signal
        self._reported_window = False
        self.position = 0  # Current read position in the signal, in samples

    def load(self) -> None:
        """Load the audio file at self.file_path via librosa, at
        self.sample_rate, and store the resulting signal on the instance.
        """
        if self.signal is None:
            self.signal, _ = librosa.load(self.file_path, sr=self.sample_rate)
            
            #print(f"Loaded signal with {len(self.signal)} samples at {self.sample_rate} Hz.")
            return self.signal  # type: ignore
        else:
            print("Signal already loaded, skipping load.")
            return self.signal  # type: ignore
#done lmao
    def get_features(self) -> dict: # type: ignore
        if self.signal is None:
            raise NotImplementedError("AudioPipeline.load() must be called before get_features().")

        window_size = 1024
        start = self.position
        end = start + window_size
        if end > len(self.signal):
            raise ValueError("Not enough samples left in the signal to extract a full window.")
        window = self.signal[start:end]
        self.position = end  # Advance the read position for the next call


        if len(self.signal) < window_size:
            raise ValueError("The signal must contain at least 1024 samples.")

        peak = float(np.max(np.abs(window)))
        rms = float(np.sqrt(np.mean(np.square(window))))

        
        

        if not self._reported_window:
            print(f"Peak: {peak:.6f} | RMS: {rms:.6f}")
            tempo, beat_frames = librosa.beat.beat_track(
                y=self.signal,
                sr=self.sample_rate,
            )
            tempo_value = float(np.asarray(tempo).reshape(-1)[0])
            print(f"Tempo: {tempo_value:.2f} BPM | Beats: {len(beat_frames)}")
            self._reported_window = True
        

        return {
            "Mean_amplitude": np.mean(np.abs(window)),
            "Highest_amplitude": peak,
            "Lowest_amplitude": np.min(np.abs(window)),
            "peak": peak,
            "rms": rms,
        }
    
        """Extract numerical features (amplitude at minimum) from the current
        window of the loaded signal, advance the pipeline's internal read
        position accordingly, and return them as a dict[str, float].

        This return value is passed directly into engine.update().
        """
        
