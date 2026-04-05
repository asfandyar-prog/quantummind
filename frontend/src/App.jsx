import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import LandingPage        from '@/components/LandingPage'
import ModeSelector        from '@/components/ModeSelector'
import MainApp             from '@/components/MainApp'
import TeacherDashboard    from '@/components/TeacherDashboard'

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/"        element={<LandingPage />} />
        <Route path="/select"  element={<ModeSelector />} />
        <Route path="/app"     element={<MainApp />} />
        <Route path="/teacher" element={<TeacherDashboard />} />
        <Route path="*"        element={<Navigate to="/" replace />} />
      </Routes>
    </BrowserRouter>
  )
}
