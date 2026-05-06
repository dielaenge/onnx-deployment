class RealTimeAudioProcessor extends AudioWorkletProcessor {
    process(inputs, outputs, parameters) {
        //inputs[0] is the audio source; inputs[0][0] is the left channel (Mono)
        const inputLeftChannel = inputs[0][0];

        if (inputLeftChannel) {
            // we take the left channel input and copy it as a float32 array (called data) to the main thread
            const data = new Float32Array(inputLeftChannel);
            this.port.postMessage(data);
        }
        return true;
    }
}

registerProcessor('real-time-audio-processor', RealTimeAudioProcessor);
