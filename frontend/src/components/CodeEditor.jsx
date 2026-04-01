import { useState, useRef } from 'react'
import Editor from '@monaco-editor/react'
import { motion, AnimatePresence } from 'framer-motion'

const FONT = '-apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif'
const MONO = 'SF Mono, ui-monospace, Menlo, Consolas, monospace'

const STARTER_CODE = `# QuantumMind — Practice Mode
# Write your Qiskit code here and press Run

from qiskit import QuantumCircuit
from qiskit_aer import AerSimulator
from qiskit.visualization import plot_histogram

# Create a Bell State
qc = QuantumCircuit(2, 2)
qc.h(0)        # Hadamard on qubit 0
qc.cx(0, 1)    # CNOT: qubit 0 controls qubit 1
qc.measure([0, 1], [0, 1])

# Run on simulator
sim = AerSimulator()
job = sim.run(qc, shots=1024)
counts = job.result().get_counts()
print(counts)
`

const DEMO_OUTPUT = `{'00': 507, '11': 517}

Circuit depth  : 3
Total gates    : 3
Qubits used    : 2
Execution time : 0.42s
Backend        : ibmq_qasm_simulator`

export default function PracticeEditor() {
  const [theme, setTheme]       = useState('vs-dark')   // 'vs-dark' | 'light'
  const [code, setCode]         = useState(STARTER_CODE)
  const [output, setOutput]     = useState('')
  const [isRunning, setIsRunning] = useState(false)
  const [fontSize, setFontSize] = useState(14)
  const editorRef = useRef(null)

  const isDark = theme === 'vs-dark'

  function handleEditorMount(editor) {
    editorRef.current = editor
    // Configure Python-specific settings
    editor.updateOptions({
      fontFamily: 'SF Mono, ui-monospace, Menlo, Consolas, monospace',
      fontSize: fontSize,
      lineHeight: 22,
      padding: { top: 20, bottom: 20 },
      minimap: { enabled: false },
      scrollBeyondLastLine: false,
      renderLineHighlight: 'line',
      cursorStyle: 'line',
      cursorBlinking: 'smooth',
      smoothScrolling: true,
      contextmenu: false,
      folding: true,
      lineNumbers: 'on',
      wordWrap: 'on',
      tabSize: 4,
      insertSpaces: true,
      bracketPairColorization: { enabled: true },
    })
  }

  function handleRun() {
    setIsRunning(true)
    setOutput('')
    // Simulate execution delay — will be replaced by real API call Day 3
    setTimeout(() => {
      setOutput(DEMO_OUTPUT)
      setIsRunning(false)
    }, 1400)
  }

  function handleFontSize(delta) {
    const next = Math.min(Math.max(fontSize + delta, 11), 20)
    setFontSize(next)
    editorRef.current?.updateOptions({ fontSize: next })
  }

  return (
    <div style={{
      display: 'flex', flexDirection: 'column', height: '100%',
      background: isDark ? '#1A1A2E' : '#FFFFFF',
      fontFamily: FONT,
      transition: 'background 0.25s ease',
    }}>

      {/* ── Editor toolbar ── */}
      <div style={{
        display: 'flex', alignItems: 'center', gap: '8px',
        padding: '10px 16px',
        background: isDark ? '#13131F' : '#F7F7FA',
        borderBottom: `1px solid ${isDark ? 'rgba(255,255,255,0.07)' : 'rgba(0,0,0,0.08)'}`,
        flexShrink: 0,
      }}>
        {/* File name */}
        <div style={{ display:'flex', alignItems:'center', gap:'7px', marginRight:'auto' }}>
          <span style={{ fontSize:'13px', fontFamily: MONO, color: isDark ? '#CDD6F4' : '#1C1C1E', fontWeight:500 }}>
            circuit.py
          </span>
          <span style={{
            fontSize:'10px', fontWeight:600, letterSpacing:'0.06em', textTransform:'uppercase',
            padding:'2px 7px', borderRadius:'4px',
            background: isDark ? 'rgba(50,173,230,0.15)' : 'rgba(0,122,255,0.08)',
            color: isDark ? '#32ADE6' : '#007AFF',
          }}>
            Python
          </span>
        </div>

        {/* Font size controls */}
        <div style={{ display:'flex', alignItems:'center', gap:'4px' }}>
          <ToolbarBtn isDark={isDark} onClick={() => handleFontSize(-1)} title="Decrease font size">A−</ToolbarBtn>
          <span style={{ fontSize:'11px', color: isDark ? '#6C7086' : '#AEAEB2', minWidth:'20px', textAlign:'center', fontFamily: MONO }}>
            {fontSize}
          </span>
          <ToolbarBtn isDark={isDark} onClick={() => handleFontSize(1)} title="Increase font size">A+</ToolbarBtn>
        </div>

        {/* Divider */}
        <div style={{ width:'1px', height:'20px', background: isDark ? 'rgba(255,255,255,0.1)' : 'rgba(0,0,0,0.1)' }} />

        {/* Theme toggle */}
        <button
          onClick={() => setTheme(isDark ? 'light' : 'vs-dark')}
          title={isDark ? 'Switch to light theme' : 'Switch to dark theme'}
          style={{
            display: 'flex', alignItems: 'center', gap: '6px',
            padding: '5px 12px', borderRadius: '8px', border: 'none',
            background: isDark ? 'rgba(255,255,255,0.07)' : 'rgba(0,0,0,0.06)',
            color: isDark ? '#CDD6F4' : '#3C3C43',
            fontSize: '12px', fontWeight: 500, fontFamily: FONT,
            cursor: 'pointer', transition: 'all 0.15s',
          }}
          onMouseEnter={e => e.currentTarget.style.opacity = '0.75'}
          onMouseLeave={e => e.currentTarget.style.opacity = '1'}
        >
          {isDark ? '☀ Light' : '◑ Dark'}
        </button>

        {/* Run button */}
        <motion.button
          onClick={handleRun}
          disabled={isRunning}
          style={{
            display: 'flex', alignItems: 'center', gap: '7px',
            padding: '7px 18px', borderRadius: '9px', border: 'none',
            background: isRunning
              ? (isDark ? 'rgba(0,122,255,0.4)' : 'rgba(0,122,255,0.3)')
              : 'linear-gradient(135deg, #007AFF, #32ADE6)',
            color: '#FFFFFF',
            fontSize: '13px', fontWeight: 600, fontFamily: FONT,
            cursor: isRunning ? 'not-allowed' : 'pointer',
            boxShadow: isRunning ? 'none' : '0 2px 10px rgba(0,122,255,0.35)',
            transition: 'all 0.2s',
          }}
          whileHover={!isRunning ? { scale: 1.03 } : {}}
          whileTap={!isRunning ? { scale: 0.97 } : {}}
        >
          {isRunning ? (
            <>
              <RunSpinner /> Running…
            </>
          ) : (
            <>▶  Run</>
          )}
        </motion.button>
      </div>

      {/* ── Monaco Editor ── */}
      <div style={{ flex: 1, overflow: 'hidden', minHeight: 0 }}>
        <Editor
          height="100%"
          defaultLanguage="python"
          value={code}
          onChange={(val) => setCode(val ?? '')}
          theme={theme}
          onMount={handleEditorMount}
          loading={
            <div style={{
              display: 'flex', alignItems: 'center', justifyContent: 'center',
              height: '100%', color: '#AEAEB2', fontSize: '14px', fontFamily: FONT,
            }}>
              Loading editor…
            </div>
          }
          options={{
            fontFamily: MONO,
            fontSize: fontSize,
            lineHeight: 22,
            padding: { top: 20, bottom: 20 },
            minimap: { enabled: false },
            scrollBeyondLastLine: false,
            renderLineHighlight: 'line',
            cursorBlinking: 'smooth',
            smoothScrolling: true,
            folding: true,
            lineNumbers: 'on',
            wordWrap: 'on',
            tabSize: 4,
          }}
        />
      </div>

      {/* ── Output panel ── */}
      <AnimatePresence>
        {(output || isRunning) && (
          <motion.div
            key="output"
            style={{
              flexShrink: 0,
              borderTop: `1px solid ${isDark ? 'rgba(255,255,255,0.08)' : 'rgba(0,0,0,0.08)'}`,
              background: isDark ? '#13131F' : '#F9F9FB',
              maxHeight: '180px',
              overflow: 'hidden',
              display: 'flex', flexDirection: 'column',
            }}
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: 'auto', opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.28, ease: 'easeOut' }}
          >
            {/* Output header */}
            <div style={{
              display: 'flex', alignItems: 'center', justifyContent: 'space-between',
              padding: '8px 16px',
              borderBottom: `1px solid ${isDark ? 'rgba(255,255,255,0.06)' : 'rgba(0,0,0,0.06)'}`,
            }}>
              <span style={{
                fontSize: '11px', fontWeight: 600,
                letterSpacing: '0.08em', textTransform: 'uppercase',
                color: isRunning ? '#FF9500' : '#34C759',
              }}>
                {isRunning ? '● Running' : '● Output'}
              </span>
              {output && (
                <button
                  onClick={() => setOutput('')}
                  style={{
                    fontSize: '12px', color: isDark ? '#6C7086' : '#AEAEB2',
                    background: 'none', border: 'none', cursor: 'pointer', fontFamily: FONT,
                  }}
                >
                  Clear
                </button>
              )}
            </div>

            {/* Output content */}
            <div style={{ padding: '12px 16px', overflowY: 'auto', flex: 1 }}>
              {isRunning ? (
                <RunningState isDark={isDark} />
              ) : (
                <pre style={{
                  fontFamily: MONO, fontSize: '12px', lineHeight: '1.7',
                  color: isDark ? '#A6E3A1' : '#1C7A3A',
                  margin: 0, whiteSpace: 'pre-wrap',
                }}>
                  {output}
                </pre>
              )}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  )
}

