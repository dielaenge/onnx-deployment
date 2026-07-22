// VARIABLES      
const micBtn = document.getElementById('mic-btn');
micBtn.addEventListener("click", startRecording);

const statusText = document.getElementById('status-text');
const recText = document.getElementById('rec-text');
const jsonResult = document.getElementById('json-result');
const resultArea = document.getElementById('result-area');
const coldPathResults = document.getElementById('coldPathResults');
const audioPlayer = document.getElementById("audio-player")
const liveSpec = document.getElementById("spectrogram-canvas")

// Web Audio API
// Get the current hostname (to solve switching between local and cloud deployment)
const host = window.location.host;

let sessionId = crypto.randomUUID();

// Find out the protocol
// …if on HTTPS/CloudFront, WSS is required
// …or else (on HTTP/local), WS is required
const protocol = window.location.protocol === 'https:' ? 'wss://' : 'ws://';

// Construct the URL
const wsUrl = `${protocol}${host}/ws?session_id=${sessionId}`;

console.log("Connecting to WebSocket at:", wsUrl);
const ws = new WebSocket(wsUrl);

let audioContext;
let micStream;


// liveStreamingBuffer will be used to store 32000 samples / 2 seconds of audio and then send it
let liveStreamingBuffer = [];

// offlineAudioBuffer caches the entire recording to make it available for cold path processing
let offlineAudioBuffer = [];

let currentTimelineData = []; // was null before, now empty array
let timeCounter = 0; // will serve as time indicator and be increased by 2 for every chunk

let lockedT60ParamId = null;
let lockedC50ParamId = null;

// FREQUENCY BANDS
const bandLabels = [
  { freq: "125 Hz", desc: "Bass/Low-end" },
  { freq: "250 Hz", desc: "Lower-mid" },
  { freq: "500 Hz", desc: "Mids" },
  { freq: "1 kHz",  desc: "Reference Band" },
  { freq: "2 kHz",  desc: "Upper-mids" },
  { freq: "4 kHz",  desc: "Presence/Highs" },
  { freq: "8 kHz",  desc: "Brilliance" }
    ];

// COLOR SCHEME
// use D3 sequential color scheme, 
// https://d3js.org/d3-scale-chromatic/sequential#interpolateWarm
const colorScale = d3.scaleSequential(d3.interpolateWarm)
    .domain([0, 6]); // 0 is 125Hz (Bass), 6 is 8kHz (Treble)

// RECORDING LOGIC
async function startRecording(){
    statusText.innerText = `Inference session started. First results in 4 seconds…`;
    let countDown = 3;        
    const countDownTimer = setInterval(() => {
        statusText.innerText = `Inference session started. First results in ${countDown} seconds…`;
        countDown--;
        if (countDown < 0) {
            clearInterval(countDownTimer);
            statusText.innerText = "Inference results streaming…";
        }
    }, 1000);

    // get the mic stream
    micStream = await navigator.mediaDevices.getUserMedia({ audio: true });
    // set mic to record at 16kHz sample rate
    audioContext = new AudioContext({sampleRate: 16000});
    // set mic stream as source
    const source = audioContext.createMediaStreamSource(micStream);
    // load external processor.js script into the AudioContext
    await audioContext.audioWorklet.addModule('processor.js');

    // create the node, which serves as a controller/processor to the processor; it's the actual interface
    const workletNode = new AudioWorkletNode(audioContext, 'real-time-audio-processor');

    // Listen for messages from processor.js
    workletNode.port.onmessage = function(event) {
        const rawFloats = event.data; // this is the left channel float32array defined in processor.js
        
        liveStreamingBuffer.push(...rawFloats);
        offlineAudioBuffer.push(...rawFloats);
    
        // If liveStreamingBuffer.length >= 3200 (0.2 seconds at 16kHz):
        if (liveStreamingBuffer.length >= 3200) {
            // cut the first 32000 samples from the chunk, if there is a remainder it stays in the liveStreamingBuffer
            const chunkToSend = liveStreamingBuffer.splice(0, 3200);
            // Convert liveStreamingBuffer into a new Float32Array
            const payload = new Float32Array(chunkToSend);
            // send it over the websocket connect
            ws.send(payload);
        }
    }
    // connect the node
    source.connect(workletNode);

    // change UI
    console.log("Recording started");
    micBtn.removeEventListener("click", startRecording);
    micBtn.addEventListener("click", stopRecording);
    recText.innerText = "Tap microphone again to stop recording.";
};

