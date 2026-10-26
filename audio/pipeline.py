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
        self.window_size = 1024
        self.file_path = file_path
        self.sample_rate = sample_rate
        self.signal = signal
        self._reported_window = False
        self.position = 0  # Current read position in the signal, in samples
        self.bandlimits = { 
            "low_hz": 125, 
            "high_hz": 2000,
        }

    def load(self) -> None:
        """Load the audio file at self.file_path via librosa, at
        self.sample_rate, and store the resulting signal on the instance.
        """
        if self.signal is None:
            self.signal, _ = librosa.load(self.file_path, sr=self.sample_rate)
            self.position = len(self.signal) // 2  # Start reading from the middle of the signal
            #print(f"Loaded signal with {len(self.signal)} samples at {self.sample_rate} Hz.")
            return self.signal  # type: ignore
        else:
            print("Signal already loaded, skipping load.")
            return self.signal  # type: ignore
        #
    
    def get_window(self): 
       if self.signal is not None:
            return self.signal[self.position:self.position + self.window_size]
       else:
            raise ValueError("Signal not loaded. Call load() first.")

    def get_peak(self):
        peak = float(np.max(np.abs(self.get_window())))
        return peak



    def get_rms(self):
        rms = float(np.sqrt(np.mean(np.square(self.get_window()))))
        return rms

    
    def get_tempo(self):
        if not self._reported_window:
             print(f"Peak: {self.get_peak():.6f} | RMS: {self.get_rms():.6f}")
             tempo, beat_frames = librosa.beat.beat_track(
                 y=self.signal,
                 sr=self.sample_rate,
             )
             tempo_value = float(np.asarray(tempo).reshape(-1)[0])
             print(f"Tempo: {tempo_value:.2f} BPM | Beats: {len(beat_frames)}")
             self._reported_window = True


    

                
    def get_bands(self):
        low_hz = self.bandlimits["low_hz"]
        high_hz = self.bandlimits["high_hz"]
        bins = self.fourier_transform()["bins"]
        bass_bins = bins[0:(low_hz * (self.window_size // self.sample_rate))]
        mid_bins = bins[(low_hz * (self.window_size // self.sample_rate)):(high_hz * (self.window_size // self.sample_rate))]
        treble_bins = bins[(high_hz * (self.window_size // self.sample_rate)):]
        bass = np.sum(bass_bins**2)
        mid = np.sum(mid_bins**2)
        treble = np.sum(treble_bins**2)
        return {
            "bass": bass,
            "mid": mid,
            "treble": treble,
        }
    
    def get_features(self) -> dict: # type: ignore
        if self.signal is None:
            raise NotImplementedError("AudioPipeline.load() must be called before get_features().")

        window_size = self.window_size
        start = self.position
        end = start + window_size
        if end > len(self.signal):
            raise ValueError("Not enough samples left in the signal to extract a full window.")
        window = self.signal[start:end]
        self.position = end  # Advance the read position for the next call


        if len(self.signal) < window_size:
            raise ValueError("The signal must contain at least 1024 samples.")

        

        

        return {
            "Mean_amplitude": np.mean(np.abs(window)),
            "Highest_amplitude": np.max(np.abs(window)),
            "Lowest_amplitude": np.min(np.abs(window)),
            "peak": self.get_peak(),
            "rms": self.get_rms(),
        }
    
        """Extract numerical features (amplitude at minimum) from the current
        window of the loaded signal, advance the pipeline's internal read
        position accordingly, and return them as a dict[str, float].

        This return value is passed directly into engine.update().
        """
    def fourier_transform(self):
        current_window = np.array(self.get_window() * np.hanning(self.window_size))
        # spectrum = np.fft.rfftfreq(len(current_window), d=1/self.sample_rate)
        spectrum: np.ndarray = np.abs(np.fft.rfft(current_window))
        num_bins = len(spectrum)
        bins: np.ndarray = np.fft.rfftfreq(self.window_size, d=1/self.sample_rate)
        return {
            "spectrum": spectrum,
            "num_bins": num_bins,
            "bins": bins,
        }
        
        
        
        