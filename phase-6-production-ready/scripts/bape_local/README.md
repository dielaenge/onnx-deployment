**BAPE** Blind Acoustic Parameter Estimation

## Features

- RIR and speech dataset pipelines
- Variational autoencoder (VAE) for RIRs
- Transformer-based speech encoder
- Uncertainty model
- Flexible YAML configuration ([conf/](conf/))

## Structure

- `src/` — Source code (models, data, utils, pipelines)
- `conf/` — Hydra configs (data, models, trainers)
- `data/` — Datasets and pickles
- `logs/`, `outputs/` — Training logs, results


## Running from terminal

Add working directory to python path:
```
export PYTHONPATH="${PWD}"
```