import { useEffect, useRef, useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import useAppState from '@/hooks/useAppState'

const FONT = '-apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif'
const MONO = 'SF Mono, ui-monospace, Menlo, Consolas, monospace'
const BACKEND_URL = 'http://localhost:8000'

// Generate a unique thread_id per browser session.
// localStorage persists across page refreshes but not across browsers.
// This means each device gets its own conversation history.
function getThreadId() {
  let id = localStorage.getItem('qm_thread_id')
  if (!id) {
    id = 'thread_' + Date.now() + '_' + Math.random().toString(36).slice(2)
    localStorage.setItem('qm_thread_id', id)
  }
  return id
}

const SUGGESTIONS = {
  theory:   ['What is quantum superposition?', 'Explain entanglement in simple terms', 'How does a quantum gate work?', 'What makes quantum computers faster?'],
  guided:   ['Start the Quantum Basics lesson', 'Explain superposition with an example', 'Show me the Hadamard gate in Qiskit', 'What is a Bell State?'],
  practice: ['Explain the Bell State circuit', 'How do I add more qubits?', 'What does qc.measure() do?', "Show me Grover's algorithm"],
}

const MODE_LABELS = {
  theory:   { label: 'Theory Mode',   color: '#007AFF' },
  guided:   { label: 'Guided Mode',   color: '#5856D6' },
  practice: { label: 'Practice Mode', color: '#32ADE6' },
}

export default function ChatPanel() {
  const messages       = useAppState(s => s.messages)
  const isStreaming    = useAppState(s => s.isStreaming)
  const addMessage     = useAppState(s => s.addMessage)
  const setIsStreaming = useAppState(s => s.setIsStreaming)
  const mode           = useAppState(s => s.mode) ?? 'guided'

  const bottomRef   = useRef(null)
  const textareaRef = useRef(null)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, isStreaming])

  async function handleSend(text) {
    const msg = (text ?? textareaRef.current?.value ?? '').trim()
    if (!msg || isStreaming) return

    addMessage({ role: 'user', content: msg })

    if (!text && textareaRef.current) {
      textareaRef.current.value = ''
      textareaRef.current.style.height = 'auto'
    }

    const history = messages.map(m => ({ role: m.role, content: m.content }))

    setIsStreaming(true)
    let aiResponse = ''
    const streamId = Date.now().toString()
    addMessage({ id: streamId, role: 'ai', content: '' })

    try {
      const response = await fetch(`${BACKEND_URL}/api/stream`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: msg, mode, chat_history: history, thread_id: getThreadId() }),
      })

      if (!response.ok) throw new Error(`HTTP ${response.status}`)

      const reader  = response.body.getReader()
      const decoder = new TextDecoder()

      while (true) {
        const { done, value } = await reader.read()
        if (done) break

        const text = decoder.decode(value, { stream: true })
        const lines = text.split('\n')

        for (const line of lines) {
          if (!line.startsWith('data: ')) continue
          try {
            const event = JSON.parse(line.slice(6))
            if (event.type === 'token') {
              aiResponse += event.content
              const current = useAppState.getState().messages
              useAppState.setState({
                messages: current.map(m =>
                  m.id === streamId ? { ...m, content: aiResponse } : m
                )
              })
            }
            if (event.type === 'error') throw new Error(event.content)
          } catch (_) { continue }
        }
      }
    } catch (error) {
      console.error('Stream error:', error)
      const current = useAppState.getState().messages
      useAppState.setState({
        messages: current.map(m =>
          m.id === streamId ? { ...m, content: 'Something went wrong. Please try again.' } : m
        )
      })
    } finally {
      setIsStreaming(false)
    }
  }

  function handleKeyDown(e) {
    if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); handleSend() }
  }

  function handleInput(e) {
    e.target.style.height = 'auto'
    e.target.style.height = Math.min(e.target.scrollHeight, 140) + 'px'
  }

  function handleSuggest(text) {
    if (textareaRef.current) {
      textareaRef.current.value = text
      textareaRef.current.focus()
      textareaRef.current.style.height = 'auto'
      textareaRef.current.style.height = textareaRef.current.scrollHeight + 'px'
    }
  }

  const isEmpty = messages.length === 0

  return (
    <div style={{ display:'flex', flexDirection:'column', height:'100%', overflow:'hidden', fontFamily: FONT }}>
      <div style={{ flex:1, overflowY:'auto', padding:'28px 32px', display:'flex', flexDirection:'column', gap:'24px', scrollbarWidth:'thin', scrollbarColor:'rgba(0,0,0,0.1) transparent' }}>
        <AnimatePresence>
          {isEmpty && !isStreaming && <EmptyState mode={mode} onSuggest={handleSuggest} />}
        </AnimatePresence>
        <AnimatePresence initial={false}>
          {messages.map(msg => <Message key={msg.id} msg={msg} />)}
        </AnimatePresence>
        {isStreaming && messages.length === 0 && <StreamingIndicator />}
        <div ref={bottomRef} />
      </div>

      <div style={{ padding:'14px 20px 18px', borderTop:'1px solid rgba(0,0,0,0.07)', background:'rgba(247,247,250,0.9)', backdropFilter:'blur(12px)', WebkitBackdropFilter:'blur(12px)', display:'flex', alignItems:'flex-end', gap:'10px' }}>
        <textarea
          ref={textareaRef}
          rows={1}
          placeholder="Ask anything about quantum computing…"
          onKeyDown={handleKeyDown}
          onInput={handleInput}
          disabled={isStreaming}
          style={{ flex:1, resize:'none', border:'none', outline:'none', background:'#FFFFFF', borderRadius:'14px', padding:'12px 16px', fontSize:'15px', fontFamily:FONT, lineHeight:'1.5', color:'#1C1C1E', minHeight:'44px', maxHeight:'140px', overflow:'hidden', boxShadow:'0 1px 6px rgba(0,0,0,0.08), 0 0 0 1px rgba(0,0,0,0.07)', transition:'box-shadow 0.2s' }}
          onFocus={e => { e.target.style.boxShadow = '0 1px 6px rgba(0,0,0,0.08), 0 0 0 2px rgba(0,122,255,0.35)' }}
          onBlur={e  => { e.target.style.boxShadow = '0 1px 6px rgba(0,0,0,0.08), 0 0 0 1px rgba(0,0,0,0.07)' }}
        />
        <motion.button
          onClick={() => handleSend()}
          disabled={isStreaming}
          style={{ width:'44px', height:'44px', borderRadius:'50%', border:'none', background:'linear-gradient(135deg, #007AFF, #32ADE6)', color:'#fff', fontSize:'18px', cursor:'pointer', flexShrink:0, display:'flex', alignItems:'center', justifyContent:'center', boxShadow:'0 2px 10px rgba(0,122,255,0.35)', opacity: isStreaming ? 0.5 : 1 }}
          whileHover={!isStreaming ? { scale: 1.06 } : {}}
          whileTap={!isStreaming ? { scale: 0.94 } : {}}
        >
          ↑
        </motion.button>
      </div>
    </div>
  )
}

