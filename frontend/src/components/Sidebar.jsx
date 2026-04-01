import { motion } from 'framer-motion'
import useAppState from '@/hooks/useAppState'

const FONT = '-apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif'

const CURRICULUM = [
  { id: 'quantum-basics',    label: 'Quantum Basics',     done: true  },
  { id: 'superposition',     label: 'Superposition',      done: true  },
  { id: 'entanglement',      label: 'Entanglement',       done: false },
  { id: 'quantum-gates',     label: 'Quantum Gates',      done: false },
  { id: 'grovers-algorithm', label: "Grover's Algorithm", done: false },
  { id: 'shors-algorithm',   label: "Shor's Algorithm",   done: false },
]

const MY_WORK = [
  { id: 'saved-circuits', label: 'Saved Circuits' },
  { id: 'code-history',   label: 'Code History'   },
]

const COMPLETED = CURRICULUM.filter(m => m.done).length
const TOTAL = CURRICULUM.length

export default function Sidebar() {
  const activeModule    = useAppState(s => s.activeModule)
  const setActiveModule = useAppState(s => s.setActiveModule)

  return (
    <motion.aside
      style={{
        width: '224px', minWidth: '224px',
        display: 'flex', flexDirection: 'column',
        background: '#F7F7FA',
        borderRight: '1px solid rgba(0,0,0,0.07)',
        overflow: 'hidden',
        fontFamily: FONT,
      }}
      initial={{ x: -16, opacity: 0 }}
      animate={{ x: 0, opacity: 1 }}
      transition={{ duration: 0.35, delay: 0.08 }}
    >
      {/* ── Curriculum ── */}
      <SectionLabel>Curriculum</SectionLabel>
      <nav>
        {CURRICULUM.map((mod, i) => (
          <SidebarItem
            key={mod.id}
            label={mod.label}
            isActive={activeModule === mod.id}
            isDone={mod.done}
            index={i}
            onClick={() => setActiveModule(mod.id)}
          />
        ))}
      </nav>

      {/* ── My Work ── */}
      <SectionLabel style={{ marginTop: '8px' }}>My Work</SectionLabel>
      <nav>
        {MY_WORK.map((item, i) => (
          <SidebarItem
            key={item.id}
            label={item.label}
            isActive={activeModule === item.id}
            isDone={false}
            isSecondary
            index={i}
            onClick={() => setActiveModule(item.id)}
          />
        ))}
      </nav>

      {/* ── Progress ── */}
      <div style={{
        marginTop: 'auto',
        padding: '16px',
        borderTop: '1px solid rgba(0,0,0,0.07)',
      }}>
        <div style={{ display:'flex', justifyContent:'space-between', alignItems:'center', marginBottom:'10px' }}>
          <span style={{ fontSize:'11px', fontWeight:600, letterSpacing:'0.08em', textTransform:'uppercase', color:'#AEAEB2' }}>
            Progress
          </span>
          <span style={{ fontSize:'12px', fontWeight:500, color:'#6C6C70' }}>
            {COMPLETED}/{TOTAL}
          </span>
        </div>
        <div style={{ height:'5px', background:'rgba(0,0,0,0.08)', borderRadius:'3px', overflow:'hidden' }}>
          <motion.div
            style={{ height:'100%', borderRadius:'3px', background:'linear-gradient(90deg, #007AFF, #32ADE6)' }}
            initial={{ width:'0%' }}
            animate={{ width:`${(COMPLETED/TOTAL)*100}%` }}
            transition={{ duration:0.9, delay:0.5, ease:'easeOut' }}
          />
        </div>
      </div>
    </motion.aside>
  )
}

function SectionLabel({ children }) {
  return (
    <p style={{
      fontSize: '11px', fontWeight: 600,
      letterSpacing: '0.08em', textTransform: 'uppercase',
      color: '#AEAEB2', padding: '18px 16px 6px',
      fontFamily: FONT,
    }}>
      {children}
    </p>
  )
}

function SidebarItem({ label, isActive, isDone, isSecondary, index, onClick }) {
  return (
    <motion.button
      onClick={onClick}
      style={{
        display: 'flex', alignItems: 'center', gap: '10px',
        width: '100%', padding: '9px 16px',
        fontSize: '14px', fontWeight: isActive ? 600 : 400,
        color: isActive ? '#007AFF' : '#3C3C43',
        background: isActive ? 'rgba(0,122,255,0.08)' : 'transparent',
        border: 'none', cursor: 'pointer', textAlign: 'left',
        position: 'relative', transition: 'all 0.15s ease',
        fontFamily: FONT,
      }}
      initial={{ opacity: 0, x: -8 }}
      animate={{ opacity: 1, x: 0 }}
      transition={{ delay: 0.1 + index * 0.04 }}
      onMouseEnter={e => { if (!isActive) e.currentTarget.style.background = 'rgba(0,0,0,0.03)' }}
      onMouseLeave={e => { if (!isActive) e.currentTarget.style.background = 'transparent' }}
    >
      {/* Active left bar */}
      {isActive && (
        <span style={{
          position: 'absolute', left: 0, top: '20%', bottom: '20%',
          width: '3px', borderRadius: '0 3px 3px 0',
          background: '#007AFF',
        }} />
      )}

      {/* Status icon */}
      <span style={{
        fontSize: '13px', width: '16px', textAlign: 'center', flexShrink: 0,
        color: isActive ? '#007AFF' : isDone ? '#34C759' : '#AEAEB2',
      }}>
        {isSecondary ? '◇' : isDone ? '●' : '○'}
      </span>

      <span>{label}</span>
    </motion.button>
  )
}