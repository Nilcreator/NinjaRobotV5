/**
 * @file App.jsx
 * @description Root application component with React Router configuration.
 * 
 * Routes:
 * - "/" (Home): Landing page with quick actions
 * - "/agent": AI Chat interface (WebSocket)
 * - "/code": Blockly visual programming
 * - "/help": Documentation and troubleshooting
 */

import { BrowserRouter, Routes, Route } from 'react-router-dom';
import { BluetoothProvider } from './contexts/BluetoothContext';
import Layout from './components/layout/Layout';
import Home from './pages/Home';
import Agent from './pages/Agent';
import Code from './pages/Code';
import Help from './pages/Help';

function App() {
    return (
        <BluetoothProvider>
            <BrowserRouter>
                <Routes>
                    <Route path="/" element={<Layout />}>
                        <Route index element={<Home />} />
                        <Route path="agent" element={<Agent />} />
                        <Route path="code" element={<Code />} />
                        <Route path="help" element={<Help />} />
                    </Route>
                </Routes>
            </BrowserRouter>
        </BluetoothProvider>
    );
}

export default App;
