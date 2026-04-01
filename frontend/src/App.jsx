import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import SplashScreen  from '@/components/SplashScreen'
import ModeSelector  from '@/components/ModeSelector'
import MainApp       from '@/components/MainApp'

/**
 * App — top-level router
 *
 * Routes:
 *   /        → SplashScreen (auto-advances to /select after 2.8s)
 *   /select  → ModeSelector (user picks Theory / Practice / Guided)
 *   /app     → MainApp (the full learning interface)
 *   *        → redirect to /  (handles any unknown URL)
 *
 * Why BrowserRouter and not HashRouter?
 * BrowserRouter uses real URLs (/app, /select). This is cleaner and
 * required for Vercel deployment. If you were hosting on GitHub Pages
 * without a redirect config, HashRouter (/#/select) would be easier —
 * but we're using Vercel, so BrowserRouter is correct.
 *
 * Why not nested layouts?
 * Each screen is full-height and full-width. There's no shared chrome
 * between Splash/ModeSelector and MainApp that would justify nesting.
 * Flat routes keep it simple.
 */
export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/"       element={<SplashScreen />} />
        <Route path="/select" element={<ModeSelector />} />
        <Route path="/app"    element={<MainApp />} />
        <Route path="*"       element={<Navigate to="/" replace />} />
      </Routes>
    </BrowserRouter>
  )
}