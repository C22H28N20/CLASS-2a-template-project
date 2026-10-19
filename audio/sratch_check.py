import numpy as np
from audio.pipeline import AudioPipeline

pipeline = AudioPipeline("audio/audio (2).mp3")
pipeline.load()

features = []

for call_number in range(1, 16):
    result = pipeline.get_features()
    features.append(result)

    print(
        f"Call {call_number}: "
        f"peak={result['peak']:.6f}, rms={result['rms']:.6f}"
    )

assert len({round(item["peak"], 10) for item in features}) > 1

# Check call 6 manually: samples 5120 through 6143.
window = pipeline.signal[5120:6144]  # type: ignore
manual_rms = np.sqrt(np.mean(np.square(window)))

print(f"Manual RMS for call 6: {manual_rms:.6f}")
print(f"Pipeline RMS for call 6: {features[5]['rms']:.6f}")
assert np.isclose(manual_rms, features[5]["rms"])