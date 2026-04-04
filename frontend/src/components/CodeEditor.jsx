import { useState, useRef } from 'react'
import Editor from '@monaco-editor/react'
import { motion, AnimatePresence } from 'framer-motion'

const FONT    = '-apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif'
const MONO    = 'SF Mono, ui-monospace, Menlo, Consolas, monospace'
const BACKEND = 'http://localhost:8000'

const STARTER_CODE = `# QuantumMind — Practice Mode
# Write your Qiskit code and press Run ▶

from qiskit import QuantumCircuit
from qiskit_aer import AerSimulator

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

export default function CodeEditor() {
  const [theme, setTheme]         = useState('vs-dark')
  const [code, setCode]           = useState(STARTER_CODE)
  const [output, setOutput]       = useState(null)  // { success, output, error, circuit_image, execution_time }
  const [isRunning, setIsRunning] = useState(false)
  const [fontSize, setFontSize]   = useState(14)
  const editorRef = useRef(null)
  const isDark    = theme === 'vs-dark'

  function handleEditorMount(editor) {
    editorRef.current = editor
    editor.updateOptions({
      fontFamily: MONO,
      fontSize, lineHeight: 22,
      padding: { top: 20, bottom: 20 },
      minimap: { enabled: false },
      scrollBeyondLastLine: false,
      renderLineHighlight: 'line',
      cursorBlinking: 'smooth',
      smoothScrolling: true,
      wordWrap: 'on',
      tabSize: 4,
    })
  }

  async function handleRun() {
    const currentCode = editorRef.current?.getValue() ?? code
    if (!currentCode.trim() || isRunning) return

    setIsRunning(true)
    setOutput(null)

    try {
      const res = await fetch(`${BACKEND}/api/execute`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ code: currentCode, shots: 1024 }),
      })

      if (!res.ok) throw new Error(`HTTP ${res.status}`)
      const data = await res.json()
      setOutput(data)
    } catch (err) {
      setOutput({
        success: false,
        output: '',
        error: `Connection error: ${err.message}. Is the backend running?`,
        circuit_image: '',
        execution_time: 0,
      })
    } finally {
      setIsRunning(false)
    }
  }

  function handleFontSize(delta) {
    const next = Math.min(Math.max(fontSize + delta, 11), 20)
    setFontSize(next)
    editorRef.current?.updateOptions({ fontSize: next })
  }

  return (
    <div style={{ display:'flex', flexDirection:'column', height:'100%', background: isDark ? '#1A1A2E' : '#FFFFFF', fontFamily:FONT, transition:'background 0.25s' }}>

      {/* Toolbar */}
      <div style={{ display:'flex', alignItems:'center', gap:'8px', padding:'10px 16px', background: isDark ? '#13131F' : '#F7F7FA', borderBottom:`1px solid ${isDark ? 'rgba(255,255,255,0.07)' : 'rgba(0,0,0,0.08)'}`, flexShrink:0 }}>

        {/* File name */}
        <div style={{ display:'flex', alignItems:'center', gap:'7px', marginRight:'auto' }}>
          <span style={{ fontSize:'13px', fontFamily:MONO, color: isDark ? '#CDD6F4' : '#1C1C1E', fontWeight:500 }}>circuit.py</span>
          <span style={{ fontSize:'10px', fontWeight:600, letterSpacing:'0.06em', textTransform:'uppercase', padding:'2px 7px', borderRadius:'4px', background: isDark ? 'rgba(50,173,230,0.15)' : 'rgba(0,122,255,0.08)', color: isDark ? '#32ADE6' : '#007AFF' }}>Python</span>
        </div>

        {/* Font size */}
        <div style={{ display:'flex', alignItems:'center', gap:'4px' }}>
          <ToolbarBtn isDark={isDark} onClick={() => handleFontSize(-1)}>A−</ToolbarBtn>
          <span style={{ fontSize:'11px', color: isDark ? '#6C7086' : '#AEAEB2', minWidth:'20px', textAlign:'center', fontFamily:MONO }}>{fontSize}</span>
          <ToolbarBtn isDark={isDark} onClick={() => handleFontSize(1)}>A+</ToolbarBtn>
        </div>

        <div style={{ width:'1px', height:'20px', background: isDark ? 'rgba(255,255,255,0.1)' : 'rgba(0,0,0,0.1)' }} />

        {/* Theme toggle */}
        <button
          onClick={() => setTheme(isDark ? 'light' : 'vs-dark')}
          style={{ display:'flex', alignItems:'center', gap:'6px', padding:'5px 12px', borderRadius:'8px', border:'none', background: isDark ? 'rgba(255,255,255,0.07)' : 'rgba(0,0,0,0.06)', color: isDark ? '#CDD6F4' : '#3C3C43', fontSize:'12px', fontWeight:500, fontFamily:FONT, cursor:'pointer' }}
        >
          {isDark ? '☀ Light' : '◑ Dark'}
        </button>

        {/* Run button */}
        <motion.button
          onClick={handleRun}
          disabled={isRunning}
          style={{ display:'flex', alignItems:'center', gap:'7px', padding:'7px 18px', borderRadius:'9px', border:'none', background: isRunning ? 'rgba(0,122,255,0.4)' : 'linear-gradient(135deg, #007AFF, #32ADE6)', color:'#FFFFFF', fontSize:'13px', fontWeight:600, fontFamily:FONT, cursor: isRunning ? 'not-allowed' : 'pointer', boxShadow: isRunning ? 'none' : '0 2px 10px rgba(0,122,255,0.35)' }}
          whileHover={!isRunning ? { scale:1.03 } : {}}
          whileTap={!isRunning ? { scale:0.97 } : {}}
        >
          {isRunning ? <><Spinner /> Running…</> : <>▶  Run</>}
        </motion.button>
      </div>

      {/* Monaco Editor */}
      <div style={{ flex:1, overflow:'hidden', minHeight:0 }}>
        <Editor
          height="100%"
          defaultLanguage="python"
          value={code}
          onChange={val => setCode(val ?? '')}
          theme={theme}
          onMount={handleEditorMount}
          loading={<div style={{ display:'flex', alignItems:'center', justifyContent:'center', height:'100%', color:'#AEAEB2', fontSize:'14px', fontFamily:FONT }}>Loading editor…</div>}
          options={{ fontFamily:MONO, fontSize, lineHeight:22, padding:{ top:20, bottom:20 }, minimap:{ enabled:false }, scrollBeyondLastLine:false, wordWrap:'on', tabSize:4 }}
        />
      </div>

      {/* Output panel */}
      <AnimatePresence>
        {output && (
          <motion.div
            key="output"
            style={{ flexShrink:0, borderTop:`1px solid ${isDark ? 'rgba(255,255,255,0.08)' : 'rgba(0,0,0,0.08)'}`, background: isDark ? '#13131F' : '#F9F9FB', maxHeight:'320px', overflow:'hidden', display:'flex', flexDirection:'column' }}
            initial={{ height:0, opacity:0 }}
            animate={{ height:'auto', opacity:1 }}
            exit={{ height:0, opacity:0 }}
            transition={{ duration:0.28 }}
          >
            {/* Output header */}
            <div style={{ display:'flex', alignItems:'center', justifyContent:'space-between', padding:'8px 16px', borderBottom:`1px solid ${isDark ? 'rgba(255,255,255,0.06)' : 'rgba(0,0,0,0.06)'}` }}>
              <div style={{ display:'flex', alignItems:'center', gap:'8px' }}>
                <span style={{ fontSize:'11px', fontWeight:600, letterSpacing:'0.08em', textTransform:'uppercase', color: output.success ? '#34C759' : '#FF3B30' }}>
                  {output.success ? '● Output' : '● Error'}
                </span>
                {output.success && (
                  <span style={{ fontSize:'11px', color: isDark ? '#6C7086' : '#AEAEB2' }}>
                    {output.execution_time}s
                  </span>
                )}
              </div>
              <button onClick={() => setOutput(null)} style={{ fontSize:'12px', color: isDark ? '#6C7086' : '#AEAEB2', background:'none', border:'none', cursor:'pointer', fontFamily:FONT }}>
                Clear
              </button>
            </div>

            {/* Output content */}
            <div style={{ display:'flex', overflow:'hidden', flex:1 }}>
              {/* Text output */}
              <div style={{ flex:1, padding:'12px 16px', overflowY:'auto' }}>
                {output.success ? (
                  <pre style={{ fontFamily:MONO, fontSize:'13px', lineHeight:'1.7', color: isDark ? '#A6E3A1' : '#1C7A3A', margin:0, whiteSpace:'pre-wrap' }}>
                    {output.output || '(no output)'}
                  </pre>
                ) : (
                  <pre style={{ fontFamily:MONO, fontSize:'12px', lineHeight:'1.7', color:'#FF3B30', margin:0, whiteSpace:'pre-wrap' }}>
                    {output.error}
                  </pre>
                )}
              </div>

              {/* Circuit diagram */}
              {output.circuit_image && (
                <div style={{ borderLeft:`1px solid ${isDark ? 'rgba(255,255,255,0.08)' : 'rgba(0,0,0,0.08)'}`, padding:'12px', display:'flex', alignItems:'center', justifyContent:'center', background: isDark ? '#0D0D1A' : '#FFFFFF', minWidth:'200px', maxWidth:'400px' }}>
                  <div>
                    <p style={{ fontSize:'10px', fontWeight:600, letterSpacing:'0.08em', textTransform:'uppercase', color: isDark ? '#6C7086' : '#AEAEB2', marginBottom:'8px', textAlign:'center' }}>Circuit</p>
                    <img
                      src={`data:image/png;base64,${output.circuit_image}`}
                      alt="Circuit diagram"
                      style={{ maxWidth:'100%', maxHeight:'220px', objectFit:'contain', borderRadius:'8px' }}
                    />
                  </div>
                </div>
              )}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  )
}

function ToolbarBtn({ children, isDark, onClick }) {
  return (
    <button onClick={onClick} style={{ padding:'4px 8px', borderRadius:'6px', border:'none', background: isDark ? 'rgba(255,255,255,0.06)' : 'rgba(0,0,0,0.05)', color: isDark ? '#CDD6F4' : '#3C3C43', fontSize:'11px', fontWeight:600, fontFamily:MONO, cursor:'pointer' }}>
      {children}
    </button>
  )
}

function Spinner() {
  return (
    <motion.div
      style={{ width:'12px', height:'12px', borderRadius:'50%', border:'2px solid rgba(255,255,255,0.3)', borderTopColor:'#FFFFFF' }}
      animate={{ rotate:360 }}
      transition={{ duration:0.7, repeat:Infinity, ease:'linear' }}
    />
  )
}