import { useState, useEffect } from 'react'
import { motion, AnimatePresence } from 'framer-motion'

const FONT    = '-apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif'
const MONO    = 'SF Mono, ui-monospace, Menlo, Consolas, monospace'
const BACKEND = 'http://localhost:8000'

// ── helpers ──────────────────────────────────────────────────
function fmt(iso) {
  if (!iso) return '—'
  return new Date(iso).toLocaleString('en-GB', { day:'2-digit', month:'short', hour:'2-digit', minute:'2-digit' })
}
function scoreColor(s) {
  if (s >= 7) return '#34C759'
  if (s >= 5) return '#FF9500'
  return '#FF3B30'
}
function versionColor(v) {
  return v === 'V1' ? '#34C759' : v === 'V2' ? '#FF9500' : '#FF3B30'
}

// ── ScoreSlider ───────────────────────────────────────────────
function ScoreSlider({ label, aiScore, value, onChange, color }) {
  return (
    <div style={{ marginBottom: '16px' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '6px' }}>
        <span style={{ fontSize: '12px', fontWeight: 600, color: '#6C6C70', textTransform: 'uppercase', letterSpacing: '0.06em' }}>{label}</span>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <span style={{ fontSize: '11px', color: '#AEAEB2' }}>AI: {aiScore}</span>
          <span style={{ fontSize: '14px', fontWeight: 700, color, minWidth: '32px', textAlign: 'right' }}>{value}/10</span>
        </div>
      </div>
      <input type="range" min="0" max="10" step="0.5" value={value}
        onChange={e => onChange(parseFloat(e.target.value))}
        style={{ width: '100%', accentColor: color, cursor: 'pointer' }}
      />
      <div style={{ display: 'flex', justifyContent: 'space-between', marginTop: '2px' }}>
        <span style={{ fontSize: '10px', color: '#AEAEB2' }}>0</span>
        <span style={{ fontSize: '10px', color: '#AEAEB2' }}>10</span>
      </div>
    </div>
  )
}