function stopRecording() {
    // Swap button listeners back to start mode
    micBtn.removeEventListener("click", stopRecording);
    micBtn.addEventListener("click", startRecording);
    recText.innerText = "Processing and uploading raw audio...";

    // Stop the microphone recording
    if (typeof micStream !== 'undefined') {
        micStream.getTracks().forEach(track => track.stop());
    }
    
    // Stop the audio processing environment
    if (typeof audioContext !== 'undefined' && audioContext.state !== 'closed') {
        audioContext.close();
        statusText.innerText = "Recording stream closed.";
        recText.innerText = "Reload page for new inference session.";
        micBtn.classList.add('hidden');
    }
    
    // Close the WebSocket connection to the server
    if (ws.readyState === WebSocket.OPEN) {
        ws.close();
    }

    // trigger cold-path upload
    uploadAndProcessRecording();
};

// UPLOAD AND PROCESS RECORDING ON STOP

async function uploadAndProcessRecording() {
    if (offlineAudioBuffer.length === 0) return;

    try {
        console.log("Encoding raw floats to 16-bit WAV …");
        const wavBlob = encodeWav(offlineAudioBuffer, 16000);

        console.log("Fetching presigned URLs …");
        const response = await fetch(`/api/presigned-urls?session_id=${sessionId}`);
        const { session_id, upload_url, upload_object_key, wav_download_url, wav_download_key, spec_download_url, spec_download_key } = await response.json();
        
        console.log("Uploading WAV directly to S3...");
        await fetch(upload_url, {
            method: "PUT",
            headers: { "Content-Type": "audio/wav" },
            body: wavBlob
        });
        console.log(`SUCCESS: WAV uploaded to S3 for Session ID: ${session_id}`);
        

        console.log(`Polling S3 for cold path results…`);
        
        let ready = false;
        let attempt = 0;
        const maxAttempts = 8;
        
        while (attempt < maxAttempts ) {
            const check = await fetch(wav_download_url, { method: 'GET' });
            
            // if HTTP: 200: S3 has the file
            if (check.ok) {
                ready = true;
                break;
            }

            // if check does not return 200, calculate delay, sleep and initialize next attempt
            let delay = 1000 * Math.pow(1.5, attempt) + (Math.random() * 500);
            console.log(`Results not ready yet, retrying in ${Math.round(delay)}ms ….`);
            await new Promise(resolve => setTimeout(resolve, delay));
            attempt++;
        }

        if (ready) {
            console.log("Assets ready in S3, downloading cold path results…")
            
            // Catch results
            const processedWav = await fetch(wav_download_url, { method: 'GET' });
            const wavBlob = await processedWav.blob();
            // create a temporary blob URL that references the WAV audio data stored in memory
            const audioUrl = URL.createObjectURL(wavBlob);

            coldPathResults.classList.remove('hidden');
            liveSpec.classList.add('hidden');
            audioPlayer.src = audioUrl;

            const processedSpec = await fetch(spec_download_url, { method: 'GET' });
            const specJson = await processedSpec.json();
            
            // Pass JSON values directly to your existing canvas rendering functions
            renderSpectrogramCanvas(specJson.data.flat(), specJson.shape, "cold-path-spectrogram-canvas");

            // Re-render D3 charts with FULL session history (0s to end)
            drawChart(currentTimelineData, 't60_params', 't60-chart-container', 'T60 Decay (Seconds)');
            drawChart(currentTimelineData, 'c50_params', 'c50-chart-container', 'C50 Clarity (dB)');

            // Reset Audio Buffer
            // Reset the buffer for the next session
            offlineAudioBuffer = [];
        }

        
    } catch (e) {
        console.error(`Cold-path upload failed:${e}`);
    }
}

