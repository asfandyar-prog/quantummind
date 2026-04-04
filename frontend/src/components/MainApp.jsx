import { useNavigate } from 'react-router-dom'
import { motion, AnimatePresence } from 'framer-motion'
import useAppState from '@/hooks/useAppState'
import Sidebar from '@/components/Sidebar'
import CourseSidebar from '@/components/CourseSidebar'
import ChatPanel from '@/components/ChatPanel'
import CoursePanel from '@/components/CoursePanel'
import CircuitVisualizer from '@/components/CircuitVisualizer'
import ConceptCards from '@/components/ConceptCards'
import CodeEditor from '@/components/CodeEditor'
import GuidedPanel from '@/components/GuidedPanel'
import PracticeAssistant from '@/components/PracticeAssistant'
import clsx from 'clsx'

const FONT = '-apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif'

const PANEL_TABS = [
  { id: 'circuit',  label: 'Circuit'  },
  { id: 'concepts', label: 'Concepts' },
  { id: 'code',     label: 'Code'     },
]

const MODE_META = {
  theory:   { label: 'Theory Mode',   color: '#007AFF', bg: 'rgba(0,122,255,0.07)'   },
  practice: { label: 'Practice Mode', color: '#32ADE6', bg: 'rgba(50,173,230,0.07)'  },
  guided:   { label: 'Guided Mode',   color: '#5856D6', bg: 'rgba(88,86,214,0.07)'   },
  course:   { label: 'Course Mode',   color: '#34C759', bg: 'rgba(52,199,89,0.07)'   },
}

export default function MainApp() {
  const navigate         = useNavigate()
  const mode             = useAppState(s => s.mode)
  const activePanel      = useAppState(s => s.activePanel)
  const setPanel         = useAppState(s => s.setActivePanel)
  const activeTopicId    = useAppState(s => s.activeTopicId)
  const setActiveTopicId = useAppState(s => s.setActiveTopicId)
  const activeWeek       = useAppState(s => s.activeWeek)
  const setActiveWeek    = useAppState(s => s.setActiveWeek)
  const completedTopics  = useAppState(s => s.completedTopics)
  const markTopicComplete = useAppState(s => s.markTopicComplete)

  const meta       = MODE_META[mode] ?? MODE_META.guided
  const isTheory   = mode === 'theory'
  const isPractice = mode === 'practice'
  const isCourse   = mode === 'course'

  function handleSelectTopic(topicId, week) {
    setActiveTopicId(topicId)
    setActiveWeek(week)
  }

  return (
    <div style={{ width:'100%', height:'100%', display:'flex', flexDirection:'column', overflow:'hidden', background:'#F2F2F7', fontFamily: FONT }}>

      <Topbar meta={meta} onBack={() => navigate('/select')} />

      <div style={{ display:'flex', flex:1, overflow:'hidden' }}>

        {/* ── COURSE MODE ── */}
        {isCourse && (
          <>
            <CourseSidebar
              activeTopicId={activeTopicId}
              activeWeek={activeWeek}
              onSelectTopic={handleSelectTopic}
              completedTopics={completedTopics}
            />
            <CoursePanel
              activeTopicId={activeTopicId}
              activeWeek={activeWeek}
              onMarkComplete={markTopicComplete}
              completedTopics={completedTopics}
            />
          </>
        )}

        {/* ── PRACTICE MODE ── */}
        {isPractice && (
          <motion.div
            key="practice"
            style={{ display:'flex', flex:1, overflow:'hidden' }}
            initial={{ opacity:0 }} animate={{ opacity:1 }} transition={{ duration:0.3 }}
          >
            <div style={{ flex:1, overflow:'hidden', minWidth:0 }}>
              <CodeEditor />
            </div>
            <PracticeAssistant />
          </motion.div>
        )}

        {/* ── GUIDED MODE ── */}
        {!isPractice && !isCourse && mode === 'guided' && (
          <motion.div
            key="guided"
            style={{ display:'flex', flex:1, overflow:'hidden' }}
            initial={{ opacity:0 }} animate={{ opacity:1 }} transition={{ duration:0.3 }}
          >
            <GuidedPanel />
          </motion.div>
        )}

        {/* ── THEORY MODE ── */}
        {!isPractice && !isCourse && mode !== 'guided' && (
          <motion.div
            key="chat"
            style={{ display:'flex', flex:1, overflow:'hidden' }}
            initial={{ opacity:0 }} animate={{ opacity:1 }} transition={{ duration:0.3 }}
          >
            <Sidebar />

            <div style={{ flex:1, overflow:'hidden', background:'#FFFFFF', borderRight: isTheory ? 'none' : '1px solid rgba(0,0,0,0.07)' }}>
              <ChatPanel />
            </div>

            <AnimatePresence>
              {!isTheory && (
                <motion.div
                  key="right-panel"
                  style={{ width:'320px', minWidth:'320px', display:'flex', flexDirection:'column', overflow:'hidden', background:'#FFFFFF' }}
                  initial={{ x:40, opacity:0 }} animate={{ x:0, opacity:1 }} exit={{ x:40, opacity:0 }}
                  transition={{ duration:0.35, ease:[0.16,1,0.3,1] }}
                >
                  <div style={{ display:'flex', background:'#F7F7FA', borderBottom:'1px solid rgba(0,0,0,0.07)', padding:'0 4px', flexShrink:0 }}>
                    {PANEL_TABS.map(tab => {
                      const active = activePanel === tab.id
                      return (
                        <button key={tab.id} onClick={() => setPanel(tab.id)} style={{ flex:1, padding:'12px 8px', fontSize:'11px', fontWeight: active ? 600 : 400, fontFamily:FONT, letterSpacing:'0.06em', textTransform:'uppercase', color: active ? meta.color : '#AEAEB2', background:'transparent', border:'none', borderBottom:`2px solid ${active ? meta.color : 'transparent'}`, cursor:'pointer', transition:'all 0.18s', outline:'none' }}>
                          {tab.label}
                        </button>
                      )
                    })}
                  </div>
                  <div style={{ flex:1, overflowY:'auto', padding:'20px 16px' }}>
                    <AnimatePresence mode="wait">
                      <motion.div key={activePanel} initial={{ opacity:0, y:8 }} animate={{ opacity:1, y:0 }} exit={{ opacity:0 }} transition={{ duration:0.2 }}>
                        {activePanel === 'circuit'  && <CircuitVisualizer />}
                        {activePanel === 'concepts' && <ConceptCards />}
                        {activePanel === 'code'     && <CodePanel />}
                      </motion.div>
                    </AnimatePresence>
                  </div>
                </motion.div>
              )}
            </AnimatePresence>
          </motion.div>
        )}
      </div>
    </div>
  )
}