/* ── Small reusable toolbar button ── */
function ToolbarBtn({ children, isDark, onClick, title }) {
  return (
    <button
      onClick={onClick}
      title={title}
      style={{
        padding: '4px 8px', borderRadius: '6px', border: 'none',
        background: isDark ? 'rgba(255,255,255,0.06)' : 'rgba(0,0,0,0.05)',
        color: isDark ? '#CDD6F4' : '#3C3C43',
        fontSize: '11px', fontWeight: 600, fontFamily: 'SF Mono, monospace',
        cursor: 'pointer', transition: 'opacity 0.15s',
      }}
      onMouseEnter={e => e.target.style.opacity = '0.65'}
      onMouseLeave={e => e.target.style.opacity = '1'}
    >
      {children}
    </button>
  )
}

/* ── Animated spinner for run state ── */
function RunSpinner() {
  return (
    <motion.div
      style={{
        width: '12px', height: '12px', borderRadius: '50%',
        border: '2px solid rgba(255,255,255,0.3)',
        borderTopColor: '#FFFFFF',
      }}
      animate={{ rotate: 360 }}
      transition={{ duration: 0.7, repeat: Infinity, ease: 'linear' }}
    />
  )
}

/* ── Running skeleton animation ── */
function RunningState({ isDark }) {
  const color = isDark ? 'rgba(255,255,255,0.08)' : 'rgba(0,0,0,0.06)'
  const lines = [60, 85, 45, 70]
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
      {lines.map((w, i) => (
        <motion.div
          key={i}
          style={{ height: '10px', borderRadius: '5px', background: color, width: `${w}%` }}
          animate={{ opacity: [0.4, 0.9, 0.4] }}
          transition={{ duration: 1.2, delay: i * 0.12, repeat: Infinity, ease: 'easeInOut' }}
        />
      ))}
    </div>
  )
}