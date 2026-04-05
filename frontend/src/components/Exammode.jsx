import { useState, useRef, useEffect } from 'react'
import { motion, AnimatePresence } from 'framer-motion'

const FONT    = '-apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif'
const MONO    = 'SF Mono, ui-monospace, Menlo, Consolas, monospace'
const BACKEND = 'http://localhost:8000'

const TOPICS = [
  'Quantum Superposition', 'Quantum Entanglement', 'Quantum Gates',
  'Bell States', "Grover's Algorithm", 'Deutsch-Jozsa Algorithm',
  'Quantum Teleportation', 'Quantum Circuits', 'Bloch Sphere',
]

const VERSION_INFO = {
  V1: { label: 'Static',   color: '#34C759', desc: '5 fixed questions, no adaptation' },
  V2: { label: 'Adaptive', color: '#FF9500', desc: 'Fixed questions + follow-ups on weak answers' },
  V3: { label: 'Dynamic',  color: '#FF3B30', desc: 'Fully adaptive — questions based on your answers' },
}

function ScoreBar({ label, value, color }) {
  return (
    <div style={{ marginBottom: '10px' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '4px' }}>
        <span style={{ fontSize: '12px', fontWeight: 600, color: '#6C6C70', textTransform: 'uppercase', letterSpacing: '0.06em' }}>{label}</span>
        <span style={{ fontSize: '13px', fontWeight: 700, color }}>{value}/10</span>
      </div>
      <div style={{ height: '6px', background: 'rgba(0,0,0,0.07)', borderRadius: '3px', overflow: 'hidden' }}>
        <motion.div
          style={{ height: '100%', background: color, borderRadius: '3px' }}
          initial={{ width: 0 }}
          animate={{ width: `${value * 10}%` }}
          transition={{ duration: 0.6, ease: 'easeOut' }}
        />
      </div>
    </div>
  )
}

