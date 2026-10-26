import numpy as np
import audio.pipeline as pipeline

window = np.array(1024 * np.hanning(1024))
magnitude = np.abs(np.fft.rfft(window))
sample_rate = getattr(pipeline, "sample_rate", 44100)
bins = np.fft.rfftfreq(len(window), d=1/sample_rate)
num_bins = len(bins)

print(f"Number of bins: {num_bins}")



