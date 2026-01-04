/**
 * @file Agent/index.jsx
 * @description Agent page with AI chat interface and hardware controls.
 * Uses WebSocket for real-time streaming.
 */

import { useState, useRef, useEffect } from 'react';
import { useTranslation } from 'react-i18next';
import Button from '../../components/common/Button';
import IconButton from '../../components/common/IconButton';
import styles from './Agent.module.css';

function Agent() {
    const { t, i18n } = useTranslation();
    const [messages, setMessages] = useState([]);
    const [input, setInput] = useState('');
    const [isLoading, setIsLoading] = useState(false);
    const [distance, setDistance] = useState(null);
    const [isRecording, setIsRecording] = useState(false);
    const [logs, setLogs] = useState([]);
    const messagesEndRef = useRef(null);
    const logsEndRef = useRef(null);
    const mediaRecorderRef = useRef(null);
    const audioChunksRef = useRef([]);

    // Scroll to bottom when new messages arrive
    useEffect(() => {
        messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
    }, [messages]);

    // Connect to WebSockets (Distance & Events)
    useEffect(() => {
        let distanceWs;
        let eventsWs;
        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';

        const connectDistance = () => {
            const wsUrl = `${protocol}//${window.location.host}/ws/distance`;
            try {
                distanceWs = new WebSocket(wsUrl);
                distanceWs.onmessage = (event) => {
                    const data = JSON.parse(event.data);
                    if (data.distance_mm !== undefined) {
                        setDistance(data.distance_mm);
                    } else if (data.distance !== undefined) {
                        setDistance(data.distance);
                    }
                };
            } catch (e) {
                console.error("Distance WS Error", e);
            }
        };

        const connectEvents = () => {
            const wsUrl = `${protocol}//${window.location.host}/ws/events`;
            try {
                eventsWs = new WebSocket(wsUrl);
                eventsWs.onmessage = (event) => {
                    try {
                        // Attempt to parse as JSON
                        const data = JSON.parse(event.data);
                        // Add to internal logs state
                        const timestamp = new Date().toLocaleTimeString();
                        const logEntry = typeof data === 'string' ? data : JSON.stringify(data);
                        setLogs(prev => [...prev, `[${timestamp}] ${logEntry}`].slice(-50)); // Keep last 50 logs
                    } catch {
                        // Plain text fallback
                        const timestamp = new Date().toLocaleTimeString();
                        setLogs(prev => [...prev, `[${timestamp}] ${event.data}`].slice(-50));
                    }
                };
            } catch (e) {
                console.error("Events WS Error", e);
            }
        };

        connectDistance();
        connectEvents();

        return () => {
            if (distanceWs) distanceWs.close();
            if (eventsWs) eventsWs.close();
        };
    }, []);

    const sendMessage = async () => {
        if (!input.trim() || isLoading) return;

        const userMessage = input.trim();
        setInput('');
        setMessages(prev => [...prev, { role: 'user', content: userMessage }]);
        setIsLoading(true);

        try {
            const response = await fetch('/api/agent/chat', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    message: userMessage,
                    language: i18n.language
                }),
            });

            const data = await response.json();
            setMessages(prev => [...prev, { role: 'assistant', content: data.response }]);
            if (data.log) {
                console.log("Agent Log:", data.log);
            }
        } catch {
            setMessages(prev => [...prev, {
                role: 'assistant',
                content: t('agent.error') || 'Error: Could not connect to robot.'
            }]);
        } finally {
            setIsLoading(false);
        }
    };

    const handleKeyPress = (e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            sendMessage();
        }
    };

    // Voice Input Handler
    const toggleVoiceRecording = async () => {
        if (isRecording) {
            // Stop recording
            mediaRecorderRef.current?.stop();
            setIsRecording(false);
        } else {
            // Start recording
            try {
                const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
                const mediaRecorder = new MediaRecorder(stream);
                mediaRecorderRef.current = mediaRecorder;
                audioChunksRef.current = [];

                mediaRecorder.ondataavailable = (event) => {
                    if (event.data.size > 0) {
                        audioChunksRef.current.push(event.data);
                    }
                };

                mediaRecorder.onstop = async () => {
                    const audioBlob = new Blob(audioChunksRef.current, { type: 'audio/wav' }); // or 'audio/webm' depending on browser
                    // In a real implementation, we would send this blob to /api/agent/voice
                    // For now, let's assume the API accepts formData
                    const formData = new FormData();
                    formData.append('file', audioBlob);

                    setIsLoading(true);
                    try {
                        const response = await fetch('/api/agent/voice', {
                            method: 'POST',
                            body: formData
                        });
                        const data = await response.json();
                        if (data.transcription) {
                            setMessages(prev => [...prev, { role: 'user', content: `🎤 ${data.transcription}` }]);
                        }
                        if (data.response) {
                            setMessages(prev => [...prev, { role: 'assistant', content: data.response }]);
                        }
                    } catch (error) {
                        console.error("Voice upload failed", error);
                        setMessages(prev => [...prev, { role: 'assistant', content: "Error processing voice command." }]);
                    } finally {
                        setIsLoading(false);
                        // Stop tracks to release mic
                        stream.getTracks().forEach(track => track.stop());
                    }
                };

                mediaRecorder.start();
                setIsRecording(true);
            } catch (err) {
                console.error("Error accessing microphone:", err);
                alert("Could not access microphone.");
            }
        }
    };

    // Auto-scroll logs
    useEffect(() => {
        logsEndRef.current?.scrollIntoView({ behavior: 'smooth' });
    }, [logs]);

    const triggerAction = async (type, name) => {
        // Map simplified types to actual API endpoints
        // 'expressions' -> 'display/expressions'
        // 'sounds' -> 'sound/emotions'
        // 'movements' -> 'servos/movements'

        let apiPath = '';
        let method = 'POST';

        switch (type) {
            case 'expressions':
                apiPath = `/api/display/expressions/${name}`;
                break;
            case 'sounds':
                apiPath = `/api/sound/emotions/${name}`;
                break;
            case 'movements':
                apiPath = `/api/servos/movements/${name}/execute`;
                break;
            default:
                console.error("Unknown action type:", type);
                return;
        }

        try {
            await fetch(apiPath, { method });
        } catch (error) {
            console.error(`Failed to trigger ${type}/${name}:`, error);
        }
    };

    return (
        <div className={styles.agent}>
            {/* Main Content Area - Split into Chat and Logs if needed, but for now just Chat */}
            <div className={styles.chatArea}>
                <div className={styles.messages}>
                    {messages.length === 0 && (
                        <div className={styles.welcome}>
                            <span className={styles.welcomeIcon}>🥷</span>
                            <p>{t('agent.title')}</p>
                        </div>
                    )}
                    {messages.map((msg, idx) => (
                        <div
                            key={idx}
                            className={`${styles.message} ${styles[msg.role]}`}
                        >
                            {msg.content}
                        </div>
                    ))}
                    {isLoading && (
                        <div className={`${styles.message} ${styles.assistant}`}>
                            <span className={styles.typing}>...</span>
                        </div>
                    )}
                    <div ref={messagesEndRef} />
                </div>

                {/* System Log Panel */}
                <div className={styles.logPanel}>
                    <div className={styles.logHeader}>System Log</div>
                    <div className={styles.logContent}>
                        {logs.length === 0 && <div className={styles.logPlaceholder}>System events will appear here...</div>}
                        {logs.map((log, i) => (
                            <div key={i} className={styles.logEntry}>{log}</div>
                        ))}
                        <div ref={logsEndRef} />
                    </div>
                </div>

                {/* Input Area */}
                <div className={styles.inputArea}>
                    <IconButton
                        icon={isRecording ? "⏹️" : "🎤"}
                        onClick={toggleVoiceRecording}
                        className={isRecording ? styles.recordingBtn : ""}
                        title="Voice Input"
                    />
                    <input
                        type="text"
                        value={input}
                        onChange={(e) => setInput(e.target.value)}
                        onKeyPress={handleKeyPress}
                        placeholder={t('agent.placeholder')}
                        className={styles.input}
                        disabled={isLoading || isRecording}
                    />
                    <Button
                        variant="primary"
                        onClick={sendMessage}
                        disabled={!input.trim() || isLoading}
                    >
                        {t('agent.send')}
                    </Button>
                </div>
            </div>

            {/* Controls Sidebar */}
            <div className={styles.controls}>
                {/* Distance Sensor */}
                <div className={styles.controlSection}>
                    <h3>📏 {t('agent.distance')}</h3>
                    <div className={styles.distanceValue}>
                        {distance !== null ? `${distance} ${t('agent.distanceUnit')}` : '---'}
                    </div>
                </div>

                {/* Expressions */}
                <div className={styles.controlSection}>
                    <h3>😊 {t('agent.expressions')}</h3>
                    <div className={styles.buttonGrid}>
                        {['idle', 'happy', 'laughing', 'sad', 'cry', 'angry', 'surprising', 'sleepy', 'speaking', 'shy', 'scary', 'exciting', 'confusing'].map(expr => (
                            <IconButton
                                key={expr}
                                icon="😊"
                                label={expr}
                                onClick={() => triggerAction('expressions', expr)}
                            />
                        ))}
                    </div>
                </div>

                {/* Sounds */}
                <div className={styles.controlSection}>
                    <h3>🔊 {t('agent.sounds')}</h3>
                    <div className={styles.buttonGrid}>
                        {['startup', 'happy', 'sad', 'exciting', 'angry', 'confusing', 'cry', 'embarrassing', 'idle', 'laughing', 'scary', 'shy', 'sleepy', 'speaking', 'surprising'].map(sound => (
                            <IconButton
                                key={sound}
                                icon="🎵"
                                label={sound}
                                onClick={() => triggerAction('sounds', sound)}
                            />
                        ))}
                    </div>
                </div>

                {/* Movements */}
                <div className={styles.controlSection}>
                    <h3>🤖 {t('agent.movements')}</h3>
                    <div className={styles.buttonGrid}>
                        {['wave', 'bow', 'dance', 'look_around', 'nod', 'shake_head'].map(move => (
                            <IconButton
                                key={move}
                                icon="🎭"
                                label={move}
                                onClick={() => triggerAction('movements', move)}
                            />
                        ))}
                    </div>
                </div>
            </div>

            {/* TODO: Add explicit LogPanel if space permits, or integrate into chat */}
        </div>
    );
}

export default Agent;