function EmptyState({ mode, onSuggest }) {
  const meta = MODE_LABELS[mode] ?? MODE_LABELS.guided
  const suggestions = SUGGESTIONS[mode] ?? SUGGESTIONS.guided
  return (
    <motion.div
      style={{ display:'flex', flexDirection:'column', alignItems:'center', justifyContent:'center', flex:1, padding:'40px 24px', textAlign:'center', minHeight:'400px' }}
      initial={{ opacity:0, y:16 }} animate={{ opacity:1, y:0 }} exit={{ opacity:0, y:-8 }}
      transition={{ duration:0.4, ease:[0.16,1,0.3,1] }}
    >
      <div style={{ width:'64px', height:'64px', borderRadius:'20px', background:`linear-gradient(135deg, ${meta.color}18, ${meta.color}30)`, border:`1px solid ${meta.color}22`, display:'flex', alignItems:'center', justifyContent:'center', fontSize:'28px', marginBottom:'20px', boxShadow:`0 4px 20px ${meta.color}15` }}>⚛</div>
      <h2 style={{ fontSize:'22px', fontWeight:700, color:'#1C1C1E', letterSpacing:'-0.3px', marginBottom:'8px', fontFamily:FONT }}>Hello, Asfand 👋</h2>
      <p style={{ fontSize:'15px', color:'#6C6C70', lineHeight:1.6, maxWidth:'380px', marginBottom:'10px', fontFamily:FONT }}>
        You are in <span style={{ color:meta.color, fontWeight:600 }}>{meta.label}</span>. Ask me anything or pick a question below.
      </p>
      <div style={{ width:'40px', height:'2px', borderRadius:'2px', background:`linear-gradient(90deg, ${meta.color}, ${meta.color}44)`, margin:'20px auto 28px' }} />
      <div style={{ display:'grid', gridTemplateColumns:'1fr 1fr', gap:'10px', width:'100%', maxWidth:'540px' }}>
        {suggestions.map((s, i) => (
          <motion.button key={s} onClick={() => onSuggest(s)}
            style={{ padding:'13px 16px', borderRadius:'12px', border:'1px solid rgba(0,0,0,0.08)', background:'#FFFFFF', color:'#3C3C43', fontSize:'13px', fontFamily:FONT, textAlign:'left', cursor:'pointer', lineHeight:1.45, boxShadow:'0 1px 4px rgba(0,0,0,0.05)' }}
            initial={{ opacity:0, y:10 }} animate={{ opacity:1, y:0 }} transition={{ delay:0.15 + i * 0.07 }}
            whileHover={{ y:-3, boxShadow:'0 6px 20px rgba(0,0,0,0.09)', borderColor:`${meta.color}44` }}
            whileTap={{ scale:0.97 }}
          >
            <span style={{ color:meta.color, marginRight:'8px', fontSize:'14px' }}>→</span>{s}
          </motion.button>
        ))}
      </div>
    </motion.div>
  )
}