function Topbar({ meta, onBack }) {
  return (
    <motion.header
      style={{ height:'56px', display:'flex', alignItems:'center', padding:'0 20px', gap:'12px', flexShrink:0, background:'rgba(255,255,255,0.85)', backdropFilter:'blur(20px)', WebkitBackdropFilter:'blur(20px)', borderBottom:'1px solid rgba(0,0,0,0.08)', fontFamily:FONT, zIndex:10 }}
      initial={{ y:-8, opacity:0 }} animate={{ y:0, opacity:1 }} transition={{ duration:0.3 }}
    >
      <div style={{ display:'flex', alignItems:'center', gap:'8px' }}>
        <span style={{ fontSize:'18px', fontWeight:700, letterSpacing:'-0.5px', background:'linear-gradient(135deg, #007AFF, #5856D6)', WebkitBackgroundClip:'text', WebkitTextFillColor:'transparent', backgroundClip:'text' }}>
          QuantumMind
        </span>
        <span style={{ fontSize:'10px', fontWeight:600, letterSpacing:'0.08em', textTransform:'uppercase', color:'#007AFF', background:'rgba(0,122,255,0.08)', border:'1px solid rgba(0,122,255,0.2)', padding:'2px 8px', borderRadius:'20px' }}>
          Beta
        </span>
      </div>

      <div style={{ marginLeft:'auto', display:'flex', alignItems:'center', gap:'12px' }}>
        <div style={{ display:'flex', alignItems:'center', gap:'7px', background:meta.bg, border:`1px solid ${meta.color}22`, padding:'6px 14px', borderRadius:'20px' }}>
          <div style={{ width:7, height:7, borderRadius:'50%', background:meta.color, flexShrink:0 }} />
          <span style={{ fontSize:'13px', fontWeight:500, color:meta.color }}>{meta.label}</span>
        </div>
        <button onClick={onBack} style={{ display:'flex', alignItems:'center', gap:'6px', fontSize:'13px', fontWeight:500, color:'#6C6C70', background:'transparent', border:'1px solid rgba(0,0,0,0.1)', padding:'6px 14px', borderRadius:'10px', cursor:'pointer', fontFamily:FONT, transition:'all 0.15s' }}
          onMouseEnter={e => { e.target.style.background='#F2F2F7'; e.target.style.color='#1C1C1E' }}
          onMouseLeave={e => { e.target.style.background='transparent'; e.target.style.color='#6C6C70' }}>
          ← Change mode
        </button>
      </div>
    </motion.header>
  )
}

function CodePanel() {
  const CODE = `# Bell State — Qiskit
from qiskit import QuantumCircuit
from qiskit_aer import AerSimulator

qc = QuantumCircuit(2, 2)
qc.h(0)
qc.cx(0, 1)
qc.measure([0, 1], [0, 1])

sim = AerSimulator()
job = sim.run(qc, shots=1024)
counts = job.result().get_counts()
print(counts)`

  return (
    <div style={{ display:'flex', flexDirection:'column', gap:'12px', fontFamily:FONT }}>
      <pre style={{ background:'#1A1A2E', color:'#CDD6F4', fontFamily:'SF Mono, monospace', fontSize:'12px', lineHeight:'1.75', padding:'16px', borderRadius:'12px', overflowX:'auto', margin:0 }}>
        {CODE}
      </pre>
      <div style={{ display:'flex', gap:'8px' }}>
        <button style={{ flex:1, padding:'10px', borderRadius:'10px', background:'linear-gradient(135deg, #007AFF, #32ADE6)', color:'#fff', fontSize:'13px', fontWeight:600, border:'none', cursor:'pointer', fontFamily:FONT }}>▶  Run</button>
        <button style={{ padding:'10px 18px', borderRadius:'10px', background:'transparent', color:'#6C6C70', fontSize:'13px', border:'1px solid rgba(0,0,0,0.10)', cursor:'pointer', fontFamily:FONT }}>Copy</button>
      </div>
      <div style={{ background:'#F9F9FB', border:'1px solid rgba(0,0,0,0.07)', borderRadius:'10px', padding:'14px 16px' }}>
        <div style={{ fontSize:'10px', fontWeight:600, letterSpacing:'0.1em', textTransform:'uppercase', color:'#007AFF', marginBottom:'8px' }}>Output</div>
        <div style={{ fontFamily:'SF Mono, monospace', fontSize:'12px', color:'#34C759' }}>{`{'00': 512, '11': 512}`}</div>
      </div>
    </div>
  )
}