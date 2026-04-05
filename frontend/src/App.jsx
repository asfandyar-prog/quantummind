import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import LandingPage   from '@/components/LandingPage'
import ModeSelector  from '@/components/ModeSelector'
import MainApp       from '@/components/MainApp'

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/"        element={<LandingPage />} />
        <Route path="/select"  element={<ModeSelector />} />
        <Route path="/app"     element={<MainApp />} />
        <Route path="/teacher" element={<div style={{ display:'flex', alignItems:'center', justifyContent:'center', height:'100vh', fontFamily:'system-ui', fontSize:'18px', color:'#6C6C70' }}>Teacher Dashboard — Coming Soon</div>} />
        <Route path="*"        element={<Navigate to="/" replace />} />
      </Routes>
    </BrowserRouter>
  )
}