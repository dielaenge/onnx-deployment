#!/bin/bash

export PYTHONPATH="$(pwd):PYTHONPATH"

# python src/datagen.py -cn datagen_rirs seed=32
# python src/datagen.py -cn datagen_speech seed=32
# python src/datagen.py -cn datagen_speech_ctr seed=32

# python src/datagen.py -cn datagen_rirs seed=42
# python src/datagen.py -cn datagen_speech seed=42
# python src/datagen.py -cn datagen_speech_ctr seed=42

# python src/datagen.py -cn datagen_rirs seed=52
# python src/datagen.py -cn datagen_speech seed=52
# python src/datagen.py -cn datagen_speech_ctr seed=52

python src/datagen.py -cn datagen_rirs seed=62
python src/datagen.py -cn datagen_speech seed=62
python src/datagen.py -cn datagen_speech_ctr seed=62