import { useState, useRef, useEffect } from 'react'
import { motion, AnimatePresence } from 'framer-motion'

const FONT    = '-apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif'
const BACKEND = 'http://localhost:8000'

const SUGGESTIONS = [
  'Explain what this circuit does',
  'How do I add more qubits?',
  'What is a CNOT gate?',
  "Show me Grover's algorithm",
]

function getThreadId() {
  let id = localStorage.getItem('qm_thread_id')
  if (!id) { id = 'thread_' + Date.now() + '_' + Math.random().toString(36).slice(2); localStorage.setItem('qm_thread_id', id) }
  return id
}

export default function PracticeAssistant() {
  // PracticeAssistant has its OWN local message state
  // completely separate from the main ChatPanel Zustand state
  const [messages, setMessages]      = useState([])
  const [isStreaming, setIsStreaming] = useState(false)
  const [input, setInput]            = useState('')
  const bottomRef  = useRef(null)
  const inputRef   = useRef(null)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, isStreaming])

  async function handleSend(text) {
    const msg = (text ?? input).trim()
    if (!msg || isStreaming) return

    setInput('')

    const userMsg = { id: Date.now().toString(), role: 'user', content: msg }
    const aiId    = (Date.now() + 1).toString()
    setMessages(prev => [...prev, userMsg, { id: aiId, role: 'ai', content: '' }])
    setIsStreaming(true)
    let aiResponse = ''

    try {
      const res = await fetch(`${BACKEND}/api/stream`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          message: msg,
          mode: 'practice',
          chat_history: [],
          thread_id: `${getThreadId()}_practice`,
        }),
      })

      if (!res.ok) throw new Error(`HTTP ${res.status}`)

      const reader  = res.body.getReader()
      const decoder = new TextDecoder()

      while (true) {
        const { done, value } = await reader.read()
        if (done) break
        for (const line of decoder.decode(value, { stream: true }).split('\n')) {
          if (!line.startsWith('data: ')) continue
          try {
            const event = JSON.parse(line.slice(6))
            if (event.type === 'token') {
              aiResponse += event.content
              setMessages(prev => prev.map(m => m.id === aiId ? { ...m, content: aiResponse } : m))
            }
          } catch (_) { continue }
        }
      }
    } catch (err) {
      setMessages(prev => prev.map(m =>
        m.id === aiId ? { ...m, content: 'Connection error. Is the backend running?' } : m
      ))
    } finally {
      setIsStreaming(false)
    }
  }

  return (
    <div style={{ width:'300px', minWidth:'300px', display:'flex', flexDirection:'column', height:'100%', overflow:'hidden', background:'#FFFFFF', borderLeft:'1px solid rgba(0,0,0,0.07)', fontFamily:FONT }}>

      {/* Header */}
      <div style={{ padding:'14px 16px 12px', borderBottom:'1px solid rgba(0,0,0,0.07)', background:'#F7F7FA', flexShrink:0 }}>
        <div style={{ display:'flex', alignItems:'center', gap:'8px' }}>
          <div style={{ width:'28px', height:'28px', borderRadius:'8px', background:'linear-gradient(135deg, #007AFF, #32ADE6)', display:'flex', alignItems:'center', justifyContent:'center', fontSize:'14px', flexShrink:0 }}>
            ✦
          </div>
          <div>
            <div style={{ fontSize:'13px', fontWeight:600, color:'#1C1C1E' }}>AI Assistant</div>
            <div style={{ fontSize:'11px', color:'#AEAEB2' }}>Ask about your code</div>
          </div>
        </div>
      </div>

      {/* Messages */}
      <div style={{ flex:1, overflowY:'auto', padding:'14px', display:'flex', flexDirection:'column', gap:'12px', scrollbarWidth:'thin', scrollbarColor:'rgba(0,0,0,0.1) transparent' }}>

        {/* Empty state with suggestions */}
        {messages.length === 0 && (
          <motion.div initial={{ opacity:0 }} animate={{ opacity:1 }} transition={{ delay:0.2 }}>
            <p style={{ fontSize:'12px', color:'#AEAEB2', marginBottom:'10px', lineHeight:1.5 }}>
              Write some code and ask me to explain it, debug it, or improve it.
            </p>
            {SUGGESTIONS.map((s, i) => (
              <motion.button
                key={s}
                onClick={() => handleSend(s)}
                style={{ width:'100%', padding:'9px 12px', borderRadius:'10px', border:'1px solid rgba(0,0,0,0.08)', background:'#FFFFFF', color:'#3C3C43', fontSize:'12px', fontFamily:FONT, textAlign:'left', cursor:'pointer', marginBottom:'6px', boxShadow:'0 1px 3px rgba(0,0,0,0.05)', display:'block' }}
                initial={{ opacity:0, y:6 }}
                animate={{ opacity:1, y:0 }}
                transition={{ delay:0.1 + i * 0.06 }}
                whileHover={{ y:-2, boxShadow:'0 4px 12px rgba(0,0,0,0.08)', borderColor:'rgba(0,122,255,0.25)' }}
              >
                <span style={{ color:'#007AFF', marginRight:'8px' }}>→</span>{s}
              </motion.button>
            ))}
          </motion.div>
        )}

        {/* Messages */}
        <AnimatePresence initial={false}>
          {messages.map(msg => (
            <motion.div
              key={msg.id}
              style={{ display:'flex', flexDirection:'column', gap:'4px', alignItems: msg.role === 'ai' ? 'flex-start' : 'flex-end' }}
              initial={{ opacity:0, y:6 }}
              animate={{ opacity:1, y:0 }}
              transition={{ duration:0.22 }}
            >
              <span style={{ fontSize:'10px', fontWeight:600, letterSpacing:'0.07em', textTransform:'uppercase', color: msg.role === 'ai' ? '#007AFF' : '#AEAEB2' }}>
                {msg.role === 'ai' ? 'AI' : 'You'}
              </span>
              <div style={{
                maxWidth:'92%', padding:'10px 13px', fontSize:'13px', lineHeight:'1.6', fontFamily:FONT,
                color: msg.role === 'ai' ? '#1C1C1E' : '#FFFFFF',
                background: msg.role === 'ai' ? '#F2F2F7' : 'linear-gradient(135deg, #007AFF, #1A8FFF)',
                borderRadius: msg.role === 'ai' ? '3px 14px 14px 14px' : '14px 3px 14px 14px',
                boxShadow: msg.role === 'ai' ? '0 1px 3px rgba(0,0,0,0.05)' : '0 3px 10px rgba(0,122,255,0.25)',
              }}>
                {msg.content || <motion.span animate={{ opacity:[0.4,1,0.4] }} transition={{ duration:1.2, repeat:Infinity }}>●●●</motion.span>}
              </div>
            </motion.div>
          ))}
        </AnimatePresence>

        <div ref={bottomRef} />
      </div>

      {/* Input */}
      <div style={{ padding:'10px 12px 14px', borderTop:'1px solid rgba(0,0,0,0.07)', background:'#F7F7FA', flexShrink:0 }}>
        <div style={{ display:'flex', alignItems:'flex-end', gap:'8px', background:'#FFFFFF', borderRadius:'12px', padding:'8px 8px 8px 14px', boxShadow:'0 1px 4px rgba(0,0,0,0.07), 0 0 0 1px rgba(0,0,0,0.07)' }}>
          <textarea
            ref={inputRef}
            rows={1}
            value={input}
            onChange={e => setInput(e.target.value)}
            placeholder="Ask about your code…"
            onKeyDown={e => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); handleSend() } }}
            onInput={e => { e.target.style.height = 'auto'; e.target.style.height = Math.min(e.target.scrollHeight, 100) + 'px' }}
            disabled={isStreaming}
            style={{ flex:1, resize:'none', border:'none', outline:'none', background:'transparent', fontSize:'13px', fontFamily:FONT, lineHeight:'1.5', color:'#1C1C1E', minHeight:'22px', maxHeight:'100px', overflow:'hidden', disabled: isStreaming }}
          />
          <motion.button
            onClick={() => handleSend()}
            disabled={!input.trim() || isStreaming}
            style={{ width:'32px', height:'32px', borderRadius:'50%', border:'none', background: input.trim() ? 'linear-gradient(135deg, #007AFF, #32ADE6)' : 'rgba(0,0,0,0.08)', color: input.trim() ? '#fff' : '#AEAEB2', fontSize:'15px', cursor: input.trim() ? 'pointer' : 'default', display:'flex', alignItems:'center', justifyContent:'center', flexShrink:0, transition:'all 0.18s' }}
            whileHover={input.trim() ? { scale:1.08 } : {}}
            whileTap={input.trim() ? { scale:0.92 } : {}}
          >↑</motion.button>
        </div>
      </div>
    </div>
  )
}