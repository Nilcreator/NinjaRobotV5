/**
 * @file App.jsx
 * @description Root application component with React Router configuration.
 * 
 * Routes:
 * - "/" (Home): Landing page with quick actions and power-off slider
 * - "/agent": AI Chat interface (WebSocket)
 * - "/help": Documentation and troubleshooting
 */
import { BrowserRouter, Routes, Route } from 'react-router-dom';
import Layout from './components/layout/Layout';
import Home from './pages/Home';
import Agent from './pages/Agent';
import Help from './pages/Help';

function App() {
    return (
        <BrowserRouter>
            <Routes>
                <Route path="/" element={<Layout />}>
                    <Route index element={<Home />} />
                    <Route path="agent" element={<Agent />} />
                    <Route path="help" element={<Help />} />
                </Route>
            </Routes>
        </BrowserRouter>
    );
}

export default App;
