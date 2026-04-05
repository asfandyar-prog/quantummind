import { useNavigate } from 'react-router-dom'
import { motion } from 'framer-motion'
import { useState } from 'react'

const FONT = '-apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif'

const FEATURES = [
  {
    icon: '⚛',
    title: 'Theory Mode',
    description: 'Deep-dive into quantum concepts with an AI tutor that adapts to your knowledge level in real time.',
    color: '#007AFF',
    tag: 'Free',
  },
  {
    icon: '⟨ψ|',
    title: 'Practice Mode',
    description: 'Write and execute real Qiskit code in a VS Code-quality editor. See circuit diagrams instantly.',
    color: '#32ADE6',
    tag: 'Free',
  },
  {
    icon: '🎯',
    title: 'Guided Learning',
    description: 'Step-by-step lessons with mandatory check questions. You must understand before you advance.',
    color: '#5856D6',
    tag: 'Free',
  },
  {
    icon: '🎓',
    title: '13-Week Course',
    description: 'Structured quantum computing curriculum with RAG-powered AI tutor grounded in lecture notes.',
    color: '#34C759',
    tag: 'Premium',
  },
  {
    icon: '📝',
    title: 'Exam Mode',
    description: 'AI examiner with adaptive questioning, rubric-based grading, and human-in-the-loop review.',
    color: '#FF9500',
    tag: 'Coming Soon',
  },
]

const STATS = [
  { value: '60+',  label: 'Students taught' },
  { value: '120+', label: 'Qiskit Fall Fest participants' },
  { value: '13',   label: 'Week curriculum' },
  { value: '$0',   label: 'Infrastructure cost' },
]

