import librosa
import numpy as np
import time


class AudioPipeline:
    """Loads an audio file and extracts features from it, frame by frame."""

    def __init__(self, file_path: str, sample_rate: int = 22050, signal: np.ndarray | None = None) -> None:
        self.window_size = 1024
        self.file_path = file_path
        self.sample_rate = sample_rate
        self.signal = signal
        self._reported_window = False
        self.position = 0  # Current read position in the signal, in samples
        self._playback_started_at: float | None = None
        self.bandlimits = {
            "low_hz": 250,
            "high_hz": 2000,
        }
        self.band_peaks = {
            "bass": 0.0,
            "mid": 0.0,
            "treble": 0.0,
        }

    def load(self) -> np.ndarray:
        """Load the audio file at self.file_path via librosa, at
        self.sample_rate, and store the resulting signal on the instance.
        """
        if self.signal is None:
            self.signal, _ = librosa.load(self.file_path, sr=self.sample_rate)
            self.position = 0
        else:
            print("Signal already loaded, skipping load.")
        self.band_peaks = self.get_bands_peak()
        return self.signal

    def get_window(self) -> np.ndarray:
        if self.signal is None:
            raise ValueError("Signal not loaded. Call load() first.")
        return self.signal[self.position:self.position + self.window_size]

    def get_peak(self) -> float:
        return float(np.max(np.abs(self.get_window())))

        
    def get_rms(self) -> float:
        return float(np.sqrt(np.mean(np.square(self.get_window()))))

    def get_centroid(self) -> float:
        ft = self.fourier_transform()
        freqs = ft["bins"]
        spectrum = ft["spectrum"]
        total_energy = np.sum(spectrum)
        if total_energy == 0:
            return 0.0
        return float(np.sum(freqs * spectrum) / total_energy)

    def get_onset(self) -> float:
        ft = self.fourier_transform()
        spectrum = ft["spectrum"]
        return float(np.sum(np.diff(spectrum)))

    def get_tempo(self) -> None:
        if not self._reported_window:
            print(f"Peak: {self.get_peak():.6f} | RMS: {self.get_rms():.6f}")
            tempo, beat_frames = librosa.beat.beat_track(
                y=self.signal,
                sr=self.sample_rate,
            )
            tempo_value = float(np.asarray(tempo).reshape(-1)[0])
            print(f"Tempo: {tempo_value:.2f} BPM | Beats: {len(beat_frames)}")
            self._reported_window = True

    def fourier_transform(self) -> dict:
        window = self.get_window()
        if len(window) != self.window_size:
            raise ValueError("Window is shorter than window_size; not enough samples left.")

        current_window = window * np.hanning(self.window_size)
        spectrum: np.ndarray = np.abs(np.fft.rfft(current_window))  # magnitude per bin
        freqs: np.ndarray = np.fft.rfftfreq(self.window_size, d=1 / self.sample_rate)  # Hz per bin
        return {
            "spectrum": spectrum,
            "num_bins": len(spectrum),
            "bins": freqs,
        }

    def get_bands_peak(self) -> dict:
        peaks = {"bass": 0.0, "mid": 0.0, "treble": 0.0}
        if self.signal is None:
            raise ValueError("Signal not loaded. Call load() first.")
        low_hz = self.bandlimits["low_hz"]
        high_hz = self.bandlimits["high_hz"]
        N_windows = len(self.signal) // (self.window_size * 4)
        for i in range(N_windows): 
            current_window = self.signal[i * self.window_size:(i + 1) * self.window_size]
            spectrum: np.ndarray = np.abs(np.fft.rfft(current_window))  # magnitude per bin
            bins: np.ndarray = np.fft.rfftfreq(self.window_size, d=1 / self.sample_rate)  # Hz per bin
            power = spectrum ** 2  # energy per bin
            bass = float(np.sum(power[bins < low_hz]))
            mid = float(np.sum(power[(bins >= low_hz) & (bins < high_hz)]))
            treble = float(np.sum(power[bins >= high_hz]))
            peaks["bass"] = max(peaks["bass"], bass)
            peaks["mid"] = max(peaks["mid"], mid)
            peaks["treble"] = max(peaks["treble"], treble)

        return peaks
            


    def get_bands(self) -> dict:
        """Relative energy in bass / mid / treble. The three values sum to 1."""
        low_hz = self.bandlimits["low_hz"]
        high_hz = self.bandlimits["high_hz"]

        ft = self.fourier_transform()
        freqs = ft["bins"]
        power = ft["spectrum"] ** 2  # energy per bin

        bass = float(np.sum(power[freqs < low_hz])) / self.band_peaks["bass"] if self.band_peaks["bass"] > 0 else 1.0
        mid = float(np.sum(power[(freqs >= low_hz) & (freqs < high_hz)])) / self.band_peaks["mid"] if self.band_peaks["mid"] > 0 else 1.0
        treble = float(np.sum(power[freqs >= high_hz])) / self.band_peaks["treble"] if self.band_peaks["treble"] > 0 else 1.0
        bass = min(max(bass, 0.0), 1.0)
        mid = min(max(mid, 0.0), 1.0)
        treble = min(max(treble, 0.0), 1.0)

        return {
            "bass": bass,
            "mid": mid,
            "treble": treble,
        }

    def get_features(self) -> dict:
        """Extract numerical features from the current window, then advance
        the read position (looping back to the start at the end of the signal).
        """
        if self.signal is None:
            raise NotImplementedError("AudioPipeline.load() must be called before get_features().")

        if len(self.signal) < self.window_size:
            raise ValueError(f"The signal must contain at least {self.window_size} samples.")

        if self._playback_started_at is None:
            self._playback_started_at = time.perf_counter()

        elapsed = time.perf_counter() - self._playback_started_at
        max_start = len(self.signal) - self.window_size
        self.position = int(elapsed * self.sample_rate) % (max_start + 1)

        window = self.get_window()
        bands = self.get_bands()  # one FFT per frame

        features = {
            "Mean_amplitude": float(np.mean(np.abs(window))),
            "Highest_amplitude": float(np.max(np.abs(window))),
            "Lowest_amplitude": float(np.min(np.abs(window))),
            "peak": self.get_peak(),
            "rms": self.get_rms(),
            "bass": bands["bass"],
            "mid": bands["mid"],
            "treble": bands["treble"],
            "centroid": self.get_centroid(),
            "onset": self.get_onset(),
        }

        return features