export default function ExamMode() {
  const [phase, setPhase]           = useState('setup')    // setup | exam | result
  const [studentName, setStudentName] = useState('')
  const [topic, setTopic]           = useState('')
  const [customTopic, setCustomTopic] = useState('')
  const [version, setVersion]       = useState('V2')
  const [sessionId, setSessionId]   = useState(null)
  const [question, setQuestion]     = useState('')
  const [turnNumber, setTurnNumber] = useState(1)
  const [answer, setAnswer]         = useState('')
  const [isLoading, setIsLoading]   = useState(false)
  const [lastResult, setLastResult] = useState(null)
  const [transcript, setTranscript] = useState([])
  const [examComplete, setExamComplete] = useState(false)
  const [isFollowup, setIsFollowup] = useState(false)
  const [listening, setListening]   = useState(false)

  const answerRef  = useRef(null)
  const bottomRef  = useRef(null)
  const recognitionRef = useRef(null)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [transcript, lastResult])

  // Voice input
  function startListening() {
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition
    if (!SpeechRecognition) { alert('Voice input not supported in this browser. Use Chrome.'); return }
    const rec = new SpeechRecognition()
    rec.continuous = false
    rec.lang = 'en-US'
    rec.interimResults = false
    rec.onresult = (e) => {
      const text = e.results[0][0].transcript
      setAnswer(prev => prev ? prev + ' ' + text : text)
      setListening(false)
    }
    rec.onerror = () => setListening(false)
    rec.onend   = () => setListening(false)
    recognitionRef.current = rec
    rec.start()
    setListening(true)
  }

  function stopListening() {
    recognitionRef.current?.stop()
    setListening(false)
  }

  async function handleStart() {
    const selectedTopic = topic || customTopic.trim()
    if (!studentName.trim() || !selectedTopic) return
    setIsLoading(true)
    try {
      const res = await fetch(`${BACKEND}/api/exam/start`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ student_name: studentName.trim(), topic: selectedTopic, version }),
      })
      const data = await res.json()
      setSessionId(data.session_id)
      setQuestion(data.question)
      setTurnNumber(data.turn_number)
      setPhase('exam')
    } catch (e) {
      alert('Failed to start exam. Is the backend running?')
    } finally {
      setIsLoading(false)
    }
  }

  async function handleSubmitAnswer() {
    if (!answer.trim() || isLoading) return
    setIsLoading(true)
    const submitted = answer.trim()
    setAnswer('')

    try {
      const res = await fetch(`${BACKEND}/api/exam/answer`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ session_id: sessionId, student_answer: submitted }),
      })
      const data = await res.json()

      // Add to transcript
      setTranscript(prev => [...prev, {
        question, answer: submitted, scores: data.scores,
        justification: data.justification, ideal_answer: data.ideal_answer,
        feedback: data.feedback, is_followup: data.is_followup,
        turn_id: data.turn_id,
      }])

      setLastResult(data)
      setIsFollowup(data.is_followup)

      if (data.exam_complete) {
        setExamComplete(true)
        setPhase('result')
      } else {
        setQuestion(data.next_question)
        setTurnNumber(data.turn_number)
      }
    } catch (e) {
      alert('Error submitting answer.')
    } finally {
      setIsLoading(false)
    }
  }

  function getFinalScore() {
    if (!transcript.length) return 0
    return Math.round(transcript.reduce((s, t) => s + t.scores.total, 0) / transcript.length * 10) / 10
  }

  function getGrade(score) {
    if (score >= 9) return { label: 'Outstanding', color: '#34C759' }
    if (score >= 7) return { label: 'Good',        color: '#007AFF' }
    if (score >= 5) return { label: 'Satisfactory',color: '#FF9500' }
    return                { label: 'Needs Work',   color: '#FF3B30' }
  }

  // ── SETUP PHASE ─────────────────────────────────────────────
  if (phase === 'setup') {
    return (
      <div style={{ flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center', background: '#FFFFFF', fontFamily: FONT, padding: '40px', overflowY: 'auto' }}>
        <motion.div style={{ width: '100%', maxWidth: '600px' }} initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }}>

          <div style={{ textAlign: 'center', marginBottom: '40px' }}>
            <div style={{ fontSize: '48px', marginBottom: '16px' }}>📝</div>
            <h1 style={{ fontSize: '28px', fontWeight: 700, color: '#1C1C1E', marginBottom: '8px' }}>AI Examiner</h1>
            <p style={{ fontSize: '15px', color: '#6C6C70', lineHeight: 1.6 }}>
              An adaptive examination system powered by LangGraph.<br />
              Your answers are graded on accuracy, reasoning, and clarity.
            </p>
          </div>

          {/* Student name */}
          <div style={{ marginBottom: '20px' }}>
            <label style={{ fontSize: '12px', fontWeight: 600, color: '#6C6C70', letterSpacing: '0.08em', textTransform: 'uppercase', display: 'block', marginBottom: '8px' }}>Your Name</label>
            <input
              value={studentName}
              onChange={e => setStudentName(e.target.value)}
              placeholder="Enter your name or student ID"
              style={{ width: '100%', padding: '12px 16px', borderRadius: '12px', border: '1px solid rgba(0,0,0,0.1)', fontSize: '15px', fontFamily: FONT, color: '#1C1C1E', outline: 'none', background: '#F9F9FB', boxSizing: 'border-box' }}
              onFocus={e => e.target.style.border = '1px solid rgba(0,122,255,0.4)'}
              onBlur={e  => e.target.style.border = '1px solid rgba(0,0,0,0.1)'}
            />
          </div>

          {/* Topic */}
          <div style={{ marginBottom: '20px' }}>
            <label style={{ fontSize: '12px', fontWeight: 600, color: '#6C6C70', letterSpacing: '0.08em', textTransform: 'uppercase', display: 'block', marginBottom: '8px' }}>Topic</label>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '8px', marginBottom: '10px' }}>
              {TOPICS.map(t => (
                <button key={t} onClick={() => setTopic(t)}
                  style={{ padding: '10px 12px', borderRadius: '10px', border: `1px solid ${topic === t ? '#007AFF' : 'rgba(0,0,0,0.08)'}`, background: topic === t ? 'rgba(0,122,255,0.08)' : '#FFFFFF', color: topic === t ? '#007AFF' : '#3C3C43', fontSize: '12px', fontFamily: FONT, cursor: 'pointer', fontWeight: topic === t ? 600 : 400, transition: 'all 0.15s' }}>
                  {t}
                </button>
              ))}
            </div>
            <input
              value={customTopic}
              onChange={e => { setCustomTopic(e.target.value); setTopic('') }}
              placeholder="Or type a custom topic…"
              style={{ width: '100%', padding: '12px 16px', borderRadius: '12px', border: '1px solid rgba(0,0,0,0.1)', fontSize: '14px', fontFamily: FONT, color: '#1C1C1E', outline: 'none', background: '#F9F9FB', boxSizing: 'border-box' }}
              onFocus={e => e.target.style.border = '1px solid rgba(0,122,255,0.4)'}
              onBlur={e  => e.target.style.border = '1px solid rgba(0,0,0,0.1)'}
            />
          </div>

          {/* Version */}
          <div style={{ marginBottom: '32px' }}>
            <label style={{ fontSize: '12px', fontWeight: 600, color: '#6C6C70', letterSpacing: '0.08em', textTransform: 'uppercase', display: 'block', marginBottom: '8px' }}>Exam Mode</label>
            <div style={{ display: 'flex', gap: '10px' }}>
              {Object.entries(VERSION_INFO).map(([v, info]) => (
                <button key={v} onClick={() => setVersion(v)}
                  style={{ flex: 1, padding: '14px 12px', borderRadius: '12px', border: `1px solid ${version === v ? info.color : 'rgba(0,0,0,0.08)'}`, background: version === v ? `${info.color}10` : '#FFFFFF', cursor: 'pointer', fontFamily: FONT, transition: 'all 0.15s', textAlign: 'left' }}>
                  <div style={{ fontSize: '13px', fontWeight: 700, color: version === v ? info.color : '#1C1C1E', marginBottom: '4px' }}>{v} — {info.label}</div>
                  <div style={{ fontSize: '11px', color: '#6C6C70', lineHeight: 1.4 }}>{info.desc}</div>
                </button>
              ))}
            </div>
          </div>

          <motion.button
            onClick={handleStart}
            disabled={isLoading || (!studentName.trim() || (!topic && !customTopic.trim()))}
            style={{ width: '100%', padding: '16px', borderRadius: '14px', border: 'none', background: (studentName.trim() && (topic || customTopic.trim())) ? 'linear-gradient(135deg, #FF9500, #FF3B30)' : 'rgba(0,0,0,0.08)', color: (studentName.trim() && (topic || customTopic.trim())) ? '#fff' : '#AEAEB2', fontSize: '16px', fontWeight: 700, fontFamily: FONT, cursor: (studentName.trim() && (topic || customTopic.trim())) ? 'pointer' : 'default', boxShadow: (studentName.trim() && (topic || customTopic.trim())) ? '0 4px 16px rgba(255,149,0,0.35)' : 'none' }}
            whileHover={(studentName.trim() && (topic || customTopic.trim())) ? { scale: 1.02 } : {}}
            whileTap={(studentName.trim() && (topic || customTopic.trim())) ? { scale: 0.98 } : {}}
          >
            {isLoading ? 'Preparing exam…' : 'Begin Exam →'}
          </motion.button>
        </motion.div>
      </div>
    )
  }

  // ── RESULT PHASE ─────────────────────────────────────────────
  if (phase === 'result') {
    const finalScore = getFinalScore()
    const grade      = getGrade(finalScore)
    return (
      <div style={{ flex: 1, display: 'flex', overflow: 'hidden', background: '#F9F9FB', fontFamily: FONT }}>
        {/* Left: Summary */}
        <div style={{ width: '320px', minWidth: '320px', background: '#FFFFFF', borderRight: '1px solid rgba(0,0,0,0.07)', padding: '32px 24px', display: 'flex', flexDirection: 'column', gap: '20px' }}>
          <div style={{ textAlign: 'center' }}>
            <div style={{ fontSize: '56px', marginBottom: '12px' }}>🎓</div>
            <h2 style={{ fontSize: '20px', fontWeight: 700, color: '#1C1C1E', marginBottom: '4px' }}>Exam Complete</h2>
            <p style={{ fontSize: '13px', color: '#6C6C70' }}>{studentName}</p>
          </div>

          <div style={{ padding: '20px', borderRadius: '14px', background: `${grade.color}10`, border: `1px solid ${grade.color}25`, textAlign: 'center' }}>
            <div style={{ fontSize: '48px', fontWeight: 800, color: grade.color, letterSpacing: '-2px' }}>{finalScore}</div>
            <div style={{ fontSize: '12px', color: grade.color, fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.08em', marginTop: '4px' }}>{grade.label}</div>
          </div>

          <div>
            <p style={{ fontSize: '11px', fontWeight: 600, color: '#AEAEB2', textTransform: 'uppercase', letterSpacing: '0.08em', marginBottom: '12px' }}>Score Breakdown</p>
            {['accuracy', 'reasoning', 'clarity'].map(dim => {
              const avg = transcript.length ? Math.round(transcript.reduce((s, t) => s + t.scores[dim], 0) / transcript.length * 10) / 10 : 0
              const colors = { accuracy: '#007AFF', reasoning: '#5856D6', clarity: '#34C759' }
              return <ScoreBar key={dim} label={dim} value={avg} color={colors[dim]} />
            })}
          </div>

          <div style={{ fontSize: '13px', color: '#6C6C70', lineHeight: 1.6 }}>
            <strong style={{ color: '#1C1C1E' }}>{transcript.length}</strong> questions answered<br />
            <strong style={{ color: '#1C1C1E' }}>{version}</strong> exam mode
          </div>

          <button
            onClick={() => { setPhase('setup'); setTranscript([]); setLastResult(null); setSessionId(null); setAnswer('') }}
            style={{ padding: '12px', borderRadius: '10px', border: '1px solid rgba(0,0,0,0.1)', background: 'transparent', color: '#6C6C70', fontSize: '14px', cursor: 'pointer', fontFamily: FONT }}
          >
            Start New Exam
          </button>
        </div>

        {/* Right: Full transcript */}
        <div style={{ flex: 1, overflowY: 'auto', padding: '28px 32px' }}>
          <h3 style={{ fontSize: '16px', fontWeight: 700, color: '#1C1C1E', marginBottom: '20px' }}>Full Transcript</h3>
          {transcript.map((turn, i) => (
            <motion.div key={i} style={{ marginBottom: '24px', background: '#FFFFFF', borderRadius: '16px', border: '1px solid rgba(0,0,0,0.07)', overflow: 'hidden', boxShadow: '0 1px 4px rgba(0,0,0,0.05)' }}
              initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: i * 0.06 }}>
              <div style={{ padding: '16px 20px', borderBottom: '1px solid rgba(0,0,0,0.06)', background: '#F9F9FB' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '6px' }}>
                  <span style={{ fontSize: '11px', fontWeight: 600, color: turn.is_followup ? '#FF9500' : '#007AFF', background: turn.is_followup ? 'rgba(255,149,0,0.1)' : 'rgba(0,122,255,0.1)', padding: '2px 8px', borderRadius: '20px' }}>
                    {turn.is_followup ? 'Follow-up' : `Q${i + 1}`}
                  </span>
                  <span style={{ fontSize: '12px', fontWeight: 700, color: turn.scores.total >= 7 ? '#34C759' : turn.scores.total >= 5 ? '#FF9500' : '#FF3B30' }}>
                    {turn.scores.total}/10
                  </span>
                </div>
                <p style={{ fontSize: '14px', fontWeight: 600, color: '#1C1C1E' }}>{turn.question}</p>
              </div>
              <div style={{ padding: '16px 20px' }}>
                <p style={{ fontSize: '13px', color: '#3C3C43', lineHeight: 1.6, marginBottom: '12px' }}>{turn.answer}</p>
                <div style={{ display: 'flex', gap: '12px', marginBottom: '12px' }}>
                  {[['accuracy', '#007AFF'], ['reasoning', '#5856D6'], ['clarity', '#34C759']].map(([dim, color]) => (
                    <div key={dim} style={{ flex: 1, padding: '8px 12px', borderRadius: '8px', background: `${color}08`, border: `1px solid ${color}20`, textAlign: 'center' }}>
                      <div style={{ fontSize: '16px', fontWeight: 700, color }}>{turn.scores[dim]}</div>
                      <div style={{ fontSize: '10px', color: '#AEAEB2', textTransform: 'uppercase', letterSpacing: '0.06em' }}>{dim}</div>
                    </div>
                  ))}
                </div>
                <p style={{ fontSize: '12px', color: '#6C6C70', lineHeight: 1.6, marginBottom: '8px' }}><strong>Feedback:</strong> {turn.justification}</p>
                {turn.ideal_answer && (
                  <div style={{ padding: '10px 14px', borderRadius: '8px', background: 'rgba(52,199,89,0.06)', border: '1px solid rgba(52,199,89,0.15)' }}>
                    <p style={{ fontSize: '12px', color: '#34C759', fontWeight: 600, marginBottom: '4px' }}>Ideal Answer</p>
                    <p style={{ fontSize: '12px', color: '#3C3C43', lineHeight: 1.6 }}>{turn.ideal_answer}</p>
                  </div>
                )}
              </div>
            </motion.div>
          ))}
          <div ref={bottomRef} />
        </div>
      </div>
    )
  }

  // ── EXAM PHASE ───────────────────────────────────────────────
  const vInfo = VERSION_INFO[version]
  return (
    <div style={{ flex: 1, display: 'flex', flexDirection: 'column', overflow: 'hidden', background: '#FFFFFF', fontFamily: FONT }}>

      {/* Exam header */}
      <div style={{ padding: '16px 28px', borderBottom: '1px solid rgba(0,0,0,0.07)', background: '#F9F9FB', display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexShrink: 0 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
          <span style={{ fontSize: '13px', fontWeight: 600, color: vInfo.color, background: `${vInfo.color}12`, padding: '4px 12px', borderRadius: '20px' }}>
            {version} — {vInfo.label}
          </span>
          <span style={{ fontSize: '13px', color: '#6C6C70' }}>{topic || customTopic}</span>
          {isFollowup && <span style={{ fontSize: '11px', fontWeight: 600, color: '#FF9500', background: 'rgba(255,149,0,0.1)', padding: '3px 10px', borderRadius: '20px' }}>Follow-up</span>}
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
          <span style={{ fontSize: '13px', color: '#AEAEB2' }}>Q{turnNumber} · {studentName}</span>
          <button onClick={async () => { await fetch(`${BACKEND}/api/exam/end`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ session_id: sessionId }) }); setExamComplete(true); setPhase('result') }}
            style={{ fontSize: '12px', color: '#FF3B30', background: 'transparent', border: '1px solid rgba(255,59,48,0.2)', padding: '4px 12px', borderRadius: '8px', cursor: 'pointer', fontFamily: FONT }}>
            End Exam
          </button>
        </div>
      </div>

      {/* Scrollable area */}
      <div style={{ flex: 1, overflowY: 'auto', padding: '28px 32px', display: 'flex', flexDirection: 'column', gap: '20px' }}>

        {/* Previous results */}
        {transcript.map((turn, i) => (
          <div key={i} style={{ padding: '16px', borderRadius: '12px', background: '#F9F9FB', border: '1px solid rgba(0,0,0,0.06)' }}>
            <p style={{ fontSize: '13px', fontWeight: 600, color: '#6C6C70', marginBottom: '6px' }}>Q{i+1}: {turn.question}</p>
            <p style={{ fontSize: '13px', color: '#3C3C43', marginBottom: '10px' }}>{turn.answer}</p>
            <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
              <span style={{ fontSize: '13px', fontWeight: 700, color: turn.scores.total >= 7 ? '#34C759' : turn.scores.total >= 5 ? '#FF9500' : '#FF3B30' }}>{turn.scores.total}/10</span>
              <span style={{ fontSize: '12px', color: '#6C6C70' }}>{turn.feedback}</span>
            </div>
          </div>
        ))}

        {/* Current question */}
        <motion.div
          style={{ padding: '24px', borderRadius: '16px', background: 'rgba(255,149,0,0.04)', border: '1px solid rgba(255,149,0,0.2)' }}
          initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} key={question}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '12px' }}>
            <span style={{ fontSize: '11px', fontWeight: 700, color: '#FF9500', textTransform: 'uppercase', letterSpacing: '0.08em' }}>Question {turnNumber}</span>
          </div>
          <p style={{ fontSize: '18px', fontWeight: 600, color: '#1C1C1E', lineHeight: 1.5 }}>{question}</p>
        </motion.div>

        <div ref={bottomRef} />
      </div>

      {/* Answer input */}
      <div style={{ padding: '16px 28px 20px', borderTop: '1px solid rgba(0,0,0,0.07)', background: '#F9F9FB', flexShrink: 0 }}>
        <textarea
          ref={answerRef}
          value={answer}
          onChange={e => setAnswer(e.target.value)}
          placeholder="Type your answer here… (Shift+Enter for new line, Enter to submit)"
          onKeyDown={e => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); handleSubmitAnswer() } }}
          rows={3}
          disabled={isLoading}
          style={{ width: '100%', padding: '14px 16px', borderRadius: '12px', border: '1px solid rgba(0,0,0,0.1)', fontSize: '15px', fontFamily: FONT, color: '#1C1C1E', resize: 'none', outline: 'none', background: '#FFFFFF', lineHeight: 1.6, boxSizing: 'border-box' }}
          onFocus={e => e.target.style.border = '1px solid rgba(255,149,0,0.4)'}
          onBlur={e  => e.target.style.border = '1px solid rgba(0,0,0,0.1)'}
        />
        <div style={{ display: 'flex', gap: '10px', marginTop: '10px', justifyContent: 'flex-end', alignItems: 'center' }}>
          {/* Voice button */}
          <motion.button
            onClick={listening ? stopListening : startListening}
            style={{ padding: '10px 16px', borderRadius: '10px', border: `1px solid ${listening ? '#FF3B30' : 'rgba(0,0,0,0.1)'}`, background: listening ? 'rgba(255,59,48,0.08)' : 'transparent', color: listening ? '#FF3B30' : '#6C6C70', fontSize: '13px', cursor: 'pointer', fontFamily: FONT, display: 'flex', alignItems: 'center', gap: '6px' }}
            animate={listening ? { scale: [1, 1.05, 1] } : {}}
            transition={{ duration: 0.8, repeat: listening ? Infinity : 0 }}
          >
            {listening ? '⏹ Stop' : '🎙 Voice'}
          </motion.button>

          <motion.button
            onClick={handleSubmitAnswer}
            disabled={!answer.trim() || isLoading}
            style={{ padding: '10px 24px', borderRadius: '10px', border: 'none', background: answer.trim() ? 'linear-gradient(135deg, #FF9500, #FF3B30)' : 'rgba(0,0,0,0.08)', color: answer.trim() ? '#fff' : '#AEAEB2', fontSize: '14px', fontWeight: 600, fontFamily: FONT, cursor: answer.trim() ? 'pointer' : 'default', boxShadow: answer.trim() ? '0 3px 12px rgba(255,149,0,0.35)' : 'none' }}
            whileHover={answer.trim() ? { scale: 1.03 } : {}}
            whileTap={answer.trim() ? { scale: 0.97 } : {}}
          >
            {isLoading ? 'Grading…' : 'Submit Answer →'}
          </motion.button>
        </div>
      </div>
    </div>
  )
}
