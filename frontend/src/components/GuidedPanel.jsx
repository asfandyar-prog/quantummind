import { useState, useRef, useEffect } from 'react'
import { motion, AnimatePresence } from 'framer-motion'

const FONT    = '-apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif'
const MONO    = 'SF Mono, ui-monospace, Menlo, Consolas, monospace'
const BACKEND = 'http://localhost:8000'

const SUGGESTED_TOPICS = [
  'Quantum Superposition',
  'Quantum Entanglement',
  'Hadamard Gate',
  'Bell States',
  "Grover's Algorithm",
  'Quantum Teleportation',
  'Deutsch-Jozsa Algorithm',
  'Quantum Interference',
]

// ── Render markdown-style text with code blocks ─────────────
function RichText({ content }) {
  if (!content) return null

  // Split into segments — code blocks vs normal text
  const segments = []
  const lines = content.split('\n')
  let inCode = false
  let codeLines = []
  let textLines = []

  for (const line of lines) {
    if (line.startsWith('```')) {
      if (!inCode) {
        if (textLines.length) { segments.push({ type: 'text', content: textLines.join('\n') }); textLines = [] }
        inCode = true
        codeLines = []
      } else {
        segments.push({ type: 'code', content: codeLines.join('\n') })
        codeLines = []
        inCode = false
      }
    } else if (inCode) {
      codeLines.push(line)
    } else {
      textLines.push(line)
    }
  }
  if (textLines.length) segments.push({ type: 'text', content: textLines.join('\n') })

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
      {segments.map((seg, i) => {
        if (seg.type === 'code') {
          return (
            <pre key={i} style={{
              background: '#1A1A2E', color: '#CDD6F4',
              fontFamily: MONO, fontSize: '13px', lineHeight: '1.75',
              padding: '16px 20px', borderRadius: '12px',
              overflowX: 'auto', margin: 0,
              boxShadow: '0 3px 12px rgba(0,0,0,0.14)',
            }}>
              {seg.content}
            </pre>
          )
        }
        return (
          <div key={i} style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
            {seg.content.split('\n').map((line, j) => {
              if (!line.trim()) return <br key={j} />
              const html = line
                .replace(/\*\*(.+?)\*\*/g, '<strong style="font-weight:600">$1</strong>')
                .replace(/\*(.+?)\*/g, '<em style="font-style:italic">$1</em>')
              return <span key={j} dangerouslySetInnerHTML={{ __html: html }} style={{ lineHeight: '1.75', fontSize: '15px' }} />
            })}
          </div>
        )
      })}
    </div>
  )
}

