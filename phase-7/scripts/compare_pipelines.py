import sys
import numpy as np
from pathlib import Path

# 1. Verify CLI arguments [2.1]
if len(sys.argv) < 2:
    print("Error: Please provide a session UUID.")
    print("Usage: python compare_pipelines.py <UUID>")
    sys.exit(1)

uuid = sys.argv[1]

# 2. Dynamic path resolution (safe to run from root or /scripts)
SCRIPT_DIR = Path(__file__).resolve().parent
BASE_DIR = SCRIPT_DIR.parent if SCRIPT_DIR.name == "scripts" else SCRIPT_DIR

hot_path = BASE_DIR / "app" / "models" / f"spec_hot_{uuid}.npy"
cold_path = BASE_DIR / "app" / "models" / f"spec_cold_{uuid}.npy"

if not hot_path.exists():
    print(f"Error: Hot spectrogram not found at {hot_path}")
    sys.exit(1)
if not cold_path.exists():
    print(f"Error: Cold spectrogram not found at {cold_path}")
    sys.exit(1)

# 3. Load Arrays
spec_hot = np.load(hot_path)
spec_cold = np.load(cold_path)

print(f"Hot Spectrogram Shape:  {spec_hot.shape}")
print(f"Cold Spectrogram Shape: {spec_cold.shape}")

hot_len = spec_hot.shape[1]
cold_len = spec_cold.shape[1]

if cold_len < hot_len:
    print("Error: Cold spectrogram is shorter than hot spectrogram. Cannot align.")
    sys.exit(1)

# 4. Sliding Window Search [4]
best_mse = float('inf')
best_offset = 0

print("\nScanning temporal offsets for optimal signal alignment...")
for offset in range(0, cold_len - hot_len + 1):
    spec_cold_slice = spec_cold[:, offset:offset + hot_len]
    mse = np.mean((spec_hot - spec_cold_slice) ** 2)
    
    if mse < best_mse:
        best_mse = mse
        best_offset = offset

# 5. Extract aligned metrics [4]
best_time_offset_sec = best_offset / 500.0  # 500 frames per second
spec_cold_aligned = spec_cold[:, best_offset:best_offset + hot_len]
max_deviation = np.max(np.abs(spec_hot - spec_cold_aligned))

print(f"\n--- EMPIRICAL DRIFT ANALYSIS (SLIDING ALIGNMENT) ---")
print(f"Best Temporal Offset:  {best_offset} frames ({best_time_offset_sec:.3f} seconds)")
print(f"Minimum Mean Squared Error (MSE): {best_mse:.8f}")
print(f"Max Absolute Error at Match:      {max_deviation:.8f}")