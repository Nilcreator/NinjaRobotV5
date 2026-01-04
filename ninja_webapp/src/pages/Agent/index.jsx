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
    const messagesEndRef = useRef(null);
    const wsRef = useRef(null);

    // Scroll to bottom when new messages arrive
    useEffect(() => {
        messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
    }, [messages]);

    // Connect to distance WebSocket
    useEffect(() => {
        const connectWs = () => {
            const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
            const wsUrl = `${protocol}//${window.location.host}/ws/distance`;

            try {
                wsRef.current = new WebSocket(wsUrl);

                wsRef.current.onmessage = (event) => {
                    const data = JSON.parse(event.data);
                    if (data.distance !== undefined) {
                        setDistance(data.distance);
                    }
                };

                wsRef.current.onerror = () => {
                    console.log('Distance WebSocket error');
                };
            } catch (e) {
                console.log('WebSocket not available');
            }
        };

        connectWs();

        return () => {
            if (wsRef.current) {
                wsRef.current.close();
            }
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
        } catch (error) {
            setMessages(prev => [...prev, {
                role: 'assistant',
                content: 'Error: Could not connect to robot.'
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

    const triggerAction = async (type, name) => {
        try {
            await fetch(`/api/${type}/${name}`, { method: 'POST' });
        } catch (error) {
            console.error(`Failed to trigger ${type}/${name}:`, error);
        }
    };

    return (
        <div className={styles.agent}>
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

                {/* Input Area */}
                <div className={styles.inputArea}>
                    <input
                        type="text"
                        value={input}
                        onChange={(e) => setInput(e.target.value)}
                        onKeyPress={handleKeyPress}
                        placeholder={t('agent.placeholder')}
                        className={styles.input}
                        disabled={isLoading}
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
                        {['happy', 'sad', 'angry', 'surprised'].map(expr => (
                            <IconButton
                                key={expr}
                                icon={expr === 'happy' ? '😊' : expr === 'sad' ? '😢' : expr === 'angry' ? '😠' : '😲'}
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
                        {['startup', 'success', 'error', 'alert'].map(sound => (
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
                        {['wave', 'bow', 'dance'].map(move => (
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
        </div>
    );
}

export default Agent;