function StreamingIndicator() {
  return (
    <motion.div style={{ display:'flex', flexDirection:'column', gap:'6px', alignItems:'flex-start' }} initial={{ opacity:0, y:8 }} animate={{ opacity:1, y:0 }}>
      <span style={{ fontSize:'11px', fontWeight:600, letterSpacing:'0.07em', textTransform:'uppercase', color:'#007AFF' }}>QuantumMind AI</span>
      <div style={{ display:'flex', gap:'5px', padding:'13px 17px', borderRadius:'4px 18px 18px 18px', background:'#F2F2F7' }}>
        {[0, 0.16, 0.32].map((d, i) => (
          <motion.span key={i} style={{ width:'7px', height:'7px', borderRadius:'50%', background:'#007AFF', display:'block' }}
            animate={{ y:[0,-5,0], opacity:[0.3,1,0.3] }} transition={{ duration:1.0, delay:d, repeat:Infinity }} />
        ))}
      </div>
    </motion.div>
  )
}

function Message({ msg }) {
  const isAI = msg.role === 'ai'
  return (
    <motion.div
      style={{ display:'flex', flexDirection:'column', gap:'6px', alignItems: isAI ? 'flex-start' : 'flex-end' }}
      initial={{ opacity:0, y:10 }} animate={{ opacity:1, y:0 }} exit={{ opacity:0 }} transition={{ duration:0.25 }}
    >
      <span style={{ fontSize:'11px', fontWeight:600, letterSpacing:'0.07em', textTransform:'uppercase', color: isAI ? '#007AFF' : '#AEAEB2' }}>
        {isAI ? 'QuantumMind AI' : 'You'}
      </span>
      <div style={{ maxWidth:'78%', padding:'13px 17px', fontSize:'15px', lineHeight:'1.65', fontFamily:FONT, color: isAI ? '#1C1C1E' : '#FFFFFF', background: isAI ? '#F2F2F7' : 'linear-gradient(135deg, #007AFF, #1A8FFF)', borderRadius: isAI ? '4px 18px 18px 18px' : '18px 4px 18px 18px', boxShadow: isAI ? '0 1px 3px rgba(0,0,0,0.06)' : '0 3px 12px rgba(0,122,255,0.28)' }}>
        {msg.content || <span style={{ opacity:0.4 }}>…</span>}
      </div>
      {msg.codeBlock && <CodeBlock code={msg.codeBlock} />}
    </motion.div>
  )
}

function CodeBlock({ code }) {
  const [copied, setCopied] = useState(false)
  function copy() { navigator.clipboard.writeText(code); setCopied(true); setTimeout(() => setCopied(false), 1800) }
  return (
    <div style={{ maxWidth:'90%', position:'relative' }}>
      <pre style={{ background:'#1A1A2E', color:'#CDD6F4', fontFamily:MONO, fontSize:'13px', lineHeight:'1.75', padding:'16px 20px', borderRadius:'12px', overflowX:'auto', margin:'4px 0 0', boxShadow:'0 3px 12px rgba(0,0,0,0.14)' }}>
        {code}
      </pre>
      <button onClick={copy} style={{ position:'absolute', top:'10px', right:'12px', fontSize:'11px', fontWeight:500, fontFamily:FONT, color: copied ? '#34C759' : 'rgba(255,255,255,0.45)', background: copied ? 'rgba(52,199,89,0.15)' : 'rgba(255,255,255,0.07)', border:'none', borderRadius:'6px', padding:'3px 9px', cursor:'pointer' }}>
        {copied ? '✓ Copied' : 'Copy'}
      </button>
    </div>
  )
}