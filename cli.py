import typer
import time
import json
import numpy as np
from typing import Annotated
from src.acoustic_processor import AcousticModelProcessor, load_and_preprocess_audio
from memory_profiler import profile

# set up typer CLI app
app = typer.Typer()
MODEL_PATH = "dummy_acoustic_model.onnx" # default model path

try:
    processor = AcousticModelProcessor(MODEL_PATH) #load an AcousticModelProcessor instance based on our model
except Exception as e:
    typer.echo(f"Error loading model: {e}")
    raise typer.Exit(code=1)

@profile #profile memory usage of this part only
def profile_inference(processor: AcousticModelProcessor, preprocessed_audio: np.ndarray,):
    """Measure processing time and generate acoustic vector."""

    #optional warmup run
    processor.generate_vector(preprocessed_audio)

    # timed run
    start_time = time.perf_counter()
    vector = processor.generate_vector(preprocessed_audio)
    end_time = time.perf_counter()
    
    processing_time_ms = (end_time - start_time)*1000

    return vector, processing_time_ms

@app.command()
def main( # was "generate" but switched to "main" because its a single command app and doesn't accept an option like "python cli.py generate test_audio.wav", instead it's called with "python cli.py test_audio.wav"
    audio_path: Annotated[str, typer.Argument(help="Path to the input audio file (wav/mp3).")], #
    output_json: Annotated[str, typer.Option("--output", "-o", help="File path to save the resulting vector JSON")] = "acoustic_vector.json",
):
    """
    Generates the acoustic vector from an input audio file an measures performance.
    """
    typer.echo(f"--- Starting acoustic vector generation for: {audio_path} ---")

    try:
        # --- Preprocessing and Profiling Setup ---

        # 1. Load and preprocess audio
        preprocessed_audio = load_and_preprocess_audio(audio_path)
        # 2. Load inference and time it
        vector, processing_time_ms = profile_inference(processor, preprocessed_audio)
        # 3. Document the output
        output_data = {
            "source_file": audio_path,
            "input_audio_samples": preprocessed_audio.shape[1], # input tensor will have a shape of [1, N] of which N will be the samples of the input audio
            "preprocessing_time_ms": round(processing_time_ms, 3),
            "vector_shape": list(vector.shape),
            "vector": vector.flatten().tolist() 
        }
        # 4. Save the results
        with open(output_json, "w") as f:
            json.dump(output_data, f, indent=4)

        typer.echo("\n---- Results ----")
        typer.echo(f"Inference Time: {processing_time_ms:.3f} ms")
        typer.echo(f"Vector Shape: {output_data['vector_shape']}")
        typer.echo(f"Vector saved to {output_json}")

    except Exception as e:
        typer.echo(f"\nFATAL ERROR: Failed during processing: {e}", err=True)
        raise typer.Exit(code=1)
    
if __name__=="__main__":
    app()