// BUILD LEGEND
function buildLegend(paramKey) {
    // Clear the legend before redrawing to prevent duplicates on resize
    document.getElementById(`${paramKey}-legend`).innerHTML = "";

    // Loop through the data series
    bandLabels.forEach((band, index) => {

         // Create the Frequency Span (Bold)
        const freqLabel = document.createElement("span");
        freqLabel.className = "font-bold text-slate-200 group-hover:text-white";
        // parse bandLabels.frequ
        freqLabel.innerText = bandLabels[index].freq;

        freqLabel.innerText = band.freq;

        // Create the main Button Container
        const btn = document.createElement("button");
        btn.id = `btn-param-${paramKey}-${index}`;
        btn.className = "flex items-center space-x-3 text-xs p-2 rounded hover:bg-white/5 w-full text-left transition-all border border-transparent hover:border-slate-700 group";
            
        // Create the Color Dot
        const dot = document.createElement("div");
        dot.className = "w-3 h-3 rounded-full flex-shrink-0 shadow-lg shadow-black/50";
        dot.style.backgroundColor = colorScale(index);

        // Create a Wrapper DIV for the text (Flex Column)
        const textCol = document.createElement("div");
        textCol.className = "flex flex-col";

        // Create the Description Span (Small/Gray)
        const ctxLabel = document.createElement("span");
        ctxLabel.className = "text-[10px] text-slate-500 uppercase tracking-wider group-hover:text-slate-400";
        // parse bandLabels.desc
        ctxLabel.innerText = bandLabels[index].desc;

        // Attach text spans to the Wrapper Div
        textCol.appendChild(freqLabel);
        textCol.appendChild(ctxLabel);

        // Add Toggle Functionality
        // Helper function to isolate visually
        const isolateVisuals = (targetId) => {
            // FIX B: Restrict D3 selections strictly to the current chart container
            d3.select(`#${paramKey === 't60_params' ? 't60-chart-container' : 'c50-chart-container'}`)
              .selectAll(".parameter-group")
              .transition().duration(200).style("opacity", 0.05);

            // Isolate the focused line
            d3.select(`#${paramKey === 't60_params' ? 't60-chart-container' : 'c50-chart-container'}`)
              .selectAll(`.param-${targetId}`)
              .transition().duration(200).style("opacity", 1);

            // Dim parameter-specific buttons
            for (let i = 0; i < 7; i++) {
                const b = document.getElementById(`btn-param-${paramKey}-${i}`);
                if (b) {
                    if (i === targetId) {
                        b.classList.remove("opacity-40", "grayscale");
                        b.classList.add("border-slate-500");
                    } else {
                        b.classList.add("opacity-40", "grayscale");
                        b.classList.remove("border-slate-500");
                    }
                }
            }
        };

        // Helper function to reset visuals
        const resetVisuals = () => {
            // FIX C: Restrict reset selection to the current chart container
            d3.select(`#${paramKey === 't60_params' ? 't60-chart-container' : 'c50-chart-container'}`)
              .selectAll(".parameter-group")
              .transition().duration(200).style("opacity", 1);
            
            for (let i = 0; i < 7; i++) {
                const b = document.getElementById(`btn-param-${paramKey}-${i}`);
                if (b) {
                    b.classList.remove("opacity-40", "grayscale", "border-slate-500");
                }
            }
        };

        // Determine current lock state dynamically based on the parameter
        const getLockState = () => paramKey === 't60_params' ? lockedT60ParamId : lockedC50ParamId;
        const setLockState = (val) => {
            if (paramKey === 't60_params') lockedT60ParamId = val;
            else lockedC50ParamId = val;
        };

        btn.onmouseenter = () => { if (getLockState() === null) isolateVisuals(index); };
        btn.onmouseleave = () => { if (getLockState() === null) resetVisuals(); else isolateVisuals(getLockState()); };
        
        btn.onclick = () => {
            if (getLockState() === index) {
                setLockState(null);
                resetVisuals();
            } else {
                setLockState(index);
                isolateVisuals(index);
            }
        };

        btn.appendChild(dot);
        btn.appendChild(textCol);
        document.getElementById(`${paramKey}-legend`).append(btn);
    });
};
window.onload = () => {
    buildLegend('t60_params');
    buildLegend('c50_params');
};

