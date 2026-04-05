import { useNavigate } from 'react-router-dom'
import { motion } from 'framer-motion'
import { useState, useEffect } from 'react'

const FONT = '-apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif'

const STATS = [
  { value: '60+',  label: 'Students taught' },
  { value: '120+', label: 'Qiskit Fall Fest' },
  { value: '13',   label: 'Week curriculum'  },
  { value: '$0',   label: 'Infrastructure'   },
]

export default function LandingPage() {
  const navigate = useNavigate()
  const [dark, setDark] = useState(true)

  useEffect(() => {
    const saved = localStorage.getItem('qm_theme')
    if (saved) setDark(saved === 'dark')
  }, [])

  function toggleTheme() {
    const next = !dark
    setDark(next)
    localStorage.setItem('qm_theme', next ? 'dark' : 'light')
  }

  const t = dark ? {
    bg:         '#000000',
    nav:        'rgba(0,0,0,0.8)',
    navBorder:  'rgba(255,255,255,0.08)',
    text:       '#F5F5F7',
    textSub:    '#A1A1A6',
    textMuted:  '#6C6C70',
    divider:    'rgba(255,255,255,0.08)',
    glow:       'rgba(0,122,255,0.18)',
    navBtn:     '#F5F5F7',
    navBtnTxt:  '#000000',
    themeIcon:  '☀',
    footerLink: '#6C6C70',
  } : {
    bg:         '#F5F5F7',
    nav:        'rgba(245,245,247,0.85)',
    navBorder:  'rgba(0,0,0,0.08)',
    text:       '#1C1C1E',
    textSub:    '#3C3C43',
    textMuted:  '#6C6C70',
    divider:    'rgba(0,0,0,0.08)',
    glow:       'rgba(0,122,255,0.07)',
    navBtn:     '#1C1C1E',
    navBtnTxt:  '#FFFFFF',
    themeIcon:  '◑',
    footerLink: '#AEAEB2',
  }

  return (
    <motion.div
      style={{ width: '100vw', height: '100vh', background: t.bg, fontFamily: FONT, color: t.text, overflow: 'hidden', display: 'flex', flexDirection: 'column' }}
      animate={{ background: t.bg }}
      transition={{ duration: 0.35 }}
    >
      {/* ── NAV ─────────────────────────────────────────────── */}
      <motion.nav
        style={{
          position: 'fixed', top: 0, left: 0, right: 0, zIndex: 100,
          background: t.nav,
          backdropFilter: 'blur(24px)', WebkitBackdropFilter: 'blur(24px)',
          borderBottom: `1px solid ${t.navBorder}`,
          padding: '0 48px', height: '52px',
          display: 'flex', alignItems: 'center', justifyContent: 'space-between',
        }}
        initial={{ y: -52 }}
        animate={{ y: 0 }}
        transition={{ duration: 0.5 }}
      >
        <span style={{
          fontSize: '18px', fontWeight: 700,
          background: 'linear-gradient(135deg, #007AFF, #5856D6)',
          WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent',
        }}>
          QuantumMind
        </span>

        <div style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
          <button
            onClick={toggleTheme}
            style={{ fontSize: '15px', color: t.textMuted, background: 'transparent', border: 'none', cursor: 'pointer', padding: '6px 10px', borderRadius: '8px', fontFamily: FONT, lineHeight: 1 }}
          >
            {t.themeIcon}
          </button>
          <button
            onClick={() => navigate('/teacher')}
            style={{ fontSize: '13px', fontWeight: 500, color: t.textMuted, background: 'transparent', border: 'none', cursor: 'pointer', fontFamily: FONT, padding: '6px 16px', borderRadius: '8px' }}
          >
            Tutor Login
          </button>
          <motion.button
            onClick={() => navigate('/splash')}
            style={{ fontSize: '13px', fontWeight: 600, color: t.navBtnTxt, background: t.navBtn, border: 'none', cursor: 'pointer', fontFamily: FONT, padding: '8px 20px', borderRadius: '20px' }}
            whileHover={{ scale: 1.05 }}
            whileTap={{ scale: 0.96 }}
          >
            Start Learning
          </motion.button>
        </div>
      </motion.nav>

      {/* ── HERO — full screen, nothing else ────────────────── */}
      <section style={{
        flex: 1,
        display: 'flex', flexDirection: 'column',
        alignItems: 'center', justifyContent: 'center',
        textAlign: 'center',
        padding: '0 40px',
        position: 'relative', overflow: 'hidden',
      }}>
        {/* Glow */}
        <div style={{
          position: 'absolute', width: '900px', height: '700px',
          top: '50%', left: '50%',
          transform: 'translate(-50%, -55%)',
          background: `radial-gradient(ellipse, ${t.glow} 0%, transparent 65%)`,
          pointerEvents: 'none',
        }} />

        {/* Eyebrow */}
        <motion.p
          style={{ fontSize: '12px', fontWeight: 600, letterSpacing: '0.14em', textTransform: 'uppercase', color: '#007AFF', marginBottom: '24px' }}
          initial={{ opacity: 0, y: 8 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5 }}
        >
          AI-Powered Quantum Computing Education
        </motion.p>

        {/* Headline */}
        <motion.h1
          style={{
            fontSize: 'clamp(48px, 7vw, 88px)',
            fontWeight: 800,
            letterSpacing: '-3px',
            lineHeight: 1.02,
            marginBottom: '28px',
            maxWidth: '820px',
          }}
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.7, delay: 0.1 }}
        >
          Where quantum theory
          <br />
          <span style={{
            background: 'linear-gradient(135deg, #007AFF 0%, #5856D6 50%, #32ADE6 100%)',
            WebkitBackgroundClip: 'text',
            WebkitTextFillColor: 'transparent',
          }}>
            meets practice.
          </span>
        </motion.h1>

        {/* One line. That's it. */}
        <motion.p
          style={{
            fontSize: '20px',
            color: t.textSub,
            lineHeight: 1.55,
            maxWidth: '480px',
            marginBottom: '52px',
            fontWeight: 400,
          }}
          initial={{ opacity: 0, y: 12 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6, delay: 0.2 }}
        >
          Five AI agents. One quantum platform.
        </motion.p>

        {/* Single CTA */}
        <motion.div
          initial={{ opacity: 0, y: 12 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5, delay: 0.3 }}
        >
          <motion.button
            onClick={() => navigate('/splash')}
            style={{
              padding: '18px 52px',
              borderRadius: '14px',
              border: 'none',
              background: '#007AFF',
              color: '#FFFFFF',
              fontSize: '17px',
              fontWeight: 700,
              fontFamily: FONT,
              cursor: 'pointer',
              boxShadow: '0 0 48px rgba(0,122,255,0.45)',
              letterSpacing: '-0.2px',
            }}
            whileHover={{ scale: 1.05, boxShadow: '0 0 64px rgba(0,122,255,0.55)' }}
            whileTap={{ scale: 0.97 }}
          >
            Start Learning Free →
          </motion.button>
        </motion.div>

        {/* Stats — minimal, below CTA */}
        <motion.div
          style={{
            display: 'flex', gap: '48px', justifyContent: 'center',
            marginTop: '64px', flexWrap: 'wrap',
          }}
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ duration: 0.6, delay: 0.5 }}
        >
          {STATS.map((stat, i) => (
            <div key={i} style={{ textAlign: 'center' }}>
              <div style={{
                fontSize: '26px', fontWeight: 800,
                letterSpacing: '-0.5px', color: t.text, lineHeight: 1,
              }}>
                {stat.value}
              </div>
              <div style={{ fontSize: '11px', color: t.textMuted, marginTop: '5px', fontWeight: 500, letterSpacing: '0.04em' }}>
                {stat.label}
              </div>
            </div>
          ))}
        </motion.div>
      </section>

      {/* ── FOOTER ──────────────────────────────────────────── */}
      <footer style={{
        padding: '16px 48px',
        borderTop: `1px solid ${t.navBorder}`,
        display: 'flex', alignItems: 'center', justifyContent: 'space-between',
        flexShrink: 0,
      }}>
        <span style={{ fontSize: '12px', color: t.textMuted }}>
          Built by{' '}
          <a href="https://github.com/asfandyar-prog" target="_blank" rel="noreferrer"
            style={{ color: t.textSub, textDecoration: 'none', fontWeight: 600 }}>
            Asfand Yar
          </a>
          {' '}· University of Debrecen · 2025
        </span>
        <div style={{ display: 'flex', gap: '20px' }}>
          <a href="https://github.com/asfandyar-prog/quantummind" target="_blank" rel="noreferrer"
            style={{ fontSize: '12px', color: t.footerLink, textDecoration: 'none', fontWeight: 500 }}>
            GitHub
          </a>
          <a href="https://linkedin.com/in/asfand-yar-3966b8291" target="_blank" rel="noreferrer"
            style={{ fontSize: '12px', color: t.footerLink, textDecoration: 'none', fontWeight: 500 }}>
            LinkedIn
          </a>
        </div>
      </footer>
    </motion.div>
  )
}