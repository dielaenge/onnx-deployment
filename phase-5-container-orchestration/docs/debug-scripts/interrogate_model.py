import torch
import json

# Path to the .pth file Paul gave you
checkpoint = torch.load("src/2025-11-18_17-40-57/model.pth", map_location="cpu")

# Print the keys to see what's inside
print(f"Keys in checkpoint: {checkpoint.keys()}")

# If you see a key called 'cfg' or 'config' or 'hyperparams', print it!
if 'cfg' in checkpoint:
    print(json.dumps(f"cfg checkpoint: {checkpoint['cfg']}"), indent=4)

if 'config' in checkpoint:
    print(json.dumps(f"config checkpoint: {checkpoint['config']}"), indent=4)

if 'hyperparams' in checkpoint:
    print(json.dumps(f"hyperparams checkpoint: {checkpoint['hyperparams']}"), indent=4)