export default function LandingPage() {
  const navigate     = useNavigate()
  const [hovered, setHovered] = useState(null)

  return (
    <div style={{ minHeight: '100vh', background: '#F2F2F7', fontFamily: FONT, overflowX: 'hidden' }}>

      {/* ── NAV ─────────────────────────────────────────────── */}
      <nav style={{ position: 'fixed', top: 0, left: 0, right: 0, zIndex: 100, background: 'rgba(242,242,247,0.85)', backdropFilter: 'blur(20px)', WebkitBackdropFilter: 'blur(20px)', borderBottom: '1px solid rgba(0,0,0,0.07)', padding: '0 40px', height: '56px', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
          <span style={{ fontSize: '20px', fontWeight: 800, letterSpacing: '-0.5px', background: 'linear-gradient(135deg, #007AFF, #5856D6)', WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent' }}>
            QuantumMind
          </span>
          <span style={{ fontSize: '10px', fontWeight: 600, letterSpacing: '0.08em', textTransform: 'uppercase', color: '#007AFF', background: 'rgba(0,122,255,0.08)', border: '1px solid rgba(0,122,255,0.2)', padding: '2px 8px', borderRadius: '20px' }}>
            Beta
          </span>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
          <button
            onClick={() => navigate('/teacher')}
            style={{ fontSize: '13px', fontWeight: 500, color: '#6C6C70', background: 'transparent', border: 'none', cursor: 'pointer', fontFamily: FONT, padding: '6px 12px', borderRadius: '8px' }}
            onMouseEnter={e => e.target.style.color = '#1C1C1E'}
            onMouseLeave={e => e.target.style.color = '#6C6C70'}
          >
            Tutor Login
          </button>
          <motion.button
            onClick={() => navigate('/splash')}
            style={{ fontSize: '13px', fontWeight: 600, color: '#fff', background: 'linear-gradient(135deg, #007AFF, #5856D6)', border: 'none', cursor: 'pointer', fontFamily: FONT, padding: '8px 20px', borderRadius: '10px', boxShadow: '0 2px 10px rgba(0,122,255,0.3)' }}
            whileHover={{ scale: 1.03 }}
            whileTap={{ scale: 0.97 }}
          >
            Start Learning →
          </motion.button>
        </div>
      </nav>

      {/* ── HERO ────────────────────────────────────────────── */}
      <section style={{ paddingTop: '140px', paddingBottom: '80px', textAlign: 'center', padding: '80px 40px 32px', position: 'relative', overflow: 'hidden' }}>
        {/* Background glows */}
        <div style={{ position: 'absolute', width: '600px', height: '600px', top: '-100px', left: '50%', transform: 'translateX(-50%)', borderRadius: '50%', background: 'radial-gradient(circle, rgba(0,122,255,0.08) 0%, transparent 70%)', pointerEvents: 'none' }} />
        <div style={{ position: 'absolute', width: '400px', height: '400px', top: '100px', right: '10%', borderRadius: '50%', background: 'radial-gradient(circle, rgba(88,86,214,0.06) 0%, transparent 70%)', pointerEvents: 'none' }} />

        <motion.div
          initial={{ opacity: 0, y: 24 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6 }}
        >


          {/* Headline */}
          <h1 style={{ fontSize: '58px', fontWeight: 800, letterSpacing: '-2px', lineHeight: 1.1, color: '#1C1C1E', maxWidth: '800px', margin: '0 auto 20px' }}>
            Where quantum theory{' '}
            <span style={{ background: 'linear-gradient(135deg, #007AFF, #5856D6)', WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent' }}>
              meets practice
            </span>
          </h1>

          {/* Subheadline */}
          <p style={{ fontSize: '17px', color: '#6C6C70', lineHeight: 1.6, maxWidth: '520px', margin: '0 auto 28px' }}>
            A multi-agent AI platform that teaches quantum computing through
            theory, code execution, guided lessons, and adaptive examination.
          </p>

          {/* CTAs */}
          <div style={{ display: 'flex', gap: '14px', justifyContent: 'center', flexWrap: 'wrap' }}>
            <motion.button
              onClick={() => navigate('/splash')}
              style={{ padding: '13px 28px', borderRadius: '12px', border: 'none', background: 'linear-gradient(135deg, #007AFF, #5856D6)', color: '#fff', fontSize: '15px', fontWeight: 700, fontFamily: FONT, cursor: 'pointer', boxShadow: '0 4px 16px rgba(0,122,255,0.35)' }}
              whileHover={{ scale: 1.04, boxShadow: '0 8px 32px rgba(0,122,255,0.5)' }}
              whileTap={{ scale: 0.97 }}
            >
              Start Learning Free →
            </motion.button>
            <motion.button
              onClick={() => document.getElementById('features').scrollIntoView({ behavior: 'smooth' })}
              style={{ padding: '13px 24px', borderRadius: '12px', border: '1px solid rgba(0,0,0,0.1)', background: '#FFFFFF', color: '#1C1C1E', fontSize: '15px', fontWeight: 600, fontFamily: FONT, cursor: 'pointer', boxShadow: '0 2px 8px rgba(0,0,0,0.06)' }}
              whileHover={{ scale: 1.03 }}
              whileTap={{ scale: 0.97 }}
            >
              Explore Features ↓
            </motion.button>
          </div>

          {/* Compact stats inline */}
          <div style={{ display: 'flex', gap: '32px', justifyContent: 'center', marginTop: '40px', flexWrap: 'wrap' }}>
            {[
              { value: '60+', label: 'Students taught' },
              { value: '120+', label: 'Qiskit Fall Fest' },
              { value: '13', label: 'Week curriculum' },
              { value: '$0', label: 'Cost' },
            ].map((stat, i) => (
              <div key={i} style={{ textAlign: 'center' }}>
                <div style={{ fontSize: '24px', fontWeight: 800, letterSpacing: '-0.5px', background: 'linear-gradient(135deg, #007AFF, #5856D6)', WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent' }}>
                  {stat.value}
                </div>
                <div style={{ fontSize: '12px', color: '#AEAEB2', marginTop: '2px', fontWeight: 500 }}>
                  {stat.label}
                </div>
              </div>
            ))}
          </div>
        </motion.div>
      </section>

      {/* ── FEATURES ────────────────────────────────────────── */}
      <section id="features" style={{ padding: '0 40px 100px' }}>
        <div style={{ maxWidth: '1000px', margin: '0 auto' }}>
          <div style={{ textAlign: 'center', marginBottom: '28px' }}>
            <h2 style={{ fontSize: '32px', fontWeight: 800, letterSpacing: '-0.5px', color: '#1C1C1E', marginBottom: '8px' }}>
              Five ways to learn quantum computing
            </h2>
            <p style={{ fontSize: '17px', color: '#6C6C70' }}>
              Each mode is powered by a different LangGraph AI agent
            </p>
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '16px' }}>
            {FEATURES.map((f, i) => (
              <motion.div
                key={f.title}
                style={{
                  background: '#FFFFFF', borderRadius: '20px', padding: '28px',
                  border: `1px solid ${hovered === i ? f.color + '40' : 'rgba(0,0,0,0.07)'}`,
                  boxShadow: hovered === i ? `0 8px 32px ${f.color}18` : '0 1px 4px rgba(0,0,0,0.06)',
                  cursor: 'default', transition: 'all 0.2s',
                  gridColumn: i === 3 ? 'span 1' : 'span 1',
                }}
                initial={{ opacity: 0, y: 16 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.1 + i * 0.08 }}
                onMouseEnter={() => setHovered(i)}
                onMouseLeave={() => setHovered(null)}
              >
                {/* Icon + tag */}
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '16px' }}>
                  <div style={{ width: '48px', height: '48px', borderRadius: '14px', background: `${f.color}12`, display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: '22px' }}>
                    {f.icon}
                  </div>
                  <span style={{
                    fontSize: '11px', fontWeight: 700, letterSpacing: '0.06em', textTransform: 'uppercase',
                    color: f.tag === 'Free' ? '#34C759' : f.tag === 'Premium' ? '#FF9500' : '#AEAEB2',
                    background: f.tag === 'Free' ? 'rgba(52,199,89,0.1)' : f.tag === 'Premium' ? 'rgba(255,149,0,0.1)' : 'rgba(0,0,0,0.05)',
                    padding: '3px 10px', borderRadius: '20px',
                  }}>
                    {f.tag}
                  </span>
                </div>

                <h3 style={{ fontSize: '17px', fontWeight: 700, color: '#1C1C1E', marginBottom: '8px' }}>
                  {f.title}
                </h3>
                <p style={{ fontSize: '14px', color: '#6C6C70', lineHeight: 1.6 }}>
                  {f.description}
                </p>
              </motion.div>
            ))}
          </div>
        </div>
      </section>

      {/* ── TECH STACK ──────────────────────────────────────── */}
      <section style={{ padding: '0 40px 100px' }}>
        <div style={{ maxWidth: '900px', margin: '0 auto', background: '#FFFFFF', borderRadius: '24px', padding: '48px', boxShadow: '0 2px 12px rgba(0,0,0,0.06)', border: '1px solid rgba(0,0,0,0.07)' }}>
          <h2 style={{ fontSize: '28px', fontWeight: 800, color: '#1C1C1E', marginBottom: '8px', letterSpacing: '-0.5px' }}>
            Production-grade AI architecture
          </h2>
          <p style={{ fontSize: '15px', color: '#6C6C70', marginBottom: '32px' }}>
            Built with the same stack used at AI research labs
          </p>

          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '24px' }}>
            {[
              { label: 'AI Framework', value: 'LangGraph multi-agent system', color: '#007AFF' },
              { label: 'LLM Provider', value: 'Groq (llama-3.1-8b-instant)', color: '#5856D6' },
              { label: 'RAG Pipeline', value: 'ChromaDB + HuggingFace embeddings', color: '#34C759' },
              { label: 'Code Execution', value: 'Real Qiskit + IBM Quantum simulator', color: '#FF9500' },
              { label: 'Frontend', value: 'React + Vite + Framer Motion', color: '#32ADE6' },
              { label: 'Backend', value: 'FastAPI + SSE streaming', color: '#FF3B30' },
            ].map((item, i) => (
              <div key={i} style={{ display: 'flex', alignItems: 'flex-start', gap: '12px' }}>
                <div style={{ width: '8px', height: '8px', borderRadius: '50%', background: item.color, flexShrink: 0, marginTop: '6px' }} />
                <div>
                  <p style={{ fontSize: '12px', fontWeight: 600, color: '#AEAEB2', letterSpacing: '0.06em', textTransform: 'uppercase', marginBottom: '2px' }}>{item.label}</p>
                  <p style={{ fontSize: '15px', fontWeight: 500, color: '#1C1C1E' }}>{item.value}</p>
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ── CTA BOTTOM ──────────────────────────────────────── */}
      <section style={{ padding: '0 40px 80px', textAlign: 'center' }}>
        <motion.div
          style={{ maxWidth: '600px', margin: '0 auto', background: 'linear-gradient(135deg, #007AFF, #5856D6)', borderRadius: '24px', padding: '56px 40px', boxShadow: '0 12px 48px rgba(0,122,255,0.3)' }}
          initial={{ opacity: 0, y: 16 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.5 }}
        >
          <h2 style={{ fontSize: '36px', fontWeight: 800, color: '#FFFFFF', marginBottom: '12px', letterSpacing: '-0.5px' }}>
            Ready to learn quantum computing?
          </h2>
          <p style={{ fontSize: '17px', color: 'rgba(255,255,255,0.8)', marginBottom: '32px', lineHeight: 1.6 }}>
            Free forever for Theory, Practice, and Guided modes.
          </p>
          <motion.button
            onClick={() => navigate('/splash')}
            style={{ padding: '16px 40px', borderRadius: '14px', border: 'none', background: '#FFFFFF', color: '#007AFF', fontSize: '17px', fontWeight: 700, fontFamily: FONT, cursor: 'pointer', boxShadow: '0 4px 16px rgba(0,0,0,0.15)' }}
            whileHover={{ scale: 1.04 }}
            whileTap={{ scale: 0.97 }}
          >
            Start Learning Free →
          </motion.button>
        </motion.div>
      </section>

      {/* ── FOOTER ──────────────────────────────────────────── */}
      <footer style={{ padding: '24px 40px', borderTop: '1px solid rgba(0,0,0,0.07)', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
        <span style={{ fontSize: '13px', color: '#AEAEB2' }}>
          Built by <a href="https://github.com/asfandyar-prog" target="_blank" rel="noreferrer" style={{ color: '#007AFF', textDecoration: 'none', fontWeight: 600 }}>Asfand Yar</a> · University of Debrecen
        </span>
        <div style={{ display: 'flex', gap: '16px' }}>
          <a href="https://github.com/asfandyar-prog/quantummind" target="_blank" rel="noreferrer" style={{ fontSize: '13px', color: '#AEAEB2', textDecoration: 'none', fontWeight: 500 }}>GitHub</a>
          <a href="https://linkedin.com/in/asfand-yar-3966b8291" target="_blank" rel="noreferrer" style={{ fontSize: '13px', color: '#AEAEB2', textDecoration: 'none', fontWeight: 500 }}>LinkedIn</a>
        </div>
      </footer>
    </div>
  )
}