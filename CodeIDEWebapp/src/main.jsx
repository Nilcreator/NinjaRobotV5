/**
 * @file main.jsx
 * @description Application entry point for NinjaRobot Code IDE.
 * 
 * This file:
 * 1. Imports global CSS variables and styles
 * 2. Initializes i18next for internationalization
 * 3. Renders the React application in StrictMode
 * 
 * @see i18n.js for language configuration
 * @see App.jsx for root component
 */

import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';
import './index.css';
import './i18n'; // Initialize i18n before app renders
import App from './App.jsx';

// Mount React application to DOM
createRoot(document.getElementById('root')).render(
  <StrictMode>
    <App />
  </StrictMode>,
);