// D3 visualisation
function drawChart(timelineData, paramKey, divContainerId, yAxisLabel) {
    const isT60 = paramKey === "t60_params";
    const currentLockedId = isT60 ? lockedT60ParamId : lockedC50ParamId;
    const tooltipSelector = `#${paramKey}-tooltip`;
    const tooltip = d3.select(tooltipSelector);

    const container = document.getElementById(divContainerId);

    const width = container.clientWidth;
    const height = container.clientHeight;

    // returns the time value from the seriesData.time array;left from an input x
    // https://d3js.org/d3-array/bisect#bisector_left
    const bisectTime = d3.bisector(d => d.time).left;

    const seriesData = [];
    const paramCount = 7;


    // 
    for (let p = 0; p < paramCount; p++) {
        const paramsAndIntervals = timelineData.map(d => {
            // BAPEs array has 21 items
            // param 0 uses indices 0,1,2 – param 1 uses 3,4,5 – …
            const paramArray = d[paramKey];
            return {
                time: d.timestamp_step,
                low:  paramArray[p * 3], // Lower bound of confidence interval for parameter[p]
                val:  paramArray[p * 3 + 1], // Actual estimate of parameter[p]
                high: paramArray[p * 3 + 2] // Upper bound of confidence interval for parameter[p]
            };
        });
        // extend the last data point to show the tail end of the last result
        if (paramsAndIntervals.length > 0) {
            const lastPoint = paramsAndIntervals[paramsAndIntervals.length - 1];
            paramsAndIntervals.push({
                time: lastPoint.time + 4, // Add the 4-second window
                low: lastPoint.low,
                val: lastPoint.val,
                high: lastPoint.high
            });
        }
    // add to seriesData
    seriesData.push({ id: p, values: paramsAndIntervals }); 
    }

    // Calculate global Min/Max across all series
    const allValues = seriesData.flatMap(s => s.values); // Flatten all 7 series into one big list
    // TO DO: calculating the true global min/max for entire (ended) recording should be delegated to a decoupled microservice

    // Clear previous chart and create svg container
    d3.select(`#${divContainerId}`).selectAll("svg").remove();

    const svg = d3.select(`#${divContainerId}`)
        .append("svg")
        .attr("width", width)
        .attr("height", height);

    // Define Scales (Scales translate data values, the INPUT DOMAIN, to screen values, the OUTPUT RANGE)
    // x-axis scale: time
    const xScale = d3.scaleLinear()
        .domain([d3.min(allValues, d => d.time), d3.max(allValues, d => d.time)]) // INPUT from min to max value from d.time
        .range([50, width - 20]); // OUTPUT starting at 50px and ending 20px before max width    
    
    // y-axis scale: estimates
    const yScale = d3.scaleLinear()
        .domain([
            d3.min(allValues, d => d.low) * 0.9, // INPUT MIN is lowest lower bound value (d.low); scale by 0.9 to add space beneath
            d3.max(allValues, d => d.high) * 1.1 // INPUT MX is highest upper bound value (d.high); scale by 1.1 to add space above
        ])
        .range([height - 30, 20]); // OUTPUT starting at (max height - 30px), ending at 20px height
    
    // create an area chart with .low and .high; on top, create a line chart with the actual .val
    
    // create area generator
    const areaGenerator = d3.area()
        .x(d => xScale(d.time)) //get x-value from time step
        .y0(d => yScale(d.low)) //get lower bound confidence
        .y1(d => yScale(d.high)) //get upper bound confidence
        //optional line-smoothing
        .curve(d3.curveStepAfter); 

    //   create line generator
    const lineGenerator = d3.line()
        .x(d => xScale(d.time)) // take timestampe_step values and scale to x-axis
        .y(d => yScale(d.val)) // take BAPEs value at index[1]
        //optional line-smoothing
        .curve(d3.curveStepAfter); // was curveMonotoneX 


    // Layer the visualization

    // We visualize each of the 7 octave bands with a line graph for the timeline of actual estimates and an area chart for the timeline of the related confidence intervall
    // we use d.id as the selector for each group
    
    // Create groups for each frequency band
    const groups = svg.selectAll(".parameter-group")
        .data(seriesData)
        .enter()
        .append("g")
        .attr("class", d => `parameter-group param-${d.id}`) // class to toggle 

    // Append area graph to each group
    groups.append("path")
        .attr("class", "confidence-area")
        .attr("d", d => areaGenerator(d.values)) // generator sources values.low and .high to generate area
        .attr("fill", d => colorScale(d.id))
        .attr("opacity", 0.2);

    // Append line graph to each group
    groups.append("path")
        .attr("class", "estimate-line")
        .attr("d", d => lineGenerator(d.values)) // generator sources values.low and .high to generate area
        .attr("stroke", d => colorScale(d.id))
        .attr("stroke-width", 2)
        .attr("fill", "none");

    // Invisible Overlay (Catches all mouse movements)

    // Dark mask for the left side
    const maskLeft = svg.append("rect")
        .attr("y", 20)
        .attr("height", height - 50)
        .attr("x", 50)   // Start at left margin
        .attr("width", 0)// add width when calculated on mousemove
        .attr("fill", "rgba(113,255, 195, 0.3)")
        .style("pointer-events", "none");

    // Dark mask for the right side
    const maskRight = svg.append("rect")
        .attr("y", 20)
        .attr("height", height - 50)
        .attr("x", width - 20)
        .attr("width", 0)
        .attr("fill", "rgba(113,255, 195, 0.3)")
        .style("pointer-events", "none");

    //Actual overlay
    svg.append("rect")
        .attr("width", width)
        .attr("height", height)
        .attr("fill", "none")
        .attr("pointer-events", "all")
        .on("mousemove", function(event) {
            const activeBandId = currentLockedId !== null ? currentLockedId : 3;
            const [mouseX, _] = d3.pointer(event);
            const hoverTime = xScale.invert(mouseX) - 2;

            // Fetch focused frequency band
            const focusedFrequencyBand = seriesData.find(s => s.id === currentLockedId);
            if (!focusedFrequencyBand) 
                return;

            // Calculate the nearest mathematical window start (steps of 2)
            const nearestWindowStart = Math.max(0, Math.round(hoverTime / 2) * 2);

            // Strictly check if this window exists in the Python data
            const currentData = focusedFrequencyBand.values.find(v => v.time === nearestWindowStart);

            // If the data doesn't exist (e.g., ghost window at 2.0s), hide the tooltip and stop.
            if (!currentData) {
                tooltip.style("opacity", 0);
                return; 
            }

            // Position and Tooltip logic (using actual data time, no fallbacks)
            const windowStartX = xScale(currentData.time);
            const windowEndX = xScale(currentData.time + 4);
            const pointX = xScale(currentData.time + 2);
            tooltip
                .style("left", pointX + "px")
                .style("top", (yScale(currentData.val) - 35) + "px")
                .style("opacity", 1);

            // Focus Masks
            // console.log("DEBUG INFO: Mouse X:", mouseX, "HoverTime:", hoverTime, "SnappedStart:", safeWindowStart);
            maskLeft
                .attr("x", 50)
                .attr("width", Math.max(0, windowStartX - 50));
            maskRight
                .attr("x", windowEndX)
                .attr("width", Math.max(0, (width - 20) - windowEndX));

            tooltip.select(".tt-header")
                .text(`${bandLabels[currentLockedId].freq} (${bandLabels[currentLockedId].desc})`);

            tooltip.select(".tt-value")
                .html(
                `Estimate: ${currentData.val.toFixed(3)}<br>` +
                `Interval: ${currentData.low.toFixed(2)} – ${currentData.high.toFixed(2)}<br><br>`+
                `Time: ${currentData.time.toFixed(1)} s - ${(currentData.time + 4).toFixed(1)} s`
                );
        })
        .on("mouseout", function() {
            tooltip.style("opacity", 0);
            maskLeft.attr("width", 0);
            maskRight.attr("width", 0);
            });
    
    // append grid/axes (background)
    // x-axis at bottom
    svg.append("g")
        .attr("transform", `translate(0, ${height - 30})`) // place at bottom
        .call(d3.axisBottom(xScale)) 

    // add x-axis label
    svg.append("text")
        .attr("text-anchor", "middle")
        .attr("x", width /2 )
        .attr("y", height) // Position it just below the axis
        .attr("class", "text-[10px] fill-slate-500 uppercase tracking-widest font-bold")
        .text("Time (Seconds)");


    // y-axis to the left
    svg.append("g")
        .attr("transform", `translate(50 ,0)`) // move right to keep margin
        .call(d3.axisLeft(yScale))

    // add y-axis label
    svg.append("text")
    .attr("transform", "rotate(-90)") 
    .attr("text-anchor", "middle")    
    .attr("x", -(height / 2)) 
    .attr("y", 15)    
    .attr("class", "text-[10px] fill-slate-500 uppercase tracking-widest font-bold")
    .text("BAPEs and Confidence");
}

