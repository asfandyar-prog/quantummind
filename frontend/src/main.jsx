import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import '@/styles/globals.css'
import App from '@/App'

/**
 * main.jsx — the entry point Vite loads first
 *
 * StrictMode: In development, React renders each component twice
 * to catch side effects. This is intentional and won't happen in
 * production. It's a development-only safety net — keep it.
 *
 * createRoot: This is React 18's API (replaces ReactDOM.render).
 * It enables concurrent features like streaming and Suspense,
 * which we'll use when we add the AI streaming response in Day 3.
 */
createRoot(document.getElementById('root')).render(
  <StrictMode>
    <App />
  </StrictMode>
)