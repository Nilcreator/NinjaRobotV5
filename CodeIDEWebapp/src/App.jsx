/**
 * @file App.jsx
 * @description Root application component with React Router configuration.
 * Defines the main routing structure for the NinjaRobot Code IDE.
 * 
 * Routes:
 * - "/" (Home): Landing page with features overview
 * - "/editor": Main Blockly IDE with BLE connectivity
 * - "/help": Documentation and troubleshooting
 * 
 * @see DevelopmentGuide.md for full documentation
 */

import { BrowserRouter, Routes, Route } from 'react-router-dom';
import { Layout } from './components/layout';
import Home from './pages/Home';
import Editor from './pages/Editor';
import Help from './pages/Help';
import './index.css';

/**
 * Root App component.
 * Wraps the application in BrowserRouter and defines route structure.
 * @returns {JSX.Element} The application root
 */
function App() {
  return (
    <BrowserRouter>
      <Routes>
        {/* Layout provides Header/Footer shell for all pages */}
        <Route path="/" element={<Layout />}>
          <Route index element={<Home />} />
          <Route path="editor" element={<Editor />} />
          <Route path="help" element={<Help />} />
        </Route>
      </Routes>
    </BrowserRouter>
  );
}

export default App;