// Spectrogram rendering
function renderSpectrogram(data, shape, canvasId) {
    const visibleCanvas = document.getElementById(canvasId);
    if (!visibleCanvas) return;
    const visibleCtx = visibleCanvas.getContext("2d");
    
    // Deconstruct dimensions (e.g., [16, 100] for live, [16, 7200] for cold path)
    const [numBins, numFrames] = shape;
    
    // 1. Create offscreen buffer canvas matching exact data dimensions
    const offscreenCanvas = document.createElement("canvas");
    offscreenCanvas.width = numFrames;
    offscreenCanvas.height = numBins;
    const offscreenCtx = offscreenCanvas.getContext("2d");
    
    const imgData = offscreenCtx.createImageData(numFrames, numBins);
    
    for (let bin = 0; bin < numBins; bin++) {
        for (let frame = 0; frame < numFrames; frame++) {
            // Read value safely whether data is passed as flat Array or 2D Array
            const val = Array.isArray(data[0]) ? data[bin][frame] : data[bin * numFrames + frame];
            
            // Normalize float [-3, +3] to green intensity [0, 255]
            let intensity = Math.floor(((val + 3) / 6) * 255);
            intensity = Math.max(0, Math.min(255, intensity));
            
            // Flip row vertically so low frequencies sit at the bottom
            const flippedBin = numBins - 1 - bin;
            const pixelIndex = (flippedBin * numFrames + frame) * 4;
            
            imgData.data[pixelIndex]     = 0;         // Red
            imgData.data[pixelIndex + 1] = intensity; // Green Glow
            imgData.data[pixelIndex + 2] = 0;         // Blue
            imgData.data[pixelIndex + 3] = 255;       // Alpha
        }
    }
    
    // Write image buffer to offscreen canvas
    offscreenCtx.putImageData(imgData, 0, 0);
    
    // 2. Upscale onto visible canvas using GPU Bilinear Filtering
    visibleCtx.clearRect(0, 0, visibleCanvas.width, visibleCanvas.height);
    visibleCtx.imageSmoothingEnabled = true;
    visibleCtx.imageSmoothingQuality = "high";
    visibleCtx.drawImage(offscreenCanvas, 0, 0, visibleCanvas.width, visibleCanvas.height);
}

