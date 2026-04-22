// Created by Metrum AI for AMD

import { createRoot } from "react-dom/client";
import { Provider } from "react-redux";
import { C } from "./tokens";
import App from "./App";
import { store } from "./store/store";

const style = document.createElement("style");
style.textContent = `
  *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }

  html, body, #root { height: 100%; overflow: hidden; }

  body {
    font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
    font-weight: 400;
    background: ${C.bg};
    color: ${C.white};
    line-height: 1.5;
    -webkit-font-smoothing: antialiased;
    -moz-osx-font-smoothing: grayscale;
    text-rendering: optimizeLegibility;
  }

  #root { display: flex; flex-direction: column; height: 100%; }

  ::-webkit-scrollbar { width: 3px; }
  ::-webkit-scrollbar-track { background: transparent; }
  ::-webkit-scrollbar-thumb { background: ${C.border}; border-radius: 2px; }
  ::-webkit-scrollbar-thumb:hover { background: ${C.borderLight}; }

  ::selection { background: rgba(237, 28, 36, 0.2); color: ${C.white}; }

  input, textarea, select, button {
    font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
  }

  textarea, input[type="text"], select {
    transition: border-color 0.2s ease, box-shadow 0.2s ease, background 0.2s ease;
  }

  input::placeholder, textarea::placeholder {
    color: ${C.dim};
    font-weight: 400;
  }

  input:focus, textarea:focus, select:focus {
    outline: none;
    border-color: ${C.teal} !important;
    box-shadow: 0 0 0 3px rgba(0, 124, 151, 0.1) !important;
    background: ${C.elevated} !important;
    color: ${C.white} !important;
  }

  select option {
    background: ${C.surface};
    color: ${C.white};
    padding: 8px;
  }

  button {
    transition: all 0.15s ease;
  }
  button:hover:not(:disabled) { transform: translateY(-1px); }
  button:active:not(:disabled) { transform: translateY(0); }

  @keyframes fadeIn {
    from { opacity: 0; }
    to { opacity: 1; }
  }
  @keyframes fadeInUp {
    from { opacity: 0; transform: translateY(8px); }
    to { opacity: 1; transform: translateY(0); }
  }
  @keyframes slideInRight {
    from { opacity: 0; transform: translateX(20px); }
    to { opacity: 1; transform: translateX(0); }
  }
  @keyframes pulse {
    0%, 100% { opacity: 1; }
    50% { opacity: 0.4; }
  }
  @keyframes pulseSoft {
    0%, 100% { opacity: 1; }
    50% { opacity: 0.6; }
  }
  @keyframes shimmer {
    0% { background-position: -200% 0; }
    100% { background-position: 200% 0; }
  }
  @keyframes spin {
    from { transform: rotate(0deg); }
    to { transform: rotate(360deg); }
  }
  @keyframes livePulse {
    0% { box-shadow: 0 0 0 0 rgba(0,124,151,0.5); opacity: 1; }
    50% { box-shadow: 0 0 0 5px rgba(0,124,151,0); opacity: 0.6; }
    100% { box-shadow: 0 0 0 0 rgba(0,124,151,0.5); opacity: 1; }
  }
  @keyframes float {
    0%, 100% { transform: translateY(0); }
    50% { transform: translateY(-4px); }
  }

  .cpm-img-card:hover .cpm-img-hover { opacity: 1 !important; }
`;
document.head.appendChild(style);

createRoot(document.getElementById("root")).render(
  <Provider store={store}>
    <App />
  </Provider>
);
