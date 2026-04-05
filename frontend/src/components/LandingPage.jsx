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

const FEATURES = [
  { icon: '⚛', title: 'Theory', description: 'AI tutor that adapts to your level. Ask anything about quantum computing and get a clear, structured answer.', color: '#007AFF', tag: 'Free' },
  { icon: '⌨', title: 'Practice', description: 'VS Code-quality editor. Write real Qiskit code, execute it, and see your circuit diagram instantly.', color: '#32ADE6', tag: 'Free' },
  { icon: '🎯', title: 'Guided', description: 'Step-by-step lessons with mandatory check questions. You must understand before you advance.', color: '#5856D6', tag: 'Free' },
  { icon: '🎓', title: '13-Week Course', description: 'The full quantum computing curriculum I designed for 60+ students at University of Debrecen.', color: '#34C759', tag: 'Premium' },
  { icon: '📝', title: 'Exam Mode', description: 'Adaptive AI examiner with rubric-based grading and human-in-the-loop teacher review.', color: '#FF9500', tag: 'Soon' },
]

export default function LandingPage() {
  const navigate = useNavigate()
  const [hovered, setHovered] = useState(null)
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
    bg: '#000000', nav: 'rgba(0,0,0,0.72)', navBorder: 'rgba(255,255,255,0.08)',
    text: '#F5F5F7', textSecond: '#A1A1A6', textMuted: '#6C6C70',
    cardBg: 'rgba(255,255,255,0.03)', cardBgH: 'rgba(255,255,255,0.06)',
    cardBorder: 'rgba(255,255,255,0.07)', cardBorderH: 'rgba(255,255,255,0.15)',
    sectionBg: 'rgba(255,255,255,0.03)', sectionBorder: 'rgba(255,255,255,0.07)',
    divider: 'rgba(255,255,255,0.07)', btnBg: 'rgba(255,255,255,0.05)',
    btnBorder: 'rgba(255,255,255,0.12)', btnHov: 'rgba(255,255,255,0.10)',
    ctaBg: '#F5F5F7', ctaColor: '#000000',
    glow: 'rgba(0,122,255,0.15)', navBtn: '#F5F5F7', navBtnColor: '#000000',
    themeIcon: '☀', tagSoon: 'rgba(255,255,255,0.06)',
  } : {
    bg: '#F5F5F7', nav: 'rgba(245,245,247,0.85)', navBorder: 'rgba(0,0,0,0.08)',
    text: '#1C1C1E', textSecond: '#3C3C43', textMuted: '#6C6C70',
    cardBg: '#FFFFFF', cardBgH: '#FFFFFF',
    cardBorder: 'rgba(0,0,0,0.07)', cardBorderH: 'rgba(0,0,0,0.14)',
    sectionBg: '#FFFFFF', sectionBorder: 'rgba(0,0,0,0.07)',
    divider: 'rgba(0,0,0,0.08)', btnBg: '#FFFFFF',
    btnBorder: 'rgba(0,0,0,0.12)', btnHov: '#F0F0F5',
    ctaBg: '#1C1C1E', ctaColor: '#FFFFFF',
    glow: 'rgba(0,122,255,0.08)', navBtn: '#1C1C1E', navBtnColor: '#FFFFFF',
    themeIcon: '◑', tagSoon: 'rgba(0,0,0,0.06)',
  }

  return (
    <motion.div
      style={{ minHeight: '100vh', background: t.bg, fontFamily: FONT, color: t.text, overflowX: 'hidden' }}
      animate={{ background: t.bg }}
      transition={{ duration: 0.35 }}
    >
      {/* NAV */}
      <motion.nav
        style={{
          position: 'fixed', top: 0, left: 0, right: 0, zIndex: 100,
          background: t.nav, backdropFilter: 'blur(24px)', WebkitBackdropFilter: 'blur(24px)',
          borderBottom: `1px solid ${t.navBorder}`,
          padding: '0 48px', height: '52px',
          display: 'flex', alignItems: 'center', justifyContent: 'space-between',
        }}
        initial={{ y: -52 }} animate={{ y: 0 }} transition={{ duration: 0.5 }}
      >
        <span style={{ fontSize: '18px', fontWeight: 700, background: 'linear-gradient(135deg, #007AFF, #5856D6)', WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent' }}>
          QuantumMind
        </span>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <button onClick={toggleTheme} style={{ fontSize: '14px', color: t.textMuted, background: 'transparent', border: 'none', cursor: 'pointer', padding: '6px 10px', borderRadius: '8px', fontFamily: FONT }}>
            {t.themeIcon}
          </button>
          <button onClick={() => navigate('/teacher')} style={{ fontSize: '13px', fontWeight: 500, color: t.textMuted, background: 'transparent', border: 'none', cursor: 'pointer', fontFamily: FONT, padding: '6px 14px', borderRadius: '8px' }}>
            Tutor Login
          </button>
          <motion.button onClick={() => navigate('/splash')} style={{ fontSize: '13px', fontWeight: 600, color: t.navBtnColor, background: t.navBtn, border: 'none', cursor: 'pointer', fontFamily: FONT, padding: '7px 18px', borderRadius: '20px' }} whileHover={{ scale: 1.04 }} whileTap={{ scale: 0.96 }}>
            Start Learning
          </motion.button>
        </div>
      </motion.nav>

      {/* HERO */}
      <section style={{ minHeight: '100vh', display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', padding: '52px 40px 0', position: 'relative', overflow: 'hidden', textAlign: 'center' }}>
        <div style={{ position: 'absolute', width: '800px', height: '600px', top: '50%', left: '50%', transform: 'translate(-50%, -60%)', background: `radial-gradient(ellipse, ${t.glow} 0%, transparent 70%)`, pointerEvents: 'none' }} />

        <motion.p style={{ fontSize: '13px', fontWeight: 600, letterSpacing: '0.12em', textTransform: 'uppercase', color: '#007AFF', marginBottom: '20px' }} initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.5 }}>
          AI-Powered Quantum Computing Education
        </motion.p>

        <motion.h1 style={{ fontSize: 'clamp(44px, 6vw, 76px)', fontWeight: 800, letterSpacing: '-2.5px', lineHeight: 1.05, marginBottom: '24px', maxWidth: '900px' }} initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.6, delay: 0.1 }}>
          Where quantum theory
          <br />
          <span style={{ background: 'linear-gradient(135deg, #007AFF 0%, #5856D6 50%, #32ADE6 100%)', WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent' }}>
            meets practice.
          </span>
        </motion.h1>

        <motion.p style={{ fontSize: '18px', color: t.textSecond, lineHeight: 1.6, maxWidth: '520px', marginBottom: '40px' }} initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.5, delay: 0.2 }}>
          A multi-agent AI platform that teaches quantum computing through real code execution, guided lessons, and adaptive examination.
        </motion.p>

        {/* Stats */}
        <motion.div style={{ display: 'flex', gap: '48px', justifyContent: 'center', marginBottom: '48px', flexWrap: 'wrap' }} initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ duration: 0.5, delay: 0.3 }}>
          {STATS.map((stat, i) => (
            <div key={i} style={{ textAlign: 'center' }}>
              <div style={{ fontSize: '28px', fontWeight: 800, letterSpacing: '-0.5px', color: t.text, lineHeight: 1 }}>{stat.value}</div>
              <div style={{ fontSize: '12px', color: t.textMuted, marginTop: '4px', fontWeight: 500 }}>{stat.label}</div>
            </div>
          ))}
        </motion.div>

        {/* Divider */}
        <motion.div style={{ width: '1px', height: '40px', background: `linear-gradient(to bottom, ${t.divider}, transparent)`, marginBottom: '32px' }} initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: 0.4 }} />

        {/* CTAs */}
        <motion.div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '20px' }} initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.45, duration: 0.5 }}>
          <p style={{ fontSize: '13px', fontWeight: 600, letterSpacing: '0.1em', textTransform: 'uppercase', color: t.textMuted }}>
            Five ways to learn quantum computing
          </p>
          <div style={{ display: 'flex', gap: '12px' }}>
            <motion.button onClick={() => navigate('/splash')} style={{ padding: '14px 32px', borderRadius: '12px', border: 'none', background: '#007AFF', color: '#FFFFFF', fontSize: '15px', fontWeight: 600, fontFamily: FONT, cursor: 'pointer', boxShadow: '0 0 32px rgba(0,122,255,0.4)' }} whileHover={{ scale: 1.04 }} whileTap={{ scale: 0.97 }}>
              Start Learning Free →
            </motion.button>
            <motion.button onClick={() => document.getElementById('features').scrollIntoView({ behavior: 'smooth' })} style={{ padding: '14px 28px', borderRadius: '12px', border: `1px solid ${t.btnBorder}`, background: t.btnBg, color: t.text, fontSize: '15px', fontWeight: 600, fontFamily: FONT, cursor: 'pointer' }} whileHover={{ background: t.btnHov }} whileTap={{ scale: 0.97 }}>
              Explore Features ↓
            </motion.button>
          </div>
        </motion.div>

        {/* Scroll indicator */}
        <motion.div style={{ position: 'absolute', bottom: '32px', left: '50%', transform: 'translateX(-50%)' }} animate={{ y: [0, 8, 0] }} transition={{ duration: 1.8, repeat: Infinity, ease: 'easeInOut' }}>
          <div style={{ width: '1px', height: '48px', background: `linear-gradient(to bottom, ${t.divider}, transparent)`, margin: '0 auto' }} />
        </motion.div>
      </section>

      {/* FEATURES */}
      <section id="features" style={{ padding: '120px 48px 100px' }}>
        <div style={{ maxWidth: '1100px', margin: '0 auto' }}>
          <motion.div style={{ textAlign: 'center', marginBottom: '64px' }} initial={{ opacity: 0, y: 16 }} whileInView={{ opacity: 1, y: 0 }} viewport={{ once: true }} transition={{ duration: 0.5 }}>
            <h2 style={{ fontSize: '48px', fontWeight: 800, letterSpacing: '-1.5px', color: t.text, marginBottom: '16px' }}>
              One platform.<br />Every way to learn.
            </h2>
            <p style={{ fontSize: '17px', color: t.textMuted, maxWidth: '480px', margin: '0 auto' }}>
              Each mode is powered by a dedicated LangGraph AI agent.
            </p>
          </motion.div>

          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '16px' }}>
            {FEATURES.map((f, i) => (
              <motion.div key={f.title}
                style={{ background: hovered === i ? t.cardBgH : t.cardBg, border: `1px solid ${hovered === i ? t.cardBorderH : t.cardBorder}`, borderRadius: '20px', padding: '32px', cursor: 'default', transition: 'all 0.2s', boxShadow: hovered === i ? `0 8px 32px ${f.color}12` : 'none' }}
                initial={{ opacity: 0, y: 20 }} whileInView={{ opacity: 1, y: 0 }} viewport={{ once: true }} transition={{ delay: i * 0.08, duration: 0.5 }}
                onMouseEnter={() => setHovered(i)} onMouseLeave={() => setHovered(null)}
              >
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '20px' }}>
                  <div style={{ width: '44px', height: '44px', borderRadius: '12px', background: `${f.color}18`, border: `1px solid ${f.color}28`, display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: '20px' }}>{f.icon}</div>
                  <span style={{ fontSize: '11px', fontWeight: 700, letterSpacing: '0.08em', textTransform: 'uppercase', color: f.tag === 'Free' ? '#34C759' : f.tag === 'Premium' ? '#FF9500' : t.textMuted, background: f.tag === 'Free' ? 'rgba(52,199,89,0.12)' : f.tag === 'Premium' ? 'rgba(255,149,0,0.12)' : t.tagSoon, padding: '3px 10px', borderRadius: '20px' }}>{f.tag}</span>
                </div>
                <h3 style={{ fontSize: '20px', fontWeight: 700, color: t.text, marginBottom: '10px', letterSpacing: '-0.3px' }}>{f.title}</h3>
                <p style={{ fontSize: '14px', color: t.textMuted, lineHeight: 1.65 }}>{f.description}</p>
                {hovered === i && (
                  <motion.div style={{ height: '2px', background: f.color, borderRadius: '1px', marginTop: '20px' }} initial={{ width: '0%' }} animate={{ width: '100%' }} transition={{ duration: 0.3 }} />
                )}
              </motion.div>
            ))}
          </div>
        </div>
      </section>

      {/* TECH STACK */}
      <section style={{ padding: '0 48px 120px' }}>
        <div style={{ maxWidth: '1100px', margin: '0 auto', background: t.sectionBg, border: `1px solid ${t.sectionBorder}`, borderRadius: '24px', padding: '56px' }}>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '56px', alignItems: 'center' }}>
            <div>
              <h2 style={{ fontSize: '36px', fontWeight: 800, letterSpacing: '-1px', color: t.text, marginBottom: '16px' }}>Built like a research lab.<br />Deployed at zero cost.</h2>
              <p style={{ fontSize: '16px', color: t.textMuted, lineHeight: 1.7 }}>Every component mirrors production AI systems at Google DeepMind, IBM Research, and ETH Zurich's Agentic Systems Lab.</p>
            </div>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
              {[
                { label: 'AI Framework', value: 'LangGraph multi-agent system', color: '#007AFF' },
                { label: 'LLM',          value: 'Groq — 500+ tokens/sec',       color: '#5856D6' },
                { label: 'RAG',          value: 'ChromaDB + HuggingFace',        color: '#34C759' },
                { label: 'Execution',    value: 'Real Qiskit + IBM Quantum',     color: '#FF9500' },
                { label: 'Streaming',    value: 'FastAPI SSE — real-time',       color: '#32ADE6' },
              ].map((item, i) => (
                <motion.div key={i} style={{ display: 'flex', alignItems: 'center', gap: '14px' }} initial={{ opacity: 0, x: 16 }} whileInView={{ opacity: 1, x: 0 }} viewport={{ once: true }} transition={{ delay: i * 0.07 }}>
                  <div style={{ width: '6px', height: '6px', borderRadius: '50%', background: item.color, flexShrink: 0 }} />
                  <span style={{ fontSize: '11px', color: t.textMuted, fontWeight: 600, minWidth: '100px', letterSpacing: '0.06em', textTransform: 'uppercase' }}>{item.label}</span>
                  <span style={{ fontSize: '14px', color: t.textSecond, fontWeight: 500 }}>{item.value}</span>
                </motion.div>
              ))}
            </div>
          </div>
        </div>
      </section>

      {/* BOTTOM CTA */}
      <section style={{ padding: '0 48px 120px', textAlign: 'center' }}>
        <motion.div style={{ maxWidth: '640px', margin: '0 auto' }} initial={{ opacity: 0, y: 20 }} whileInView={{ opacity: 1, y: 0 }} viewport={{ once: true }} transition={{ duration: 0.6 }}>
          <h2 style={{ fontSize: '48px', fontWeight: 800, letterSpacing: '-1.5px', color: t.text, marginBottom: '16px', lineHeight: 1.1 }}>Start learning<br />quantum computing today.</h2>
          <p style={{ fontSize: '17px', color: t.textMuted, marginBottom: '36px', lineHeight: 1.6 }}>Theory, Practice, and Guided modes are free forever.</p>
          <motion.button onClick={() => navigate('/splash')} style={{ padding: '16px 44px', borderRadius: '14px', border: 'none', background: t.ctaBg, color: t.ctaColor, fontSize: '17px', fontWeight: 700, fontFamily: FONT, cursor: 'pointer' }} whileHover={{ scale: 1.04 }} whileTap={{ scale: 0.97 }}>
            Start Learning Free →
          </motion.button>
        </motion.div>
      </section>

      {/* FOOTER */}
      <footer style={{ padding: '24px 48px', borderTop: `1px solid ${t.divider}`, display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
        <span style={{ fontSize: '13px', color: t.textMuted }}>
          Built by <a href="https://github.com/asfandyar-prog" target="_blank" rel="noreferrer" style={{ color: t.textSecond, textDecoration: 'none', fontWeight: 600 }}>Asfand Yar</a> · University of Debrecen · 2025
        </span>
        <div style={{ display: 'flex', gap: '20px' }}>
          <a href="https://github.com/asfandyar-prog/quantummind" target="_blank" rel="noreferrer" style={{ fontSize: '13px', color: t.textMuted, textDecoration: 'none', fontWeight: 500 }}>GitHub</a>
          <a href="https://linkedin.com/in/asfand-yar-3966b8291" target="_blank" rel="noreferrer" style={{ fontSize: '13px', color: t.textMuted, textDecoration: 'none', fontWeight: 500 }}>LinkedIn</a>
        </div>
      </footer>
    </motion.div>
  )
}