// cold path spectrogram rendering
function renderSpectrogramCanvas(data, shape, canvasId) {
    const canvas = document.getElementById(canvasId);
    const ctx = canvas.getContext('2d');
    
    // Deconstruct the array shape from npyjs ([rows, columns])
    const [numBins, numFrames] = shape;
    
    // Set the canvas resolution to match your data dimensions exactly
    canvas.width = numFrames;
    canvas.height = numBins;
    
    // Create an empty off-screen pixel array buffer
    const imageData = ctx.createImageData(numFrames, numBins);
    
    for (let bin = 0; bin < numBins; bin++) {
        for (let frame = 0; frame < numFrames; frame++) {
            // Locate flat index in row-major numpy array
            const flatIndex = bin * numFrames + frame;
            const val = data[flatIndex];
            
            // Map standardized floats to standard color byte (0-255)
            const intensity = Math.max(0, Math.min(255, (val + 3) * 42.5));
            
            // Flip the bin vertically so low frequencies sit at the bottom of the canvas
            const flippedBin = numBins - 1 - bin;
            const pixelIndex = (flippedBin * numFrames + frame) * 4;
            
            // Write RGBA values directly to pixel buffer
            imageData.data[pixelIndex]     = intensity; // Red
            imageData.data[pixelIndex + 1] = intensity; // Green
            imageData.data[pixelIndex + 2] = intensity; // Blue
            imageData.data[pixelIndex + 3] = 255;       // Alpha (Fully opaque)
        }
    }
    
    // Commit the entire pixel buffer to the canvas in a single draw call
    ctx.putImageData(imageData, 0, 0);
}