export default function GuidedPanel() {
  const [phase, setPhase]         = useState('pick')     // pick | loading | lesson | complete
  const [topic, setTopic]         = useState('')
  const [customTopic, setCustomTopic] = useState('')
  const [plan, setPlan]           = useState(null)        // lesson plan from backend
  const [currentStep, setCurrentStep] = useState(0)      // 0-indexed
  const [stepContent, setStepContent] = useState('')     // teaching content for current step
  const [loadingStep, setLoadingStep] = useState(false)
  const [checkAnswer, setCheckAnswer] = useState('')
  const [gradeResult, setGradeResult] = useState(null)   // { passed, feedback }
  const [grading, setGrading]     = useState(false)
  const [unlockedSteps, setUnlockedSteps] = useState([0]) // which steps are unlocked
  const answerRef = useRef(null)

  // Load teaching content when step changes
  useEffect(() => {
    if (plan && phase === 'lesson') {
      loadStepContent(plan.steps[currentStep], currentStep + 1)
    }
  }, [currentStep, plan, phase])

  async function startLesson(selectedTopic) {
    setTopic(selectedTopic)
    setPhase('loading')
    setPlan(null)
    setCurrentStep(0)
    setUnlockedSteps([0])
    setGradeResult(null)
    setCheckAnswer('')

    try {
      const res = await fetch(`${BACKEND}/api/lesson/plan`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ topic: selectedTopic }),
      })
      const data = await res.json()
      setPlan(data)
      setPhase('lesson')
    } catch (e) {
      setPhase('pick')
      alert('Failed to generate lesson. Is the backend running?')
    }
  }

  async function loadStepContent(step, stepNum) {
    setLoadingStep(true)
    setStepContent('')
    setGradeResult(null)
    setCheckAnswer('')

    try {
      const res = await fetch(`${BACKEND}/api/lesson/teach`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ topic, step, step_num: stepNum }),
      })
      const data = await res.json()
      setStepContent(data.content)
    } catch (e) {
      setStepContent('Failed to load step content. Please try again.')
    } finally {
      setLoadingStep(false)
    }
  }

  async function handleGrade() {
    if (!checkAnswer.trim() || grading) return
    const step = plan.steps[currentStep]
    setGrading(true)

    try {
      const res = await fetch(`${BACKEND}/api/lesson/grade`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          question: step.check_question,
          correct_answer: step.check_answer,
          student_answer: checkAnswer,
        }),
      })
      const result = await res.json()
      setGradeResult(result)

      if (result.passed) {
        // Unlock next step
        const nextStep = currentStep + 1
        if (nextStep < plan.steps.length) {
          setUnlockedSteps(prev => [...new Set([...prev, nextStep])])
        } else {
          // All steps done — show completion
          setTimeout(() => setPhase('complete'), 1500)
        }
      }
    } catch (e) {
      setGradeResult({ passed: false, feedback: 'Grading failed. Please try again.' })
    } finally {
      setGrading(false)
    }
  }

  function goToNextStep() {
    const next = currentStep + 1
    if (next < plan.steps.length && unlockedSteps.includes(next)) {
      setCurrentStep(next)
      setGradeResult(null)
      setCheckAnswer('')
    }
  }

  function reset() {
    setPhase('pick')
    setTopic('')
    setPlan(null)
    setCurrentStep(0)
    setGradeResult(null)
    setCheckAnswer('')
    setCustomTopic('')
  }

  // ── PHASE: TOPIC PICKER ──────────────────────────────────────
  if (phase === 'pick') {
    return (
      <div style={{ flex:1, display:'flex', flexDirection:'column', alignItems:'center', justifyContent:'center', padding:'40px', background:'#FFFFFF', fontFamily:FONT, overflowY:'auto' }}>
        <motion.div style={{ width:'100%', maxWidth:'860px', textAlign:'center' }} initial={{ opacity:0, y:16 }} animate={{ opacity:1, y:0 }} transition={{ duration:0.4 }}>

          <div style={{ fontSize:'48px', marginBottom:'20px' }}>🎯</div>
          <h1 style={{ fontSize:'34px', fontWeight:700, color:'#1C1C1E', letterSpacing:'-0.5px', marginBottom:'10px' }}>
            What do you want to learn?
          </h1>
          <p style={{ fontSize:'17px', color:'#6C6C70', marginBottom:'40px', lineHeight:1.6 }}>
            Choose a topic and I'll guide you through it step by step — with a check question at each stage to make sure you've understood before moving on.
          </p>

          {/* Topic grid */}
          <div style={{ display:'grid', gridTemplateColumns:'1fr 1fr', gap:'12px', marginBottom:'28px' }}>
            {SUGGESTED_TOPICS.map((t, i) => (
              <motion.button
                key={t}
                onClick={() => startLesson(t)}
                style={{ padding:'20px 24px', borderRadius:'16px', border:'1px solid rgba(0,0,0,0.08)', background:'#FFFFFF', color:'#1C1C1E', fontSize:'16px', fontFamily:FONT, textAlign:'left', cursor:'pointer', fontWeight:500, boxShadow:'0 1px 4px rgba(0,0,0,0.05)' }}
                initial={{ opacity:0, y:8 }}
                animate={{ opacity:1, y:0 }}
                transition={{ delay: i * 0.05 }}
                whileHover={{ y:-3, boxShadow:'0 6px 20px rgba(0,0,0,0.09)', borderColor:'rgba(88,86,214,0.3)' }}
                whileTap={{ scale:0.97 }}
              >
                <span style={{ color:'#5856D6', marginRight:'10px' }}>→</span>{t}
              </motion.button>
            ))}
          </div>

          {/* Custom topic input */}
          <div style={{ display:'flex', gap:'10px', alignItems:'center' }}>
            <input
              value={customTopic}
              onChange={e => setCustomTopic(e.target.value)}
              placeholder="Or type any quantum topic..."
              onKeyDown={e => { if (e.key === 'Enter' && customTopic.trim()) startLesson(customTopic.trim()) }}
              style={{ flex:1, padding:'15px 20px', borderRadius:'14px', border:'1px solid rgba(0,0,0,0.1)', fontSize:'16px', fontFamily:FONT, color:'#1C1C1E', outline:'none', background:'#F9F9FB' }}
              onFocus={e => e.target.style.border='1px solid rgba(88,86,214,0.4)'}
              onBlur={e  => e.target.style.border='1px solid rgba(0,0,0,0.1)'}
            />
            <motion.button
              onClick={() => customTopic.trim() && startLesson(customTopic.trim())}
              disabled={!customTopic.trim()}
              style={{ padding:'15px 28px', borderRadius:'14px', border:'none', background: customTopic.trim() ? 'linear-gradient(135deg, #5856D6, #007AFF)' : 'rgba(0,0,0,0.08)', color: customTopic.trim() ? '#fff' : '#AEAEB2', fontSize:'15px', fontWeight:600, fontFamily:FONT, cursor: customTopic.trim() ? 'pointer' : 'default', boxShadow: customTopic.trim() ? '0 4px 14px rgba(88,86,214,0.3)' : 'none' }}
              whileHover={customTopic.trim() ? { scale:1.03 } : {}}
              whileTap={customTopic.trim() ? { scale:0.97 } : {}}
            >
              Start →
            </motion.button>
          </div>
        </motion.div>
      </div>
    )
  }

  // ── PHASE: LOADING ───────────────────────────────────────────
  if (phase === 'loading') {
    return (
      <div style={{ flex:1, display:'flex', flexDirection:'column', alignItems:'center', justifyContent:'center', background:'#FFFFFF', fontFamily:FONT, gap:'20px' }}>
        <motion.div animate={{ rotate:360 }} transition={{ duration:1.2, repeat:Infinity, ease:'linear' }} style={{ width:'48px', height:'48px', borderRadius:'50%', border:'3px solid rgba(88,86,214,0.15)', borderTopColor:'#5856D6' }} />
        <div style={{ textAlign:'center' }}>
          <p style={{ fontSize:'17px', fontWeight:600, color:'#1C1C1E', marginBottom:'6px' }}>Preparing your lesson</p>
          <p style={{ fontSize:'14px', color:'#6C6C70' }}>Designing a step-by-step plan for <strong>{topic}</strong></p>
        </div>
      </div>
    )
  }

  // ── PHASE: COMPLETE ──────────────────────────────────────────
  if (phase === 'complete') {
    return (
      <div style={{ flex:1, display:'flex', flexDirection:'column', alignItems:'center', justifyContent:'center', background:'#FFFFFF', fontFamily:FONT, padding:'40px' }}>
        <motion.div style={{ textAlign:'center', maxWidth:'500px' }} initial={{ opacity:0, scale:0.9 }} animate={{ opacity:1, scale:1 }} transition={{ duration:0.5, ease:[0.16,1,0.3,1] }}>
          <div style={{ fontSize:'64px', marginBottom:'20px' }}>🎉</div>
          <h1 style={{ fontSize:'28px', fontWeight:700, color:'#1C1C1E', marginBottom:'12px' }}>Lesson Complete!</h1>
          <p style={{ fontSize:'16px', color:'#6C6C70', lineHeight:1.6, marginBottom:'10px' }}>
            You've completed all {plan.steps.length} steps of <strong style={{ color:'#1C1C1E' }}>{topic}</strong>.
          </p>
          <div style={{ padding:'20px', borderRadius:'16px', background:'rgba(88,86,214,0.06)', border:'1px solid rgba(88,86,214,0.15)', marginBottom:'28px' }}>
            <p style={{ fontSize:'14px', color:'#5856D6', fontWeight:600, marginBottom:'10px' }}>What you learned:</p>
            {plan.steps.map((s, i) => (
              <div key={i} style={{ display:'flex', alignItems:'center', gap:'10px', marginBottom:'6px' }}>
                <span style={{ color:'#34C759', fontSize:'16px' }}>✓</span>
                <span style={{ fontSize:'14px', color:'#3C3C43' }}>{s.title}</span>
              </div>
            ))}
          </div>
          <motion.button
            onClick={reset}
            style={{ padding:'14px 32px', borderRadius:'14px', border:'none', background:'linear-gradient(135deg, #5856D6, #007AFF)', color:'#fff', fontSize:'16px', fontWeight:600, fontFamily:FONT, cursor:'pointer', boxShadow:'0 4px 16px rgba(88,86,214,0.35)' }}
            whileHover={{ scale:1.04 }} whileTap={{ scale:0.96 }}
          >
            Learn another topic →
          </motion.button>
        </motion.div>
      </div>
    )
  }

  // ── PHASE: LESSON ────────────────────────────────────────────
  const step    = plan.steps[currentStep]
  const isLast  = currentStep === plan.steps.length - 1
  const isPassed = gradeResult?.passed

  return (
    <div style={{ flex:1, display:'flex', overflow:'hidden', background:'#FFFFFF', fontFamily:FONT }}>

      {/* Step progress sidebar */}
      <div style={{ width:'220px', minWidth:'220px', borderRight:'1px solid rgba(0,0,0,0.07)', padding:'24px 16px', background:'#FAFAFA', display:'flex', flexDirection:'column', gap:'8px' }}>
        <p style={{ fontSize:'11px', fontWeight:600, letterSpacing:'0.08em', textTransform:'uppercase', color:'#AEAEB2', marginBottom:'8px' }}>
          {topic}
        </p>
        {plan.steps.map((s, i) => {
          const isActive   = i === currentStep
          const isDone     = unlockedSteps.includes(i + 1) || (i === plan.steps.length - 1 && phase === 'complete')
          const isLocked   = !unlockedSteps.includes(i)
          return (
            <motion.button
              key={i}
              onClick={() => !isLocked && setCurrentStep(i)}
              disabled={isLocked}
              style={{
                display:'flex', alignItems:'center', gap:'10px',
                padding:'10px 12px', borderRadius:'10px', border:'none',
                background: isActive ? 'rgba(88,86,214,0.08)' : 'transparent',
                cursor: isLocked ? 'not-allowed' : 'pointer',
                textAlign:'left', fontFamily:FONT, width:'100%',
                opacity: isLocked ? 0.4 : 1,
                transition:'all 0.15s',
              }}
              whileHover={!isLocked && !isActive ? { background:'rgba(0,0,0,0.04)' } : {}}
            >
              {/* Step indicator */}
              <div style={{
                width:'26px', height:'26px', borderRadius:'50%', flexShrink:0,
                display:'flex', alignItems:'center', justifyContent:'center',
                fontSize:'12px', fontWeight:700,
                background: isDone && !isActive ? '#34C759' : isActive ? '#5856D6' : 'rgba(0,0,0,0.08)',
                color: isDone || isActive ? '#fff' : '#6C6C70',
              }}>
                {isDone && !isActive ? '✓' : i + 1}
              </div>
              <div>
                <p style={{ fontSize:'12px', fontWeight: isActive ? 600 : 400, color: isActive ? '#5856D6' : '#3C3C43', lineHeight:1.3 }}>{s.title}</p>
                {isLocked && <p style={{ fontSize:'10px', color:'#AEAEB2' }}>🔒 Locked</p>}
              </div>
            </motion.button>
          )
        })}

        <button onClick={reset} style={{ marginTop:'auto', padding:'8px', borderRadius:'8px', border:'1px solid rgba(0,0,0,0.08)', background:'transparent', color:'#AEAEB2', fontSize:'12px', cursor:'pointer', fontFamily:FONT }}>
          ← Pick new topic
        </button>
      </div>

      {/* Main lesson content */}
      <div style={{ flex:1, display:'flex', flexDirection:'column', overflow:'hidden' }}>
        {/* Step header */}
        <div style={{ padding:'24px 36px 20px', borderBottom:'1px solid rgba(0,0,0,0.07)', flexShrink:0 }}>
          <div style={{ display:'flex', alignItems:'center', gap:'8px', marginBottom:'8px' }}>
            <span style={{ fontSize:'12px', fontWeight:600, color:'#5856D6', letterSpacing:'0.06em', textTransform:'uppercase' }}>Step {currentStep + 1} of {plan.steps.length}</span>
          </div>
          <h1 style={{ fontSize:'24px', fontWeight:700, color:'#1C1C1E', letterSpacing:'-0.3px' }}>{step.title}</h1>
          <p style={{ fontSize:'14px', color:'#6C6C70', marginTop:'4px' }}>{step.objective}</p>
        </div>

        {/* Scrollable content */}
        <div style={{ flex:1, overflowY:'auto', padding:'28px 36px', display:'flex', flexDirection:'column', gap:'24px', scrollbarWidth:'thin' }}>

          {/* Teaching content */}
          {loadingStep ? (
            <div style={{ display:'flex', alignItems:'center', gap:'12px', color:'#6C6C70', fontSize:'14px' }}>
              <motion.div animate={{ rotate:360 }} transition={{ duration:1, repeat:Infinity, ease:'linear' }} style={{ width:'20px', height:'20px', borderRadius:'50%', border:'2px solid rgba(88,86,214,0.2)', borderTopColor:'#5856D6' }} />
              Preparing lesson content…
            </div>
          ) : (
            <motion.div
              style={{ fontSize:'15px', lineHeight:'1.75', color:'#1C1C1E' }}
              initial={{ opacity:0, y:8 }}
              animate={{ opacity:1, y:0 }}
              transition={{ duration:0.35 }}
            >
              <RichText content={stepContent} />
            </motion.div>
          )}

          {/* Check question — shown after content loads */}
          {!loadingStep && stepContent && (
            <motion.div
              style={{ background:'rgba(88,86,214,0.04)', border:'1px solid rgba(88,86,214,0.15)', borderRadius:'16px', padding:'24px' }}
              initial={{ opacity:0, y:10 }}
              animate={{ opacity:1, y:0 }}
              transition={{ delay:0.3, duration:0.35 }}
            >
              <div style={{ display:'flex', alignItems:'center', gap:'8px', marginBottom:'14px' }}>
                <span style={{ fontSize:'18px' }}>🎯</span>
                <p style={{ fontSize:'13px', fontWeight:600, color:'#5856D6', letterSpacing:'0.04em', textTransform:'uppercase' }}>Check your understanding</p>
              </div>
              <p style={{ fontSize:'16px', fontWeight:600, color:'#1C1C1E', marginBottom:'16px', lineHeight:1.5 }}>
                {step.check_question}
              </p>

              {/* Answer input */}
              {!gradeResult && (
                <div style={{ display:'flex', flexDirection:'column', gap:'10px' }}>
                  <textarea
                    ref={answerRef}
                    value={checkAnswer}
                    onChange={e => setCheckAnswer(e.target.value)}
                    placeholder="Type your answer here…"
                    rows={3}
                    style={{ padding:'12px 16px', borderRadius:'10px', border:'1px solid rgba(88,86,214,0.2)', fontSize:'15px', fontFamily:FONT, color:'#1C1C1E', resize:'none', outline:'none', background:'#FFFFFF', lineHeight:1.5 }}
                    onFocus={e => e.target.style.border='1px solid rgba(88,86,214,0.5)'}
                    onBlur={e  => e.target.style.border='1px solid rgba(88,86,214,0.2)'}
                  />
                  <motion.button
                    onClick={handleGrade}
                    disabled={!checkAnswer.trim() || grading}
                    style={{ alignSelf:'flex-start', padding:'10px 24px', borderRadius:'10px', border:'none', background: checkAnswer.trim() ? 'linear-gradient(135deg, #5856D6, #007AFF)' : 'rgba(0,0,0,0.08)', color: checkAnswer.trim() ? '#fff' : '#AEAEB2', fontSize:'14px', fontWeight:600, fontFamily:FONT, cursor: checkAnswer.trim() ? 'pointer' : 'default', boxShadow: checkAnswer.trim() ? '0 3px 12px rgba(88,86,214,0.3)' : 'none' }}
                    whileHover={checkAnswer.trim() ? { scale:1.03 } : {}}
                    whileTap={checkAnswer.trim() ? { scale:0.97 } : {}}
                  >
                    {grading ? 'Checking…' : 'Submit Answer'}
                  </motion.button>
                </div>
              )}

              {/* Grade result */}
              {gradeResult && (
                <motion.div
                  style={{ padding:'16px', borderRadius:'12px', background: gradeResult.passed ? 'rgba(52,199,89,0.08)' : 'rgba(255,59,48,0.06)', border:`1px solid ${gradeResult.passed ? 'rgba(52,199,89,0.25)' : 'rgba(255,59,48,0.2)'}` }}
                  initial={{ opacity:0, scale:0.96 }}
                  animate={{ opacity:1, scale:1 }}
                  transition={{ duration:0.25 }}
                >
                  <div style={{ display:'flex', alignItems:'center', gap:'8px', marginBottom:'8px' }}>
                    <span style={{ fontSize:'20px' }}>{gradeResult.passed ? '✅' : '❌'}</span>
                    <span style={{ fontSize:'14px', fontWeight:700, color: gradeResult.passed ? '#34C759' : '#FF3B30' }}>
                      {gradeResult.passed ? 'Correct!' : 'Not quite right'}
                    </span>
                  </div>
                  <p style={{ fontSize:'14px', color:'#3C3C43', lineHeight:1.6 }}>{gradeResult.feedback}</p>

                  {!gradeResult.passed && (
                    <button
                      onClick={() => { setGradeResult(null); setCheckAnswer('') }}
                      style={{ marginTop:'12px', padding:'8px 18px', borderRadius:'8px', border:'1px solid rgba(0,0,0,0.1)', background:'transparent', color:'#6C6C70', fontSize:'13px', cursor:'pointer', fontFamily:FONT }}
                    >
                      Try again
                    </button>
                  )}

                  {gradeResult.passed && !isLast && (
                    <motion.button
                      onClick={goToNextStep}
                      style={{ marginTop:'12px', padding:'10px 22px', borderRadius:'10px', border:'none', background:'linear-gradient(135deg, #34C759, #30D158)', color:'#fff', fontSize:'14px', fontWeight:600, fontFamily:FONT, cursor:'pointer', boxShadow:'0 3px 10px rgba(52,199,89,0.3)' }}
                      whileHover={{ scale:1.03 }} whileTap={{ scale:0.97 }}
                    >
                      Next Step →
                    </motion.button>
                  )}

                  {gradeResult.passed && isLast && (
                    <motion.button
                      onClick={() => setPhase('complete')}
                      style={{ marginTop:'12px', padding:'10px 22px', borderRadius:'10px', border:'none', background:'linear-gradient(135deg, #5856D6, #007AFF)', color:'#fff', fontSize:'14px', fontWeight:600, fontFamily:FONT, cursor:'pointer', boxShadow:'0 3px 10px rgba(88,86,214,0.3)' }}
                      whileHover={{ scale:1.03 }} whileTap={{ scale:0.97 }}
                    >
                      Complete Lesson 🎉
                    </motion.button>
                  )}
                </motion.div>
              )}
            </motion.div>
          )}
        </div>
      </div>
    </div>
  )
}