/**
 * @file Agent/index.jsx
 * @description Agent page with AI chat interface, hardware controls, and slidable log panel.
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
    const [isLogPanelOpen, setIsLogPanelOpen] = useState(false);
    const messagesEndRef = useRef(null);
    const logsEndRef = useRef(null);

    // Scroll to bottom when new messages arrive
    useEffect(() => {
        messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
    }, [messages]);

    // Scroll log panel when new logs
    useEffect(() => {
        logsEndRef.current?.scrollIntoView({ behavior: 'smooth' });
    }, [logs]);

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
                        const data = JSON.parse(event.data);
                        const timestamp = new Date().toLocaleTimeString();

                        // Handle BLE code reception
                        if (data.type === 'execute_received') {
                            // Display code in chat
                            setMessages(prev => [...prev, {
                                role: 'system',
                                content: `📝 Code received via BLE (${data.code_length} chars):\n\`\`\`python\n${data.full_code || 'Code not available'}\n\`\`\``
                            }]);
                            setLogs(prev => [...prev, `[${timestamp}] 📥 Code received via BLE`].slice(-50));

                            // If there's a diagnosis, show it
                            if (data.diagnosis) {
                                setMessages(prev => [...prev, {
                                    role: 'assistant',
                                    content: `🔍 Code Diagnosis:\n${data.diagnosis}`
                                }]);
                            }
                        } else if (data.type === 'execution_status') {
                            setLogs(prev => [...prev, `[${timestamp}] ⚡ ${data.status}: ${data.message || ''}`].slice(-50));
                        } else if (data.type === 'execution_log') {
                            setLogs(prev => [...prev, `[${timestamp}] 📋 ${data.content}`].slice(-50));
                        } else {
                            const logEntry = typeof data === 'string' ? data : JSON.stringify(data);
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
                const timestamp = new Date().toLocaleTimeString();
                setLogs(prev => [...prev, `[${timestamp}] Agent: ${data.log}`].slice(-50));
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

    // Voice Input (SpeechRecognition)
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
        recognition.onerror = (event) => {
            console.error("Speech Recognition Error", event.error);
            setIsRecording(false);
            setLogs(prev => [...prev, `[Error] Speech: ${event.error}`].slice(-50));
        };

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
                console.error("Failed to fetch robot capabilities:", error);
            }
        };
        fetchCapabilities();
    }, []);

    // Hardware Action
    const triggerAction = async (type, name) => {
        let apiPath = '';
        switch (type) {
            case 'expressions': apiPath = `/api/display/expressions/${name}`; break;
            case 'sounds': apiPath = `/api/sound/emotions/${name}`; break;
            case 'movements': apiPath = `/api/servos/movements/${name}/execute`; break;
            default: return;
        }
        try {
            const res = await fetch(apiPath, { method: 'POST' });
            const data = await res.json();
            const timestamp = new Date().toLocaleTimeString();
            setLogs(prev => [...prev, `[${timestamp}] ${type}: ${name} - ${data.status || 'done'}`].slice(-50));
        } catch (error) {
            console.error(`Failed to trigger ${type}/${name}:`, error);
            const timestamp = new Date().toLocaleTimeString();
            setLogs(prev => [...prev, `[${timestamp}] Error: ${type}/${name} failed`].slice(-50));
        }
    };

    const handleExecute = (type) => {
        let name = '';
        if (type === 'expressions') name = selectedExpr;
        else if (type === 'sounds') name = selectedSound;
        else if (type === 'movements') name = selectedMove;
        if (!name) return;
        triggerAction(type, name);
    };

    return (
        <div className={styles.agent}>
            {/* Main Content Area */}
            <div className={styles.mainContent}>
                {/* Chat Area */}
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
                                {msg.role === 'system' ? (
                                    <pre className={styles.codeBlock}>{msg.content}</pre>
                                ) : (
                                    msg.content
                                )}
                            </div>
                        ))}
                        {isLoading && (
                            <div className={`${styles.message} ${styles.assistant}`}>
                                <span className={styles.typing}>...</span>
                            </div>
                        )}
                        <div ref={messagesEndRef} />
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
                            <Button onClick={() => handleExecute('expressions')}>Execute</Button>
                        </div>
                    </div>

                    {/* Sounds */}
                    <div className={styles.controlSection}>
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
                            <Button onClick={() => handleExecute('sounds')}>Execute</Button>
                        </div>
                    </div>

                    {/* Movements */}
                    <div className={styles.controlSection}>
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
                            <Button onClick={() => handleExecute('movements')}>Execute</Button>
                        </div>
                    </div>
                </div>
            </div>

            {/* Slidable Log Panel - Bottom */}
            <div className={`${styles.logPanelWrapper} ${isLogPanelOpen ? styles.open : ''}`}>
                <button
                    className={styles.logPanelTab}
                    onClick={() => setIsLogPanelOpen(!isLogPanelOpen)}
                >
                    {isLogPanelOpen ? '▼' : '▲'} {t('agent.systemLog') || 'System Log'} ({logs.length})
                </button>
                <div className={styles.logPanelContent}>
                    {logs.length === 0 && (
                        <div className={styles.logPlaceholder}>
                            System events will appear here...
                        </div>
                    )}
                    {logs.map((log, i) => (
                        <div key={i} className={styles.logEntry}>{log}</div>
                    ))}
                    <div ref={logsEndRef} />
                </div>
            </div>
        </div>
    );
}

export default Agent;
