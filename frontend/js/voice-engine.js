/**
 * AutoMech AI - Voice Engine
 * Web Speech API for voice input/output with automotive jargon correction
 */
class VoiceEngine {
    constructor() {
        this.recognition = null;
        this.synthesis = window.speechSynthesis;
        this.isListening = false;
        this.isSupported = false;
        this.onResult = null;     // callback(text)
        this.onStart = null;      // callback()
        this.onEnd = null;        // callback()
        this.onError = null;      // callback(error)

        // Automotive jargon corrections for common voice misrecognitions
        this.corrections = {
            'break': 'brake', 'breaks': 'brakes', 'breaking': 'braking',
            'clutch plate': 'clutch disc', 'cluch': 'clutch',
            'oil leek': 'oil leak', 'leek': 'leak',
            'enginee': 'engine', 'engin': 'engine',
            'noisey': 'noisy', 'noyse': 'noise',
            'stearing': 'steering', 'steerin': 'steering',
            'overheeting': 'overheating', 'over heating': 'overheating',
            'battry': 'battery', 'batteri': 'battery',
            'altenator': 'alternator', 'alternater': 'alternator',
            'catylitic': 'catalytic', 'catalitic': 'catalytic',
            'radiater': 'radiator', 'radaitor': 'radiator',
            'excaust': 'exhaust', 'exaust': 'exhaust',
            'suspention': 'suspension', 'suspenion': 'suspension',
            'transmision': 'transmission', 'transmision': 'transmission',
            'termostat': 'thermostat', 'termostaat': 'thermostat',
            'caliper': 'caliper', 'calipre': 'caliper',
            'injector': 'injector', 'injecter': 'injector',
            'compresser': 'compressor', 'compresure': 'compressor',
            'cilinder': 'cylinder', 'sylinder': 'cylinder',
            'gaskit': 'gasket', 'gascket': 'gasket',
            'turbo charger': 'turbocharger',
            'abs': 'ABS', 'a b s': 'ABS',
            'rpam': 'RPM', 'rpm': 'RPM',
            'cng': 'CNG', 'lpg': 'LPG',
            'obd': 'OBD', 'o b d': 'OBD',
            'ecu': 'ECU', 'e c u': 'ECU',
            'dpf': 'DPF', 'd p f': 'DPF',
            'egr': 'EGR', 'e g r': 'EGR',
        };

        this._init();
    }

    _init() {
        const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
        if (!SpeechRecognition) {
            console.warn('Speech Recognition not supported');
            this.isSupported = false;
            return;
        }

        this.isSupported = true;
        this.recognition = new SpeechRecognition();
        this.recognition.lang = 'en-IN';        // Indian English
        this.recognition.continuous = false;
        this.recognition.interimResults = true;
        this.recognition.maxAlternatives = 3;

        this.recognition.onstart = () => {
            this.isListening = true;
            if (this.onStart) this.onStart();
        };

        this.recognition.onend = () => {
            this.isListening = false;
            if (this.onEnd) this.onEnd();
        };

        this.recognition.onerror = (event) => {
            console.error('Speech recognition error:', event.error);
            this.isListening = false;
            if (this.onError) this.onError(event.error);
            if (this.onEnd) this.onEnd();
        };

        this.recognition.onresult = (event) => {
            let finalTranscript = '';
            let interimTranscript = '';

            for (let i = event.resultIndex; i < event.results.length; i++) {
                const transcript = event.results[i][0].transcript;
                if (event.results[i].isFinal) {
                    finalTranscript += transcript;
                } else {
                    interimTranscript += transcript;
                }
            }

            if (finalTranscript) {
                const corrected = this._correctJargon(finalTranscript);
                if (this.onResult) this.onResult(corrected, true);
            } else if (interimTranscript) {
                if (this.onResult) this.onResult(interimTranscript, false);
            }
        };
    }

    start() {
        if (!this.isSupported) {
            if (this.onError) this.onError('not-supported');
            return;
        }
        if (this.isListening) return;
        
        try {
            // Unlock speech engine silently in user gesture context
            if (this.synthesis.state === 'suspended') {
                this.synthesis.resume();
            }
            
            // Send empty utterance to initialize audio context
            const unlock = new SpeechSynthesisUtterance('');
            unlock.volume = 0;
            // Catch error on speak if not allowed
            try { this.synthesis.speak(unlock); } catch(e) {}

            // Stop any ongoing speech synthesis
            this.synthesis.cancel();
            
            this.recognition.start();
        } catch (e) {
            console.error('Failed to start recognition:', e);
            if (this.onError) this.onError('start-failed');
        }
    }

    stop() {
        if (this.recognition && this.isListening) {
            this.recognition.stop();
        }
    }

    toggle() {
        if (this.isListening) {
            this.stop();
        } else {
            this.start();
        }
    }

    speak(text, callback) {
        if (!this.synthesis) return;
        
        let delay = 0;
        // Cancel any ongoing speech safely
        if (this.synthesis.speaking || this.synthesis.pending) {
            this.synthesis.cancel();
            delay = 150; // Give the browser time to clear the speech queue
        }

        setTimeout(() => {
            // Ensure synthesis is not paused
            if (this.synthesis.resume) this.synthesis.resume();

            const utterance = new SpeechSynthesisUtterance(text);
            
            // Bugfix: Prevent Garbage Collection of Utterance in WebKit/Chromium
            window.activeUtterance = utterance;

            utterance.lang = 'en-IN';
            utterance.rate = 1.05;
            utterance.pitch = 1.0;
            utterance.volume = 1.0;

            // Try to find an appropriate voice
            const voices = this.synthesis.getVoices();
            if (voices.length > 0) {
                const indianVoice = voices.find(v => v.lang.includes('en-IN') || v.lang.includes('en_IN'));
                const englishVoice = voices.find(v => v.lang.includes('en') && v.name.includes('Google'));
                const fallback = voices.find(v => v.lang.includes('en')) || voices[0];
                utterance.voice = indianVoice || englishVoice || fallback;
            } else {
                console.warn("No voices loaded yet. Browser OS default will be used.");
            }

            utterance.onstart = () => console.log("Started speaking:", text);
            utterance.onerror = (e) => {
                console.error("Speech error:", e.error);
                if (callback) callback();
            };

            utterance.onend = () => {
                if (callback) callback();
            };

            this.synthesis.speak(utterance);
        }, delay);
    }

    stopSpeaking() {
        if (this.synthesis) this.synthesis.cancel();
    }

    _correctJargon(text) {
        let corrected = text.toLowerCase();
        for (const [wrong, right] of Object.entries(this.corrections)) {
            const regex = new RegExp(`\\b${wrong}\\b`, 'gi');
            corrected = corrected.replace(regex, right);
        }
        return corrected;
    }
}
