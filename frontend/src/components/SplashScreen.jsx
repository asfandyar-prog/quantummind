import { useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { motion } from 'framer-motion'

export default function SplashScreen() {
  const navigate = useNavigate()

  useEffect(() => {
    const timer = setTimeout(() => navigate('/select'), 3200)
    return () => clearTimeout(timer)
  }, [navigate])

  return (
    <div
      className="relative w-full h-full flex items-center justify-center overflow-hidden"
      style={{
        fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif',
        background: 'linear-gradient(145deg, #E8F0FE 0%, #F2F2F7 40%, #EAF4FF 70%, #F0EEFF 100%)',
      }}
    >
      {/* Ambient glow top-left */}
      <div style={{ position:'absolute', width:700, height:700, top:-200, left:-200, borderRadius:'50%', background:'radial-gradient(circle, rgba(0,122,255,0.10) 0%, transparent 65%)', pointerEvents:'none' }} />
      {/* Ambient glow bottom-right */}
      <div style={{ position:'absolute', width:600, height:600, bottom:-150, right:-150, borderRadius:'50%', background:'radial-gradient(circle, rgba(88,86,214,0.08) 0%, transparent 65%)', pointerEvents:'none' }} />
      {/* Centre glow */}
      <div style={{ position:'absolute', width:500, height:500, borderRadius:'50%', background:'radial-gradient(circle, rgba(50,173,230,0.10) 0%, transparent 60%)', pointerEvents:'none' }} />

      {/* Main card */}
      <motion.div
        style={{
          position:'relative', zIndex:10,
          display:'flex', flexDirection:'column', alignItems:'center', textAlign:'center',
          padding:'64px 80px 56px',
          borderRadius:'32px',
          background:'rgba(255,255,255,0.75)',
          backdropFilter:'blur(32px)',
          WebkitBackdropFilter:'blur(32px)',
          boxShadow:'0 24px 80px rgba(0,0,0,0.10), 0 2px 8px rgba(0,0,0,0.06), inset 0 1px 0 rgba(255,255,255,0.9)',
          border:'1px solid rgba(255,255,255,0.85)',
          minWidth:'480px',
        }}
        initial={{ opacity:0, scale:0.92, y:24 }}
        animate={{ opacity:1, scale:1, y:0 }}
        transition={{ duration:0.65, ease:[0.16,1,0.3,1] }}
      >

        {/* Atom — SVG rings so they always render */}
        <motion.div
          style={{ marginBottom:'36px', position:'relative', width:96, height:96 }}
          animate={{ rotate:360 }}
          transition={{ duration:12, repeat:Infinity, ease:'linear' }}
        >
          <svg width="96" height="96" viewBox="0 0 96 96" style={{ overflow:'visible' }}>
            <ellipse cx="48" cy="48" rx="44" ry="16"
              fill="none" stroke="rgba(0,122,255,0.50)" strokeWidth="1.5" />
            <ellipse cx="48" cy="48" rx="44" ry="16"
              fill="none" stroke="rgba(50,173,230,0.50)" strokeWidth="1.5"
              transform="rotate(60 48 48)" />
            <ellipse cx="48" cy="48" rx="44" ry="16"
              fill="none" stroke="rgba(88,86,214,0.45)" strokeWidth="1.5"
              transform="rotate(120 48 48)" />
            <circle cx="48" cy="48" r="8" fill="url(#ng)" />
            <defs>
              <radialGradient id="ng" cx="35%" cy="35%">
                <stop offset="0%" stopColor="#5AC8FA" />
                <stop offset="100%" stopColor="#007AFF" />
              </radialGradient>
            </defs>
          </svg>
        </motion.div>

        {/* Logo */}
        <motion.h1
          style={{
            fontSize:'52px', fontWeight:700, letterSpacing:'-2px', lineHeight:1, marginBottom:'14px',
            background:'linear-gradient(135deg, #007AFF 0%, #32ADE6 50%, #5856D6 100%)',
            WebkitBackgroundClip:'text', WebkitTextFillColor:'transparent', backgroundClip:'text',
          }}
          initial={{ opacity:0, y:12 }}
          animate={{ opacity:1, y:0 }}
          transition={{ delay:0.25, duration:0.55 }}
        >
          QuantumMind
        </motion.h1>

        {/* Tagline */}
        <motion.p
          style={{ fontSize:'16px', color:'#6C6C70', fontWeight:400, lineHeight:1.5, marginBottom:'48px' }}
          initial={{ opacity:0 }}
          animate={{ opacity:1 }}
          transition={{ delay:0.45 }}
        >
          Where quantum theory meets practice
        </motion.p>

        {/* Progress bar */}
        <motion.div
          style={{ width:'200px', height:'4px', borderRadius:'2px', background:'rgba(0,122,255,0.10)', overflow:'hidden' }}
          initial={{ opacity:0 }}
          animate={{ opacity:1 }}
          transition={{ delay:0.7 }}
        >
          <motion.div
            style={{ height:'100%', borderRadius:'2px', background:'linear-gradient(90deg, #007AFF, #32ADE6, #5856D6)' }}
            initial={{ width:'0%' }}
            animate={{ width:'100%' }}
            transition={{ delay:0.85, duration:2.0, ease:'easeInOut' }}
          />
        </motion.div>

        {/* Label */}
        <motion.p
          style={{ marginTop:'14px', fontSize:'11px', color:'#AEAEB2', letterSpacing:'0.12em', textTransform:'uppercase', fontWeight:500 }}
          initial={{ opacity:0 }}
          animate={{ opacity:1 }}
          transition={{ delay:1.0 }}
        >
          Initializing
        </motion.p>

      </motion.div>
    </div>
  )
}