// ── Main component ────────────────────────────────────────────
export default function TeacherDashboard() {
  const [phase, setPhase]           = useState('login')   // login | dashboard | session
  const [password, setPassword]     = useState('')
  const [authError, setAuthError]   = useState('')
  const [sessions, setSessions]     = useState([])
  const [stats, setStats]           = useState(null)
  const [selectedSession, setSelectedSession] = useState(null)
  const [turns, setTurns]           = useState([])
  const [loading, setLoading]       = useState(false)
  const [reviews, setReviews]       = useState({})   // turn_id → review state
  const [submitting, setSubmitting] = useState({})   // turn_id → bool
  const [submitted, setSubmitted]   = useState({})   // turn_id → bool

  const headers = { 'Content-Type': 'application/json', 'x-teacher-password': password }

  async function handleLogin() {
    setLoading(true)
    setAuthError('')
    try {
      const res = await fetch(`${BACKEND}/api/teacher/sessions`, { headers })
      if (res.status === 401) { setAuthError('Incorrect password.'); return }
      const data = await res.json()
      setSessions(data.sessions || [])

      // Fetch research stats
      const statsRes = await fetch(`${BACKEND}/api/research/stats`, { headers })
      const statsData = await statsRes.json()
      setStats(statsData)

      setPhase('dashboard')
    } catch (e) {
      setAuthError('Cannot connect to backend.')
    } finally {
      setLoading(false)
    }
  }

  async function handleSelectSession(session) {
    setSelectedSession(session)
    setLoading(true)
    try {
      const res = await fetch(`${BACKEND}/api/teacher/session/${session.session_id}`, { headers })
      const data = await res.json()
      setTurns(data.turns || [])

      // Init review state for each turn
      const init = {}
      for (const t of data.turns || []) {
        init[t.turn_id] = {
          accuracy:  t.teacher_accuracy  ?? t.score_accuracy,
          reasoning: t.teacher_reasoning ?? t.score_reasoning,
          clarity:   t.teacher_clarity   ?? t.score_clarity,
          feedback:  t.teacher_feedback  || '',
          notes:     '',
        }
      }
      setReviews(init)
      setPhase('session')
    } catch (e) {
      alert('Failed to load session.')
    } finally {
      setLoading(false)
    }
  }

  async function handleSubmitReview(turn) {
    const rev = reviews[turn.turn_id]
    if (!rev) return
    setSubmitting(p => ({ ...p, [turn.turn_id]: true }))

    const changed = (
      rev.accuracy  !== turn.score_accuracy  ||
      rev.reasoning !== turn.score_reasoning ||
      rev.clarity   !== turn.score_clarity
    )

    try {
      await fetch(`${BACKEND}/api/teacher/review`, {
        method: 'POST',
        headers,
        body: JSON.stringify({
          session_id:        selectedSession.session_id,
          turn_id:           turn.turn_id,
          action:            changed ? 'modified' : 'accepted',
          ai_accuracy:       turn.score_accuracy,
          ai_reasoning:      turn.score_reasoning,
          ai_clarity:        turn.score_clarity,
          teacher_accuracy:  changed ? rev.accuracy  : null,
          teacher_reasoning: changed ? rev.reasoning : null,
          teacher_clarity:   changed ? rev.clarity   : null,
          teacher_feedback:  rev.feedback,
          teacher_notes:     rev.notes,
        }),
      })
      setSubmitted(p => ({ ...p, [turn.turn_id]: true }))
    } catch (e) {
      alert('Failed to submit review.')
    } finally {
      setSubmitting(p => ({ ...p, [turn.turn_id]: false }))
    }
  }

  // ── LOGIN ────────────────────────────────────────────────────
  if (phase === 'login') {
    return (
      <div style={{ width: '100vw', height: '100vh', background: '#000000', display: 'flex', alignItems: 'center', justifyContent: 'center', fontFamily: FONT }}>
        <motion.div
          style={{ width: '100%', maxWidth: '400px', padding: '48px', background: 'rgba(255,255,255,0.04)', border: '1px solid rgba(255,255,255,0.08)', borderRadius: '24px', backdropFilter: 'blur(24px)' }}
          initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }}
        >
          <div style={{ textAlign: 'center', marginBottom: '36px' }}>
            <div style={{ fontSize: '40px', marginBottom: '16px' }}>🔐</div>
            <h1 style={{ fontSize: '24px', fontWeight: 700, color: '#F5F5F7', marginBottom: '6px' }}>Teacher Dashboard</h1>
            <p style={{ fontSize: '14px', color: '#6C6C70' }}>QuantumMind AI Examiner</p>
          </div>

          <div style={{ marginBottom: '16px' }}>
            <input
              type="password"
              value={password}
              onChange={e => setPassword(e.target.value)}
              onKeyDown={e => { if (e.key === 'Enter') handleLogin() }}
              placeholder="Enter teacher password"
              style={{ width: '100%', padding: '14px 16px', borderRadius: '12px', border: `1px solid ${authError ? '#FF3B30' : 'rgba(255,255,255,0.1)'}`, background: 'rgba(255,255,255,0.06)', color: '#F5F5F7', fontSize: '15px', fontFamily: FONT, outline: 'none', boxSizing: 'border-box' }}
              onFocus={e => e.target.style.border = '1px solid rgba(0,122,255,0.5)'}
              onBlur={e  => e.target.style.border = `1px solid ${authError ? '#FF3B30' : 'rgba(255,255,255,0.1)'}`}
            />
            {authError && <p style={{ fontSize: '13px', color: '#FF3B30', marginTop: '6px' }}>{authError}</p>}
          </div>

          <motion.button
            onClick={handleLogin}
            disabled={!password.trim() || loading}
            style={{ width: '100%', padding: '14px', borderRadius: '12px', border: 'none', background: password.trim() ? '#007AFF' : 'rgba(255,255,255,0.08)', color: password.trim() ? '#fff' : '#6C6C70', fontSize: '15px', fontWeight: 600, fontFamily: FONT, cursor: password.trim() ? 'pointer' : 'default' }}
            whileHover={password.trim() ? { scale: 1.02 } : {}}
            whileTap={password.trim() ? { scale: 0.98 } : {}}
          >
            {loading ? 'Verifying…' : 'Access Dashboard →'}
          </motion.button>
        </motion.div>
      </div>
    )
  }

  // ── SESSION DETAIL ───────────────────────────────────────────
  if (phase === 'session' && selectedSession) {
    const avgAI = turns.length ? Math.round(turns.reduce((s, t) => s + t.score_total, 0) / turns.length * 10) / 10 : 0
    return (
      <div style={{ width: '100vw', height: '100vh', background: '#F2F2F7', fontFamily: FONT, display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>

        {/* Header */}
        <div style={{ padding: '16px 28px', background: '#FFFFFF', borderBottom: '1px solid rgba(0,0,0,0.07)', display: 'flex', alignItems: 'center', gap: '16px', flexShrink: 0 }}>
          <button onClick={() => setPhase('dashboard')}
            style={{ fontSize: '13px', color: '#007AFF', background: 'transparent', border: 'none', cursor: 'pointer', fontFamily: FONT, display: 'flex', alignItems: 'center', gap: '4px' }}>
            ← Back
          </button>
          <div style={{ width: '1px', height: '20px', background: 'rgba(0,0,0,0.1)' }} />
          <div>
            <h2 style={{ fontSize: '16px', fontWeight: 700, color: '#1C1C1E' }}>{selectedSession.student_name}</h2>
            <p style={{ fontSize: '12px', color: '#6C6C70' }}>{selectedSession.topic} · {selectedSession.version} · {fmt(selectedSession.started_at)}</p>
          </div>
          <div style={{ marginLeft: 'auto', display: 'flex', alignItems: 'center', gap: '12px' }}>
            <div style={{ textAlign: 'center' }}>
              <div style={{ fontSize: '22px', fontWeight: 800, color: scoreColor(avgAI) }}>{avgAI}</div>
              <div style={{ fontSize: '10px', color: '#AEAEB2', textTransform: 'uppercase', letterSpacing: '0.06em' }}>Avg Score</div>
            </div>
            <div style={{ textAlign: 'center' }}>
              <div style={{ fontSize: '22px', fontWeight: 800, color: '#1C1C1E' }}>{turns.length}</div>
              <div style={{ fontSize: '10px', color: '#AEAEB2', textTransform: 'uppercase', letterSpacing: '0.06em' }}>Questions</div>
            </div>
          </div>
        </div>

        {/* Turns */}
        <div style={{ flex: 1, overflowY: 'auto', padding: '24px 28px', display: 'flex', flexDirection: 'column', gap: '20px' }}>
          {turns.map((turn, i) => {
            const rev  = reviews[turn.turn_id] || {}
            const done = submitted[turn.turn_id]
            return (
              <motion.div key={turn.turn_id}
                style={{ background: '#FFFFFF', borderRadius: '16px', border: '1px solid rgba(0,0,0,0.07)', overflow: 'hidden', boxShadow: '0 1px 4px rgba(0,0,0,0.05)' }}
                initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: i * 0.05 }}
              >
                {/* Turn header */}
                <div style={{ padding: '16px 20px', borderBottom: '1px solid rgba(0,0,0,0.06)', background: '#F9F9FB', display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', gap: '12px' }}>
                  <div style={{ flex: 1 }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '6px' }}>
                      <span style={{ fontSize: '11px', fontWeight: 600, color: turn.is_followup ? '#FF9500' : '#007AFF', background: turn.is_followup ? 'rgba(255,149,0,0.1)' : 'rgba(0,122,255,0.1)', padding: '2px 8px', borderRadius: '20px' }}>
                        {turn.is_followup ? 'Follow-up' : `Q${i + 1}`}
                      </span>
                      <span style={{ fontSize: '12px', fontWeight: 700, color: scoreColor(turn.score_total) }}>
                        AI: {turn.score_total}/10
                      </span>
                      {done && <span style={{ fontSize: '11px', color: '#34C759', background: 'rgba(52,199,89,0.1)', padding: '2px 8px', borderRadius: '20px', fontWeight: 600 }}>✓ Reviewed</span>}
                    </div>
                    <p style={{ fontSize: '15px', fontWeight: 600, color: '#1C1C1E', lineHeight: 1.4 }}>{turn.question}</p>
                  </div>
                </div>

                <div style={{ padding: '20px', display: 'grid', gridTemplateColumns: '1fr 320px', gap: '24px' }}>
                  {/* Left: transcript */}
                  <div>
                    <p style={{ fontSize: '12px', fontWeight: 600, color: '#AEAEB2', textTransform: 'uppercase', letterSpacing: '0.06em', marginBottom: '8px' }}>Student Answer</p>
                    <p style={{ fontSize: '14px', color: '#1C1C1E', lineHeight: 1.7, marginBottom: '16px', padding: '14px', background: '#F9F9FB', borderRadius: '10px' }}>
                      {turn.student_answer}
                    </p>

                    {/* AI scores */}
                    <div style={{ display: 'flex', gap: '10px', marginBottom: '16px' }}>
                      {[['accuracy', '#007AFF'], ['reasoning', '#5856D6'], ['clarity', '#34C759']].map(([dim, color]) => (
                        <div key={dim} style={{ flex: 1, padding: '10px', borderRadius: '10px', background: `${color}08`, border: `1px solid ${color}18`, textAlign: 'center' }}>
                          <div style={{ fontSize: '18px', fontWeight: 700, color }}>{turn[`score_${dim}`]}</div>
                          <div style={{ fontSize: '10px', color: '#AEAEB2', textTransform: 'uppercase', letterSpacing: '0.06em' }}>{dim}</div>
                        </div>
                      ))}
                    </div>

                    <p style={{ fontSize: '12px', fontWeight: 600, color: '#AEAEB2', textTransform: 'uppercase', letterSpacing: '0.06em', marginBottom: '6px' }}>AI Justification</p>
                    <p style={{ fontSize: '13px', color: '#3C3C43', lineHeight: 1.6, marginBottom: '12px' }}>{turn.ai_justification}</p>

                    {turn.ideal_answer && (
                      <div style={{ padding: '12px 16px', borderRadius: '10px', background: 'rgba(52,199,89,0.06)', border: '1px solid rgba(52,199,89,0.15)' }}>
                        <p style={{ fontSize: '11px', fontWeight: 600, color: '#34C759', marginBottom: '4px', textTransform: 'uppercase', letterSpacing: '0.06em' }}>Ideal Answer</p>
                        <p style={{ fontSize: '13px', color: '#3C3C43', lineHeight: 1.6 }}>{turn.ideal_answer}</p>
                      </div>
                    )}
                  </div>

                  {/* Right: review panel */}
                  <div style={{ borderLeft: '1px solid rgba(0,0,0,0.07)', paddingLeft: '24px' }}>
                    <p style={{ fontSize: '12px', fontWeight: 600, color: '#AEAEB2', textTransform: 'uppercase', letterSpacing: '0.06em', marginBottom: '16px' }}>Your Review</p>

                    <ScoreSlider label="Accuracy" aiScore={turn.score_accuracy} value={rev.accuracy ?? turn.score_accuracy} onChange={v => setReviews(p => ({ ...p, [turn.turn_id]: { ...p[turn.turn_id], accuracy: v } }))} color="#007AFF" />
                    <ScoreSlider label="Reasoning" aiScore={turn.score_reasoning} value={rev.reasoning ?? turn.score_reasoning} onChange={v => setReviews(p => ({ ...p, [turn.turn_id]: { ...p[turn.turn_id], reasoning: v } }))} color="#5856D6" />
                    <ScoreSlider label="Clarity" aiScore={turn.score_clarity} value={rev.clarity ?? turn.score_clarity} onChange={v => setReviews(p => ({ ...p, [turn.turn_id]: { ...p[turn.turn_id], clarity: v } }))} color="#34C759" />

                    <div style={{ marginBottom: '12px' }}>
                      <p style={{ fontSize: '12px', fontWeight: 600, color: '#6C6C70', textTransform: 'uppercase', letterSpacing: '0.06em', marginBottom: '6px' }}>Feedback to student</p>
                      <textarea
                        value={rev.feedback || ''}
                        onChange={e => setReviews(p => ({ ...p, [turn.turn_id]: { ...p[turn.turn_id], feedback: e.target.value } }))}
                        placeholder="Add feedback for the student…"
                        rows={3}
                        style={{ width: '100%', padding: '10px 12px', borderRadius: '8px', border: '1px solid rgba(0,0,0,0.1)', fontSize: '13px', fontFamily: FONT, color: '#1C1C1E', resize: 'none', outline: 'none', background: '#F9F9FB', lineHeight: 1.5, boxSizing: 'border-box' }}
                        onFocus={e => e.target.style.border = '1px solid rgba(0,122,255,0.4)'}
                        onBlur={e  => e.target.style.border = '1px solid rgba(0,0,0,0.1)'}
                      />
                    </div>

                    <div style={{ marginBottom: '16px' }}>
                      <p style={{ fontSize: '12px', fontWeight: 600, color: '#6C6C70', textTransform: 'uppercase', letterSpacing: '0.06em', marginBottom: '6px' }}>Private notes</p>
                      <textarea
                        value={rev.notes || ''}
                        onChange={e => setReviews(p => ({ ...p, [turn.turn_id]: { ...p[turn.turn_id], notes: e.target.value } }))}
                        placeholder="Private notes (not shown to student)…"
                        rows={2}
                        style={{ width: '100%', padding: '10px 12px', borderRadius: '8px', border: '1px solid rgba(0,0,0,0.1)', fontSize: '13px', fontFamily: FONT, color: '#1C1C1E', resize: 'none', outline: 'none', background: '#F9F9FB', lineHeight: 1.5, boxSizing: 'border-box' }}
                        onFocus={e => e.target.style.border = '1px solid rgba(88,86,214,0.4)'}
                        onBlur={e  => e.target.style.border = '1px solid rgba(0,0,0,0.1)'}
                      />
                    </div>

                    <motion.button
                      onClick={() => handleSubmitReview(turn)}
                      disabled={submitting[turn.turn_id] || done}
                      style={{
                        width: '100%', padding: '11px', borderRadius: '10px', border: 'none',
                        background: done ? 'rgba(52,199,89,0.1)' : 'linear-gradient(135deg, #007AFF, #5856D6)',
                        color: done ? '#34C759' : '#fff',
                        fontSize: '13px', fontWeight: 600, fontFamily: FONT,
                        cursor: done ? 'default' : 'pointer',
                        boxShadow: done ? 'none' : '0 2px 8px rgba(0,122,255,0.3)',
                      }}
                      whileHover={!done ? { scale: 1.02 } : {}}
                      whileTap={!done ? { scale: 0.98 } : {}}
                    >
                      {done ? '✓ Review Submitted' : submitting[turn.turn_id] ? 'Submitting…' : 'Submit Review'}
                    </motion.button>
                  </div>
                </div>
              </motion.div>
            )
          })}
        </div>
      </div>
    )
  }

  // ── DASHBOARD ────────────────────────────────────────────────
  return (
    <div style={{ width: '100vw', height: '100vh', background: '#F2F2F7', fontFamily: FONT, display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>

      {/* Header */}
      <div style={{ padding: '16px 28px', background: '#FFFFFF', borderBottom: '1px solid rgba(0,0,0,0.07)', display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexShrink: 0 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
          <span style={{ fontSize: '20px', fontWeight: 700, background: 'linear-gradient(135deg, #007AFF, #5856D6)', WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent' }}>QuantumMind</span>
          <span style={{ fontSize: '12px', fontWeight: 600, color: '#FF9500', background: 'rgba(255,149,0,0.1)', padding: '3px 10px', borderRadius: '20px' }}>Teacher</span>
        </div>
        <button onClick={() => { setPhase('login'); setPassword('') }}
          style={{ fontSize: '13px', color: '#6C6C70', background: 'transparent', border: '1px solid rgba(0,0,0,0.1)', padding: '6px 14px', borderRadius: '8px', cursor: 'pointer', fontFamily: FONT }}>
          Sign out
        </button>
      </div>

      <div style={{ flex: 1, overflowY: 'auto', padding: '24px 28px' }}>

        {/* Stats */}
        {stats && (
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: '16px', marginBottom: '24px' }}>
            {[
              { label: 'Total Sessions',    value: sessions.length,                                      color: '#007AFF' },
              { label: 'Avg Score',         value: sessions.length ? (sessions.reduce((s,x) => s + (x.avg_score||0), 0) / sessions.length).toFixed(1) : '—', color: '#34C759' },
              { label: 'Reviews Submitted', value: stats.grading_agreement?.total_reviews ?? 0,          color: '#5856D6' },
              { label: 'AI Accepted',       value: stats.grading_agreement?.accepted ?? 0,               color: '#FF9500' },
            ].map((s, i) => (
              <div key={i} style={{ background: '#FFFFFF', borderRadius: '14px', padding: '20px', border: '1px solid rgba(0,0,0,0.07)', boxShadow: '0 1px 4px rgba(0,0,0,0.05)' }}>
                <div style={{ fontSize: '28px', fontWeight: 800, color: s.color, letterSpacing: '-0.5px' }}>{s.value}</div>
                <div style={{ fontSize: '12px', color: '#6C6C70', marginTop: '4px', fontWeight: 500 }}>{s.label}</div>
              </div>
            ))}
          </div>
        )}

        {/* Sessions table */}
        <div style={{ background: '#FFFFFF', borderRadius: '16px', border: '1px solid rgba(0,0,0,0.07)', overflow: 'hidden', boxShadow: '0 1px 4px rgba(0,0,0,0.05)' }}>
          <div style={{ padding: '16px 20px', borderBottom: '1px solid rgba(0,0,0,0.07)', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
            <h2 style={{ fontSize: '15px', fontWeight: 700, color: '#1C1C1E' }}>Exam Sessions</h2>
            <span style={{ fontSize: '12px', color: '#AEAEB2' }}>{sessions.length} total</span>
          </div>

          {sessions.length === 0 ? (
            <div style={{ padding: '48px', textAlign: 'center', color: '#AEAEB2' }}>
              <div style={{ fontSize: '32px', marginBottom: '12px' }}>📝</div>
              <p style={{ fontSize: '14px' }}>No exam sessions yet.</p>
            </div>
          ) : (
            <table style={{ width: '100%', borderCollapse: 'collapse' }}>
              <thead>
                <tr style={{ borderBottom: '1px solid rgba(0,0,0,0.06)' }}>
                  {['Student', 'Topic', 'Mode', 'Score', 'Questions', 'Date', ''].map(h => (
                    <th key={h} style={{ padding: '10px 16px', fontSize: '11px', fontWeight: 600, color: '#AEAEB2', textTransform: 'uppercase', letterSpacing: '0.08em', textAlign: 'left' }}>{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {sessions.map((s, i) => (
                  <motion.tr key={s.session_id}
                    style={{ borderBottom: '1px solid rgba(0,0,0,0.04)', cursor: 'pointer' }}
                    onClick={() => handleSelectSession(s)}
                    whileHover={{ background: 'rgba(0,122,255,0.03)' }}
                    initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: i * 0.04 }}
                  >
                    <td style={{ padding: '12px 16px', fontSize: '14px', fontWeight: 600, color: '#1C1C1E' }}>{s.student_name}</td>
                    <td style={{ padding: '12px 16px', fontSize: '13px', color: '#3C3C43' }}>{s.topic}</td>
                    <td style={{ padding: '12px 16px' }}>
                      <span style={{ fontSize: '11px', fontWeight: 700, color: versionColor(s.version), background: `${versionColor(s.version)}12`, padding: '3px 8px', borderRadius: '20px' }}>{s.version}</span>
                    </td>
                    <td style={{ padding: '12px 16px' }}>
                      <span style={{ fontSize: '14px', fontWeight: 700, color: scoreColor(s.avg_score) }}>{s.avg_score?.toFixed(1) ?? '—'}</span>
                    </td>
                    <td style={{ padding: '12px 16px', fontSize: '13px', color: '#6C6C70' }}>{s.total_turns}</td>
                    <td style={{ padding: '12px 16px', fontSize: '12px', color: '#AEAEB2' }}>{fmt(s.started_at)}</td>
                    <td style={{ padding: '12px 16px' }}>
                      <span style={{ fontSize: '12px', color: '#007AFF', fontWeight: 500 }}>Review →</span>
                    </td>
                  </motion.tr>
                ))}
              </tbody>
            </table>
          )}
        </div>

        {/* Research stats */}
        {stats && stats.sessions_by_version?.length > 0 && (
          <div style={{ marginTop: '20px', background: '#FFFFFF', borderRadius: '16px', border: '1px solid rgba(0,0,0,0.07)', padding: '20px', boxShadow: '0 1px 4px rgba(0,0,0,0.05)' }}>
            <h2 style={{ fontSize: '15px', fontWeight: 700, color: '#1C1C1E', marginBottom: '16px' }}>Research Metrics</h2>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '12px' }}>
              {stats.sessions_by_version.map(v => (
                <div key={v.version} style={{ padding: '14px', borderRadius: '10px', background: `${versionColor(v.version)}08`, border: `1px solid ${versionColor(v.version)}20` }}>
                  <div style={{ fontSize: '11px', fontWeight: 700, color: versionColor(v.version), textTransform: 'uppercase', letterSpacing: '0.08em', marginBottom: '8px' }}>{v.version} Mode</div>
                  <div style={{ fontSize: '22px', fontWeight: 800, color: '#1C1C1E' }}>{v.count}</div>
                  <div style={{ fontSize: '12px', color: '#6C6C70' }}>sessions · avg {v.avg_score?.toFixed(1) ?? '—'}</div>
                </div>
              ))}
            </div>
            {stats.grading_agreement?.total_reviews > 0 && (
              <div style={{ marginTop: '16px', padding: '14px', borderRadius: '10px', background: 'rgba(0,122,255,0.04)', border: '1px solid rgba(0,122,255,0.1)' }}>
                <p style={{ fontSize: '12px', fontWeight: 600, color: '#007AFF', marginBottom: '6px' }}>AI vs Human Agreement</p>
                <p style={{ fontSize: '13px', color: '#3C3C43', lineHeight: 1.6 }}>
                  Mean delta — Accuracy: <strong>{stats.grading_agreement.mean_delta_accuracy?.toFixed(2)}</strong> · 
                  Reasoning: <strong>{stats.grading_agreement.mean_delta_reasoning?.toFixed(2)}</strong> · 
                  Clarity: <strong>{stats.grading_agreement.mean_delta_clarity?.toFixed(2)}</strong>
                </p>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  )
}
