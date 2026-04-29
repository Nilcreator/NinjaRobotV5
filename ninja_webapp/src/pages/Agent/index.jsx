/**
 * @file Agent/index.jsx
 * @description Agent page with AI chat interface and hardware controls.
 * Redesigned with V4-style elements and mobile-first layout.
 */

import { useState, useRef, useEffect } from 'react';
import { useTranslation } from 'react-i18next';
import Button from '../../components/common/Button';
import styles from './Agent.module.css';

function Agent() {
    const { t, i18n } = useTranslation();
    const [messages, setMessages] = useState([]);
    const [input, setInput] = useState('');
    const [pendingMessages, setPendingMessages] = useState(0);
    const [distance, setDistance] = useState(null);
    const [isRecording, setIsRecording] = useState(false);
    const [logs, setLogs] = useState([]);
    const [isLogPanelOpen, setIsLogPanelOpen] = useState(false);
    const messagesEndRef = useRef(null);
    const logsEndRef = useRef(null);
    const isLoading = pendingMessages > 0;

    // Scroll to bottom when new messages arrive
    useEffect(() => {
        messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
    }, [messages]);

    // Scroll log panel when new logs
    useEffect(() => {
        logsEndRef.current?.scrollIntoView({ behavior: 'smooth' });
    }, [logs]);

    // Connect to WebSockets
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
                    setDistance(data.distance_mm ?? data.distance ?? null);
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
                        const data = JSON.parse(event.data);
                        const timestamp = new Date().toLocaleTimeString();

                        if (data.type === 'execute_received') {
                            setMessages(prev => [...prev, {
                                role: 'system',
                                content: `📝 Code received (${data.code_length} chars):\n${data.full_code || ''}`
                            }]);
                            setLogs(prev => [...prev, `[${timestamp}] 📥 Code received via BLE`].slice(-50));
                        } else if (data.type === 'execution_status') {
                            setLogs(prev => [...prev, `[${timestamp}] ⚡ ${data.status}: ${data.message || ''}`].slice(-50));
                        } else {
                            const logEntry = typeof data === 'string' ? data : (data.message || JSON.stringify(data));
                            setLogs(prev => [...prev, `[${timestamp}] ${logEntry}`].slice(-50));
                        }
                    } catch {
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
        if (!input.trim()) return;

        const userMessage = input.trim();
        setInput('');
        setMessages(prev => [...prev, { role: 'user', content: userMessage }]);
        setPendingMessages(prev => prev + 1);

        try {
            const response = await fetch('/api/agent/chat', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ message: userMessage, language: i18n.language }),
            });
            const data = await response.json();
            setMessages(prev => [...prev, { role: 'assistant', content: data.response }]);
            if (data.log) {
                const timestamp = new Date().toLocaleTimeString();
                setLogs(prev => [...prev, `[${timestamp}] ${data.log}`].slice(-50));
            }
        } catch {
            setMessages(prev => [...prev, {
                role: 'assistant',
                content: t('agent.error') || 'Error: Could not connect.'
            }]);
        } finally {
            setPendingMessages(prev => Math.max(0, prev - 1));
        }
    };

    const handleKeyPress = (e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            sendMessage();
        }
    };

    // Voice Input
    const toggleVoiceRecording = () => {
        if (isRecording) {
            window.speechRecognitionInstance?.stop();
            setIsRecording(false);
            return;
        }

        const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
        if (!SpeechRecognition) {
            alert(t('agent.speechNotSupported') || "Speech Recognition not supported.");
            return;
        }

        const recognition = new SpeechRecognition();
        window.speechRecognitionInstance = recognition;

        const langMap = { 'en': 'en-US', 'ja': 'ja-JP', 'zh-TW': 'zh-TW', 'zh-CN': 'zh-CN' };
        recognition.lang = langMap[i18n.language] || 'en-US';
        recognition.interimResults = false;
        recognition.maxAlternatives = 1;

        recognition.onstart = () => setIsRecording(true);
        recognition.onend = () => setIsRecording(false);
        recognition.onresult = (event) => {
            const transcript = event.results[0][0].transcript;
            if (transcript) setInput(transcript);
        };
        recognition.onerror = () => setIsRecording(false);

        recognition.start();
    };

    // Hardware Control States
    const [expressionsList, setExpressionsList] = useState([]);
    const [soundsList, setSoundsList] = useState([]);
    const [movementsList, setMovementsList] = useState([]);
    const [selectedExpr, setSelectedExpr] = useState('');
    const [selectedSound, setSelectedSound] = useState('');
    const [selectedMove, setSelectedMove] = useState('');

    // Fetch Capabilities
    useEffect(() => {
        const fetchCapabilities = async () => {
            try {
                const [expRes, sndRes, movRes] = await Promise.all([
                    fetch('/api/display/expressions'),
                    fetch('/api/sound/emotions'),
                    fetch('/api/servos/movements')
                ]);
                if (expRes.ok) {
                    const data = await expRes.json();
                    setExpressionsList(data.expressions || []);
                    if (data.expressions?.length > 0) setSelectedExpr(data.expressions[0]);
                }
                if (sndRes.ok) {
                    const data = await sndRes.json();
                    setSoundsList(data.emotions || []);
                    if (data.emotions?.length > 0) setSelectedSound(data.emotions[0]);
                }
                if (movRes.ok) {
                    const data = await movRes.json();
                    setMovementsList(data.movements || []);
                    if (data.movements?.length > 0) setSelectedMove(data.movements[0]);
                }
            } catch (error) {
                console.error("Failed to fetch capabilities:", error);
            }
        };
        fetchCapabilities();
    }, []);

    const triggerAction = async (type, name) => {
        let apiPath = '';
        switch (type) {
            case 'expressions': apiPath = `/api/display/expressions/${name}`; break;
            case 'sounds': apiPath = `/api/sound/emotions/${name}`; break;
            case 'movements': apiPath = `/api/servos/movements/${name}/execute`; break;
            default: return;
        }
        try {
            await fetch(apiPath, { method: 'POST' });
            const timestamp = new Date().toLocaleTimeString();
            setLogs(prev => [...prev, `[${timestamp}] ${type}: ${name}`].slice(-50));
        } catch (error) {
            console.error(`Failed ${type}/${name}:`, error);
        }
    };

    return (
        <div className={styles.agentPage}>
            {/* Distance Sensor Card */}
            <div className={styles.sensorCard}>
                <h3>📏 {t('agent.distance')}</h3>
                <div className={styles.sensorValue}>
                    {distance !== null ? `${distance} mm` : '---'}
                </div>
            </div>

            {/* Chat Dialog Card */}
            <div className={styles.chatCard}>
                <div className={styles.chatMessages}>
                    {messages.length === 0 && (
                        <div className={styles.welcomeMessage}>
                            <p>{"Hi! I'm Ninja. Please enter your message or click the microphone to speak to me."}</p>
                        </div>
                    )}
                    {messages.map((msg, idx) => (
                        <div key={idx} className={`${styles.chatBubble} ${styles[msg.role]}`}>
                            {msg.role === 'system' ? (
                                <pre className={styles.codeBlock}>{msg.content}</pre>
                            ) : msg.content}
                        </div>
                    ))}
                    {isLoading && (
                        <div className={`${styles.chatBubble} ${styles.assistant}`}>
                            <span className={styles.typing}>...</span>
                        </div>
                    )}
                    <div ref={messagesEndRef} />
                </div>

                {/* Input Area */}
                <div className={styles.inputArea}>
                    <button
                        className={`${styles.micButton} ${isRecording ? styles.recording : ''}`}
                        onClick={toggleVoiceRecording}
                        title="Voice Input"
                    >
                        {isRecording ? '⏹️' : '🎤'}
                    </button>
                    <input
                        type="text"
                        value={input}
                        onChange={(e) => setInput(e.target.value)}
                        onKeyPress={handleKeyPress}
                        placeholder={t('agent.placeholder')}
                        className={styles.textInput}
                        disabled={isRecording}
                    />
                    <button
                        className={styles.sendButton}
                        onClick={sendMessage}
                        disabled={!input.trim()}
                    >
                        {t('agent.send')}
                    </button>
                </div>
            </div>

            {/* Hardware Controls */}
            <div className={styles.controlsGrid}>
                {/* Expressions */}
                <div className={styles.controlCard}>
                    <h3>😊 {t('agent.expressions')}</h3>
                    <div className={styles.controlRow}>
                        <select
                            className={styles.select}
                            value={selectedExpr}
                            onChange={(e) => setSelectedExpr(e.target.value)}
                        >
                            {expressionsList.map(expr => (
                                <option key={expr} value={expr}>{expr}</option>
                            ))}
                        </select>
                        <button
                            className={styles.execButton}
                            onClick={() => triggerAction('expressions', selectedExpr)}
                        >▶</button>
                    </div>
                </div>

                {/* Sounds */}
                <div className={styles.controlCard}>
                    <h3>🔊 {t('agent.sounds')}</h3>
                    <div className={styles.controlRow}>
                        <select
                            className={styles.select}
                            value={selectedSound}
                            onChange={(e) => setSelectedSound(e.target.value)}
                        >
                            {soundsList.map(sound => (
                                <option key={sound} value={sound}>{sound}</option>
                            ))}
                        </select>
                        <button
                            className={styles.execButton}
                            onClick={() => triggerAction('sounds', selectedSound)}
                        >▶</button>
                    </div>
                </div>

                {/* Movements */}
                <div className={styles.controlCard}>
                    <h3>🤖 {t('agent.movements')}</h3>
                    <div className={styles.controlRow}>
                        <select
                            className={styles.select}
                            value={selectedMove}
                            onChange={(e) => setSelectedMove(e.target.value)}
                        >
                            {movementsList.map(move => (
                                <option key={move} value={move}>{move}</option>
                            ))}
                        </select>
                        <button
                            className={styles.execButton}
                            onClick={() => triggerAction('movements', selectedMove)}
                        >▶</button>
                    </div>
                </div>
            </div>

            {/* Slidable Log Panel */}
            <div className={`${styles.logPanel} ${isLogPanelOpen ? styles.open : ''}`}>
                <button
                    className={styles.logPanelTab}
                    onClick={() => setIsLogPanelOpen(!isLogPanelOpen)}
                >
                    {isLogPanelOpen ? '▼' : '▲'} System Log ({logs.length})
                </button>
                <div className={styles.logContent}>
                    {logs.length === 0 ? (
                        <div className={styles.logPlaceholder}>Events will appear here...</div>
                    ) : (
                        logs.map((log, i) => (
                            <div key={i} className={styles.logEntry}>{log}</div>
                        ))
                    )}
                    <div ref={logsEndRef} />
                </div>
            </div>
        </div>
    );
}

export default Agent;
