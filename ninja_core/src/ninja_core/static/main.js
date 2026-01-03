document.addEventListener('DOMContentLoaded', () => {
    // --- Element Selectors ---
    const movementsSelect = document.getElementById('movements-select');
    const expressionsSelect = document.getElementById('expressions-select');
    const emotionsSelect = document.getElementById('emotions-select');
    const distanceDisplay = document.getElementById('distance-display');
    const executeMovementBtn = document.getElementById('execute-movement-btn');
    const showExpressionBtn = document.getElementById('show-expression-btn');
    const playEmotionBtn = document.getElementById('play-emotion-btn');
    const setApiKeyBtn = document.getElementById('set-api-key-btn');
    const chatContainer = document.getElementById('chat-container');
    const logControls = document.getElementById('log-controls');
    const chatHistory = document.getElementById('chat-history');
    const chatInput = document.getElementById('chat-input');
    const chatSendBtn = document.getElementById('chat-send-btn');
    const systemLog = document.getElementById('system-log');
    const micButton = document.getElementById('micButton');
    const langSelect = document.getElementById('lang-select');

    // --- Translations ---
    const translations = {
        'en-US': {
            status_online: 'Online',
            sensor_title: 'Distance Sensor',
            servo_title: 'Servo Movements',
            expression_title: 'Facial Expressions',
            sound_title: 'Emotion Sounds',
            agent_title: 'Ninja AI Agent',
            log_title: 'System Log',
            system_title: 'System Controls',
            btn_execute: 'Execute',
            btn_show: 'Show',
            btn_play: 'Play',
            btn_set_apikey: 'Set/Update AI API Key',
            btn_send: 'Send',
            chat_placeholder: 'Ask the robot to do something...',
            slider_text: 'Slide to Power Off'
        },
        'ja-JP': {
            status_online: 'オンライン',
            sensor_title: '距離センサー',
            servo_title: 'サーボ動作',
            expression_title: '表情',
            sound_title: '感情音',
            agent_title: 'Ninja AIエージェント',
            log_title: 'システムログ',
            system_title: 'システム制御',
            btn_execute: '実行',
            btn_show: '表示',
            btn_play: '再生',
            btn_set_apikey: 'APIキー設定/更新',
            btn_send: '送信',
            chat_placeholder: 'ロボットに何か頼んでください...',
            slider_text: 'スライドして電源オフ'
        },
        'zh-TW': {
            status_online: '連線中',
            sensor_title: '距離感測器',
            servo_title: '伺服馬達動作',
            expression_title: '臉部表情',
            sound_title: '情感音效',
            agent_title: 'Ninja AI 代理',
            log_title: '系統日誌',
            system_title: '系統控制',
            btn_execute: '執行',
            btn_show: '顯示',
            btn_play: '播放',
            btn_set_apikey: '設定/更新 API 金鑰',
            btn_send: '發送',
            chat_placeholder: '請指示機器人做些什麼...',
            slider_text: '滑動以關閉電源'
        },
        'zh-CN': {
            status_online: '在线',
            sensor_title: '距离传感器',
            servo_title: '舵机动作',
            expression_title: '面部表情',
            sound_title: '情感音效',
            agent_title: 'Ninja AI 代理',
            log_title: '系统日志',
            system_title: '系统控制',
            btn_execute: '执行',
            btn_show: '显示',
            btn_play: '播放',
            btn_set_apikey: '设置/更新 API 密钥',
            btn_send: '发送',
            chat_placeholder: '请指示机器人做些什么...',
            slider_text: '滑动以关闭电源'
        }
    };

    function updateLanguage(lang) {
        const t = translations[lang] || translations['en-US'];

        // Update text content
        document.querySelectorAll('[data-i18n]').forEach(el => {
            const key = el.getAttribute('data-i18n');
            if (t[key]) el.textContent = t[key];
        });

        // Update placeholders
        document.querySelectorAll('[data-i18n-placeholder]').forEach(el => {
            const key = el.getAttribute('data-i18n-placeholder');
            if (t[key]) el.placeholder = t[key];
        });
    }

    langSelect.addEventListener('change', (e) => {
        updateLanguage(e.target.value);
    });

    // --- Speech Recognition Setup ---
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    let recognition = null;
    let isRecording = false;
    let recordingTimeout = null;

    if (SpeechRecognition) {
        recognition = new SpeechRecognition();
        recognition.continuous = false;
        recognition.interimResults = false;

        recognition.onstart = () => {
            isRecording = true;
            micButton.classList.add('recording');
            appendLog("Voice recording started...");
            // Auto-stop after 30 seconds
            recordingTimeout = setTimeout(() => {
                if (isRecording) {
                    recognition.stop();
                    appendLog("Voice recording timed out (30s).");
                }
            }, 30000);
        };

        recognition.onend = () => {
            isRecording = false;
            micButton.classList.remove('recording');
            if (recordingTimeout) clearTimeout(recordingTimeout);
            appendLog("Voice recording ended.");
        };

        recognition.onresult = (event) => {
            const transcript = event.results[0][0].transcript;
            chatInput.value = transcript;
            appendLog(`Recognized: "${transcript}"`);
        };

        recognition.onerror = (event) => {
            console.error("Speech recognition error", event.error);
            appendLog(`Voice Error: ${event.error}`);
            isRecording = false;
            micButton.classList.remove('recording');
        };

        micButton.addEventListener('click', () => {
            if (isRecording) {
                recognition.stop();
            } else {
                recognition.lang = langSelect.value;
                try {
                    recognition.start();
                } catch (e) {
                    appendLog(`Could not start recording: ${e.message}`);
                }
            }
        });
    } else {
        micButton.style.display = 'none';
        langSelect.style.display = 'none';
        console.log("Web Speech API not supported in this browser.");
    }

    // --- Generic API Call Functions ---
    async function fetchApi(endpoint, options = {}) {
        try {
            const response = await fetch(endpoint, options);
            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.detail || `API call failed`);
            }
            return await response.json();
        } catch (error) {
            console.error(`API Error for ${endpoint}:`, error);
            appendMessage('system-error', `Error: ${error.message}`);
            throw error;
        }
    }

    // --- UI & Data Loading ---
    async function populateSelect(select, endpoint, key) {
        try {
            const data = await fetchApi(`/api/${endpoint}`);
            select.innerHTML = '';
            data[key].forEach(item => {
                const option = document.createElement('option');
                option.value = item;
                option.textContent = item.charAt(0).toUpperCase() + item.slice(1);
                select.appendChild(option);
            });
        } catch (e) { console.error(`Failed to load ${key}.`); }
    }

    function appendMessage(sender, text) {
        const el = document.createElement('div');
        el.classList.add('chat-message', `chat-message-${sender}`);
        el.textContent = text;
        chatHistory.appendChild(el);
        chatHistory.scrollTop = chatHistory.scrollHeight;
    }

    function appendLog(text) {
        systemLog.textContent += `[${new Date().toLocaleTimeString()}] ${text}\n`;
        systemLog.scrollTop = systemLog.scrollHeight;
    }

    function showChatInterface(show) {
        if (show) {
            setApiKeyBtn.style.display = 'none';
            chatContainer.style.display = 'block';
            logControls.style.display = 'block';
        } else {
            setApiKeyBtn.style.display = 'block';
            chatContainer.style.display = 'none';
            logControls.style.display = 'none';
        }
    }

    // --- Event Listeners ---
    executeMovementBtn.addEventListener('click', async () => {
        try {
            await fetchApi(`/api/servos/movements/${movementsSelect.value}/execute`, { method: 'POST' });
            appendLog(`Executed movement: ${movementsSelect.value}`);
        } catch (e) { /* Error logged by fetchApi */ }
    });

    showExpressionBtn.addEventListener('click', () => fetchApi(`/api/display/expressions/${expressionsSelect.value}`, { method: 'POST' }));
    playEmotionBtn.addEventListener('click', () => fetchApi(`/api/sound/emotions/${emotionsSelect.value}`, { method: 'POST' }));

    setApiKeyBtn.addEventListener('click', async () => {
        const apiKey = prompt('Please enter your Gemini API key:');
        if (apiKey && apiKey.trim()) {
            try {
                await fetchApi('/api/agent/set_api_key', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ api_key: apiKey })
                });
                showChatInterface(true);
                appendMessage('system-info', 'Ninja AI activated.');
            } catch (e) { /* Error handled in fetchApi */ }
        }
    });

    async function handleChatSend() {
        const message = chatInput.value.trim();
        if (!message) return;

        appendMessage('user', message);
        chatInput.value = '';

        try {
            const result = await fetchApi('/api/agent/chat', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ message })
            });
            if (result) {
                if (result.response) appendMessage('agent', result.response);
                if (result.log) appendLog(result.log);
            }
        } catch (error) {
            // Error is already logged by fetchApi and displayed in chat
        }
    }

    chatSendBtn.addEventListener('click', handleChatSend);
    chatInput.addEventListener('keypress', (e) => { if (e.key === 'Enter') handleChatSend(); });

    // --- Slider Logic ---
    const sliderContainer = document.getElementById('power-off-slider');
    const sliderThumb = document.getElementById('slider-thumb');
    const sliderText = document.querySelector('.slider-text');
    let isDragging = false;
    let startX = 0;
    let currentX = 0;

    if (sliderContainer && sliderThumb) {
        const maxSlide = sliderContainer.clientWidth - sliderThumb.clientWidth - 8; // 8px padding

        function startDrag(e) {
            isDragging = true;
            startX = (e.type === 'touchstart') ? e.touches[0].clientX : e.clientX;
            sliderThumb.style.transition = 'none';
        }

        function onDrag(e) {
            if (!isDragging) return;
            e.preventDefault(); // Prevent scrolling on touch

            const clientX = (e.type === 'touchmove') ? e.touches[0].clientX : e.clientX;
            let delta = clientX - startX;

            // Clamp value
            if (delta < 0) delta = 0;
            if (delta > maxSlide) delta = maxSlide;

            currentX = delta;
            sliderThumb.style.transform = `translateX(${delta}px)`;

            // Fade text
            const opacity = 1 - (delta / maxSlide);
            sliderText.style.opacity = opacity;
        }

        function endDrag() {
            if (!isDragging) return;
            isDragging = false;
            sliderThumb.style.transition = 'transform 0.3s ease';

            if (currentX >= maxSlide * 0.9) {
                // Trigger Shutdown
                sliderThumb.style.transform = `translateX(${maxSlide}px)`;
                sliderText.style.opacity = 0;
                triggerShutdown();
            } else {
                // Reset
                sliderThumb.style.transform = 'translateX(0)';
                sliderText.style.opacity = 1;
            }
        }

        sliderThumb.addEventListener('mousedown', startDrag);
        sliderThumb.addEventListener('touchstart', startDrag);

        document.addEventListener('mousemove', onDrag);
        document.addEventListener('touchmove', onDrag, { passive: false });

        document.addEventListener('mouseup', endDrag);
        document.addEventListener('touchend', endDrag);
    }

    async function triggerShutdown() {
        if (confirm("Are you sure you want to safely shut down the robot?")) {
            try {
                const response = await fetchApi('/api/system/shutdown', { method: 'POST' });
                alert("Shutting down... Please wait for the green light to turn off before unplugging.");
                document.body.innerHTML = "<div style='display:flex;justify-content:center;align-items:center;height:100vh;color:white;background:#141414;'><h1>System is shutting down...</h1></div>";
            } catch (error) {
                // Reset slider if failed
                sliderThumb.style.transform = 'translateX(0)';
                sliderText.style.opacity = 1;
            }
        } else {
            // Reset slider if cancelled
            sliderThumb.style.transform = 'translateX(0)';
            sliderText.style.opacity = 1;
        }
    }

    // --- Initialization ---
    async function init() {
        populateSelect(movementsSelect, 'servos/movements', 'movements');
        populateSelect(expressionsSelect, 'display/expressions', 'expressions');
        populateSelect(emotionsSelect, 'sound/emotions', 'emotions');

        try {
            const status = await fetchApi('/api/agent/status');
            showChatInterface(status.active);
        } catch (e) {
            showChatInterface(false);
        }

        // Distance sensor WebSocket
        const wsProtocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        const distanceSocket = new WebSocket(`${wsProtocol}//${window.location.host}/ws/distance`);
        distanceSocket.onmessage = (event) => {
            distanceDisplay.textContent = `${JSON.parse(event.data).distance_mm} mm`;
        };
        distanceSocket.onerror = () => distanceDisplay.textContent = 'Error';
        distanceSocket.onclose = () => distanceDisplay.textContent = 'Disconnected';

        // Event/Chat WebSocket - Receives broadcasts from Dispatcher
        const eventSocket = new WebSocket(`${wsProtocol}//${window.location.host}/ws/events`);

        eventSocket.onopen = () => {
            console.log('[WS] Event socket connected');
            appendLog('Real-time event stream connected.');
        };

        eventSocket.onmessage = (event) => {
            const msg = JSON.parse(event.data);
            console.log('[WS] Received:', msg);

            if (msg.type === 'chat') {
                // Show all agent/ninja messages in chat
                if (msg.sender === 'ninja') {
                    appendMessage('agent', msg.text);
                }
                // Optionally show BLE user inputs (from other devices)
                // else if (msg.sender === 'user') { appendMessage('user', msg.text); }
            } else if (msg.type === 'execution_log') {
                appendLog(`[CODE] ${msg.content}`);
            } else if (msg.type === 'execution_status') {
                appendLog(`[STATUS] ${msg.status}: ${msg.message || ''}`);
            } else if (msg.type === 'execute_received') {
                appendLog(`[RECV] Code received (${msg.code_length} chars)`);
            }
        };

        eventSocket.onerror = (err) => {
            console.error('[WS] Event socket error:', err);
            appendLog('Event stream error.');
        };

        eventSocket.onclose = () => {
            console.log('[WS] Event socket closed');
            appendLog('Event stream disconnected.');
        };
    }

    init();
});