// when websocket receives message
ws.onmessage = function(event) {
    // parse the data from the main.py backend, which is on the other end of the websocket connection
    const incomingData = JSON.parse(event.data);

    //render spectrogram
    if (incomingData.spectrogram_latest100frames) {
        renderSpectrogram(incomingData.spectrogram_latest100frames.data.flat(), incomingData.spectrogram_latest100frames.shape, );
    }
    const t60Params = incomingData.t60_bapes.params[0].flat();
    const t60Quantiles = incomingData.t60_bapes.quantiles[0].flat();

    const c50Params = incomingData.c50_bapes.params[0].flat();
    const c50Quantiles = incomingData.c50_bapes.quantiles[0].flat();
    // drawChart(), the D3.js script, expects a time counter and two one-dimensional arrays (correct?)
    // main.py sends nested arrays like [[[val1, val2, val3]]]
    // grab the first bacth [0] and flatten to a 1D array
    const newWindow = {
        timestamp_step: timeCounter,
        time: `${timeCounter.toFixed(1)} – ${(timeCounter + 4).toFixed(1)} seconds`,

        t60_params: t60Params,
        t60_quantiles: t60Quantiles,
        
        c50_params: c50Params,
        c50_quantiles: c50Quantiles
    };

    // increase the time counter by 200ms for every websocket message
    timeCounter += 0.2;

    // streaming windows are pushed to the currentTimelineData array
    currentTimelineData.push(newWindow);

    // Log performance metrics
    console.log(`Inference took: ${incomingData.inference_time_ms} ms`);

    // unhide result area
    resultArea.classList.remove('hidden');

    // display JSON in frontend
    jsonResult.innerText = JSON.stringify(incomingData, null, 2);


    // as we stream every 200ms / 5 data points per second / at 5Hz, we instruct the D3 frontend to render 300 SVG paths per minute, which might lead to a lag
    // to prevent the DOM from breaking under the payload, a 10s rollingHistory is created which instructs the D3 function to only render the last 50 data points / 10 seconds 
    const rollingHistory = currentTimelineData.slice(-50);

    // draw charts
    drawChart(rollingHistory, 't60_params', 't60-chart-container', 'T60 Decay (Seconds)');
    drawChart(rollingHistory, 'c50_params', 'c50-chart-container', 'C50 Clarity (dB)');
};

// re-render D3 graphs on window resize
let resizeTimer;
window.addEventListener("resize", () => {
    clearTimeout(resizeTimer);
    resizeTimer = setTimeout(() => {
        const rollingHistory = currentTimelineData.slice(-50);   // recompute, module-scoped source
        if (rollingHistory.length) {                              // .length, not truthiness
            drawChart(rollingHistory, 't60_params', 't60-chart-container', 'T60 Decay (Seconds)');
            drawChart(rollingHistory, 'c50_params', 'c50-chart-container', 'C50 Clarity (dB)');
        }
    }, 200);
});


// HELPER: Convert raw Float32 array to a 16-bit PCM WAV Blob, less loss than using the MediaRecorder compression
function encodeWav(samples, sampleRate) {
    const buffer = new ArrayBuffer(44 + samples.length * 2);
    const view = new DataView(buffer);

    /* RIFF identifier */
    writeString(view, 0, 'RIFF');
    /* file length */
    view.setUint32(4, 36 + samples.length * 2, true);
    /* RIFF type */
    writeString(view, 8, 'WAVE');
    /* format chunk identifier */
    writeString(view, 12, 'fmt ');
    /* format chunk length */
    view.setUint32(16, 16, true);
    /* sample format (raw PCM = 1) */
    view.setUint16(20, 1, true);
    /* channel count (Mono = 1) */
    view.setUint16(22, 1, true);
    /* sample rate */
    view.setUint32(24, sampleRate, true);
    /* byte rate (sample rate * block align) */
    view.setUint32(28, sampleRate * 2, true);
    /* block align */
    view.setUint16(32, 2, true);
    /* bits per sample (16) */
    view.setUint16(34, 16, true);
    /* data chunk identifier */
    writeString(view, 36, 'data');
    /* data chunk length */
    view.setUint32(40, samples.length * 2, true);

    // Scale float samples [-1.0, 1.0] to 16-bit signed integers [-32768, 32767]
    let offset = 44;
    for (let i = 0; i < samples.length; i++, offset += 2) {
        let s = Math.max(-1, Math.min(1, samples[i]));
        let val = s < 0 ? s * 0x8000 : s * 0x7FFF;
        view.setInt16(offset, val, true);
    }

    return new Blob([view], { type: 'audio/wav' });
}

function writeString(view, offset, string) {
    for (let i = 0; i < string.length; i++) {
        view.setUint8(offset + i, string.charCodeAt(i));
    }
}
