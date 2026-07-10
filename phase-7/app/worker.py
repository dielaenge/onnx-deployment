import boto3
import json
import logging
import numpy as np
import os
import time
import subprocess
import urllib.parse
import wave
import shutil

from .audio_utils import MelSpectrogram

# --- Logging Setup ---
logging.basicConfig(
    level=logging.INFO,
    format= '%(asctime)s - %(name)s %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# INSTANTIATE CLIENTS
sqs_client = boto3.client('sqs')
s3_client = boto3.client('s3')

# GET ENV VARIABLES
queue_url = os.environ.get('SQS_QUEUE_URL')
app_data_bucket = os.environ.get('APP_DATA_BUCKET_NAME')



# HELPER FUNCTIONS
# Download raw file from S3
def download_raw_audio(bucket:str, key:str, local_path:str):
     s3_client.download_file(bucket, key, local_path)
# Convert to 16kHz mono wav / normalize
def normalize_raw_audio(input_path: str, output_path:str):
    
    # The FFmpeg convertion command
    # -y: Overwrite output
    # -i: Input file
    # -ar: Audio Rate (Resample to 16000)
    # -ac: Audio Channels (Mix down to 1 Mono channel)
    # -loglevel error: Don't clutter logs unless it fails
    
    # Run subprocess. check=True raises an error if FFmpeg fails (exit code != 0)
    subprocess.run(
            [
            "ffmpeg", 
            "-y", 
            "-i", input_path, 
            "-ar", "16000", 
            "-ac", "1", 
            "-loglevel", "error", 
            output_path
        ], 
        check=True, 
        stdout=subprocess.PIPE, 
        stderr=subprocess.PIPE
    )
# Generate spectrogram
def generate_spectrogram(processed_audio_path:str, full_spectrogram_path:str):
    spectrogram_processor = MelSpectrogram()

    with wave.open(processed_audio_path, 'rb') as w:
        frames = w.readframes(w.getnframes())
        audio_array = np.frombuffer(frames, dtype=np.int16).astype(np.float32) / 32768 #16bit integers range from 32768 to -32768; division sets range to [-1,1]
        
        full_spectrogram_data = spectrogram_processor(audio_array)
        
        np.save(full_spectrogram_path, full_spectrogram_data)
# Upload wav and spectrogram to S3
def upload_assets(bucket:str, processed_audio_path:str, processed_audio_key:str, full_spectrogram_path:str, spectrogram_key:str):
    s3_client.upload_file(processed_audio_path, bucket, processed_audio_key)
    s3_client.upload_file(full_spectrogram_path, bucket,  spectrogram_key)

# MAIN FUNCTION
def main():
    logger.info("Fargate Cold Path Worker started. Polling SQS...")

    while True: # ECS expects a service to run or otherwise it will start a new task / provision a new container
        try:
            # Receive message from SQS queue // API reference: https://docs.aws.amazon.com/AWSSimpleQueueService/latest/APIReference/API_Message.html
            response = sqs_client.receive_message(
                QueueUrl=queue_url,
                AttributeNames=[
                    'SentTimestamp'
                ],
                MaxNumberOfMessages=1,
                MessageAttributeNames=[
                    'All'
                ],
                WaitTimeSeconds=20
            )

            messages = response.get('Messages', [])
            
            for message in messages:
                
                # Empty path and key variables
                raw_audio_path = None
                processed_audio_path = None
                full_spectrogram_path = None 
                s3_processed_audio_object_key = None
                s3_spectrogram_object_key = None
                
                try:    
                    # Load SQS Mesagge (loads = load string) as JSON
                    body = json.loads(message["Body"])

                    # Parse Message and event notification to variables
                    event_message = body['Records'][0] # event message structure: https://docs.aws.amazon.com/AmazonS3/latest/userguide/notification-content-structure.html
                    object_key = urllib.parse.unquote_plus(event_message['s3']['object']['key'])
                    bucket_name = event_message['s3']['bucket']['name']
                    receipt_handle = message['ReceiptHandle'] # unique identifier of SQS message

                    file_name = os.path.basename(object_key) # keeps filename with whatever file extension – maybe this is redundant and I could go from object_key straight to base_name
                    base_name, _ = os.path.splitext(file_name) # split base name and file extension --> returns a tuple
                    
                    # set path variables for local processing on Linux
                    raw_audio_path=f"/tmp/raw_{file_name}"
                    processed_audio_path=f"/tmp/processed_{base_name}.wav"
                    full_spectrogram_path = f"/tmp/spec_{base_name}.npy"

                    #set S3 keys
                    s3_processed_audio_object_key = f"processed/{base_name}.wav"
                    s3_spectrogram_object_key = f"spectrograms/{base_name}.npy"

                    logger.info("SQS Message loaded and parsed:\nobject_key:%s\nbucket_name: %s\nreceipt_handle: %s\nfile_name: %s\nbase_name: %s\nraw_audio_path: %s\nprocessed_audio_path: %s\nfull_spectrogram_path: %s\ns3_processed_audio_object_key: %s\ns3_spectrogram_object_key: %s", 
                    object_key, 
                    bucket_name,
                    receipt_handle, 
                    file_name, 
                    base_name, 
                    raw_audio_path,
                    processed_audio_path,
                    full_spectrogram_path,
                    s3_processed_audio_object_key,
                    s3_spectrogram_object_key
                    )

                    # DOWNLOAD
                    download_raw_audio(app_data_bucket, object_key, raw_audio_path)
                    
                    # Normalize
                    normalize_raw_audio(raw_audio_path, processed_audio_path)

                    # Generate spectrogram
                    generate_spectrogram(processed_audio_path=processed_audio_path, full_spectrogram_path=full_spectrogram_path)

                    # Save a copy of the spectrogram to models/ folder before any uploads or cleanups
                    shutil.copy(full_spectrogram_path, "app/models/spec_cold.npy")
                    logger.info("Saved a local copy of cold-path spectrogram for parity verification.")

                    # UPLOAD ASSETS     
                    upload_assets(bucket=app_data_bucket, processed_audio_path=processed_audio_path, processed_audio_key=s3_processed_audio_object_key, full_spectrogram_path=full_spectrogram_path, spectrogram_key=s3_spectrogram_object_key)

                    # CLEANUP
                    # 4. Delete received message from queue
                    sqs_client.delete_message(
                        QueueUrl=queue_url,
                        ReceiptHandle=message['ReceiptHandle']
                    )
                    logger.info('Received and deleted message: %s', message)


                except subprocess.CalledProcessError as e:
                    # Capture FFmpeg stderr (Standard Error) for debugging
                    logging.error(f"FFmpeg failed: {e.stderr.decode()}")
                    raise RuntimeError(f"Could not process audio file: {e.stderr.decode()}")
                
                except Exception as e:
                    logging.error(f"Audio processing error: {str(e)}")
                    raise e
                
                finally:
                    # Cleanup: Look for any uploaded and normalized files and delete them
                    # If we don't delete files, /tmp is filled up to its 512MB limit and Lambda crashes
                    if raw_audio_path and os.path.exists(raw_audio_path):
                        os.remove(raw_audio_path)
                    if processed_audio_path and os.path.exists(processed_audio_path):
                        os.remove(processed_audio_path)
                    if full_spectrogram_path and os.path.exists(full_spectrogram_path):
                        os.remove(full_spectrogram_path)
                    

        except Exception as message_error:
            logger.error("Failed to process message %s: %s", message['MessageId'], message_error)
                    
        except Exception as system_error:
                    logger.error("SQS polling error / global SQS connection issues: %s", system_error)
                    time.sleep(5) # wait before retrying connection

if __name__ == "__main__":
    main()