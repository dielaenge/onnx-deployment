import numpy as np
from pathlib import Path

# Identify Base Directory
SCRIPTS_DIR = Path(__file__).resolve().parent
BASE_DIR = SCRIPTS_DIR.parent

# 1. Load both arrays
spec_hot = np.load(BASE_DIR / "app" / "models" / "spec_hot.npy")
spec_cold = np.load(BASE_DIR / "app" / "models" / "spec_cold.npy")

print(f"Hot Spectrogram Shape:  {spec_hot.shape}")
print(f"Cold Spectrogram Shape: {spec_cold.shape}")

# 2. Extract matching dimensions (aligning the end of both signals)
# Hot path length is shorter due to the 3.8s buffer warmup phase (1900 frames)
hot_len = spec_hot.shape[1]
spec_cold_aligned = spec_cold[:, -hot_len:]

# 3. Calculate mathematical distance
mse = np.mean((spec_hot - spec_cold_aligned) ** 2)
max_deviation = np.max(np.abs(spec_hot - spec_cold_aligned))

print(f"\n--- EMPIRICAL DRIFT ANALYSIS ---")
print(f"Aligned Cold Shape:     {spec_cold_aligned.shape}")
print(f"Mean Squared Error:     {mse:.8f}")
print(f"Max Absolute Error:     {max_deviation:.8f}")