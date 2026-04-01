import { useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import useAppState from '@/hooks/useAppState'

const FONT = '-apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif'

// Starter suggestions shown before any chat
const SUGGESTIONS = [
  'Explain what this circuit does',
  'How do I add more qubits?',
  'What is a CNOT gate?',
  'Show me Grover\'s algorithm',
]

export default function PracticeAssistant() {
  const messages    = useAppState(s => s.messages)
  const isStreaming = useAppState(s => s.isStreaming)
  const addMessage  = useAppState(s => s.addMessage)
  const [input, setInput] = useState('')

  function handleSend(text) {
    const msg = (text ?? input).trim()
    if (!msg || isStreaming) return
    addMessage({ role: 'user', content: msg })
    setInput('')
    // TODO Day 3: wire to streaming API
  }

  return (
    <div style={{
      width: '300px', minWidth: '300px',
      display: 'flex', flexDirection: 'column',
      height: '100%', overflow: 'hidden',
      background: '#FFFFFF',
      borderLeft: '1px solid rgba(0,0,0,0.07)',
      fontFamily: FONT,
    }}>

      {/* Header */}
      <div style={{
        padding: '14px 16px 12px',
        borderBottom: '1px solid rgba(0,0,0,0.07)',
        background: '#F7F7FA', flexShrink: 0,
      }}>
        <div style={{ display:'flex', alignItems:'center', gap:'8px' }}>
          <div style={{
            width: '28px', height: '28px', borderRadius: '8px',
            background: 'linear-gradient(135deg, #007AFF, #32ADE6)',
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            fontSize: '14px', flexShrink: 0,
          }}>
            ✦
          </div>
          <div>
            <div style={{ fontSize: '13px', fontWeight: 600, color: '#1C1C1E' }}>AI Assistant</div>
            <div style={{ fontSize: '11px', color: '#AEAEB2' }}>Ask about your code</div>
          </div>
        </div>
      </div>

      {/* Messages or suggestions */}
      <div style={{
        flex: 1, overflowY: 'auto', padding: '16px',
        display: 'flex', flexDirection: 'column', gap: '14px',
        scrollbarWidth: 'thin', scrollbarColor: 'rgba(0,0,0,0.1) transparent',
      }}>
        {messages.length === 0 ? (
          <EmptyState onSuggest={handleSend} />
        ) : (
          <AnimatePresence initial={false}>
            {messages.map(msg => (
              <AssistantMessage key={msg.id} msg={msg} />
            ))}
          </AnimatePresence>
        )}

        {isStreaming && <TypingDots />}
      </div>

      {/* Input */}
      <div style={{
        padding: '10px 12px 14px',
        borderTop: '1px solid rgba(0,0,0,0.07)',
        background: '#F7F7FA', flexShrink: 0,
      }}>
        <div style={{
          display: 'flex', alignItems: 'flex-end', gap: '8px',
          background: '#FFFFFF', borderRadius: '12px',
          padding: '8px 8px 8px 14px',
          boxShadow: '0 1px 4px rgba(0,0,0,0.07), 0 0 0 1px rgba(0,0,0,0.07)',
        }}>
          <textarea
            rows={1}
            value={input}
            onChange={e => setInput(e.target.value)}
            placeholder="Ask about your code…"
            onKeyDown={e => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); handleSend() } }}
            onInput={e => { e.target.style.height = 'auto'; e.target.style.height = Math.min(e.target.scrollHeight, 100) + 'px' }}
            style={{
              flex: 1, resize: 'none', border: 'none', outline: 'none',
              background: 'transparent',
              fontSize: '13px', fontFamily: FONT, lineHeight: '1.5',
              color: '#1C1C1E', minHeight: '22px', maxHeight: '100px',
              overflow: 'hidden',
            }}
          />
          <motion.button
            onClick={() => handleSend()}
            disabled={!input.trim() || isStreaming}
            style={{
              width: '32px', height: '32px', borderRadius: '50%', border: 'none',
              background: input.trim()
                ? 'linear-gradient(135deg, #007AFF, #32ADE6)'
                : 'rgba(0,0,0,0.08)',
              color: input.trim() ? '#fff' : '#AEAEB2',
              fontSize: '15px', cursor: input.trim() ? 'pointer' : 'default',
              display: 'flex', alignItems: 'center', justifyContent: 'center',
              flexShrink: 0, transition: 'all 0.18s',
            }}
            whileHover={input.trim() ? { scale: 1.08 } : {}}
            whileTap={input.trim() ? { scale: 0.92 } : {}}
          >
            ↑
          </motion.button>
        </div>
      </div>
    </div>
  )
}

/* ── Empty state with quick suggestions ── */
function EmptyState({ onSuggest }) {
  return (
    <motion.div
      style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      transition={{ delay: 0.2 }}
    >
      <p style={{ fontSize: '13px', color: '#AEAEB2', marginBottom: '6px', lineHeight: 1.5 }}>
        Write some code and ask me to explain it, debug it, or improve it.
      </p>
      {SUGGESTIONS.map((s, i) => (
        <motion.button
          key={s}
          onClick={() => onSuggest(s)}
          style={{
            padding: '10px 14px', borderRadius: '10px', border: '1px solid rgba(0,0,0,0.08)',
            background: '#FFFFFF', color: '#3C3C43',
            fontSize: '13px', fontFamily: FONT, textAlign: 'left',
            cursor: 'pointer', transition: 'all 0.15s',
            boxShadow: '0 1px 3px rgba(0,0,0,0.05)',
          }}
          initial={{ opacity: 0, y: 8 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.1 + i * 0.06 }}
          whileHover={{ y: -2, boxShadow: '0 4px 12px rgba(0,0,0,0.08)', borderColor: 'rgba(0,122,255,0.25)' }}
        >
          <span style={{ color: '#007AFF', marginRight: '8px' }}>→</span>
          {s}
        </motion.button>
      ))}
    </motion.div>
  )
}

/* ── Individual message ── */
function AssistantMessage({ msg }) {
  const isAI = msg.role === 'ai'
  return (
    <motion.div
      style={{ display: 'flex', flexDirection: 'column', gap: '4px', alignItems: isAI ? 'flex-start' : 'flex-end' }}
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.22 }}
    >
      <span style={{ fontSize: '10px', fontWeight: 600, letterSpacing: '0.07em', textTransform: 'uppercase', color: isAI ? '#007AFF' : '#AEAEB2' }}>
        {isAI ? 'AI' : 'You'}
      </span>
      <div style={{
        maxWidth: '92%', padding: '10px 13px',
        fontSize: '13px', lineHeight: '1.6', fontFamily: FONT,
        color: isAI ? '#1C1C1E' : '#FFFFFF',
        background: isAI ? '#F2F2F7' : 'linear-gradient(135deg, #007AFF, #1A8FFF)',
        borderRadius: isAI ? '3px 14px 14px 14px' : '14px 3px 14px 14px',
        boxShadow: isAI ? '0 1px 3px rgba(0,0,0,0.05)' : '0 3px 10px rgba(0,122,255,0.25)',
      }}>
        {msg.content}
      </div>
    </motion.div>
  )
}

/* ── Typing dots ── */
function TypingDots() {
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '4px', alignItems: 'flex-start' }}>
      <span style={{ fontSize: '10px', fontWeight: 600, letterSpacing: '0.07em', textTransform: 'uppercase', color: '#007AFF' }}>AI</span>
      <div style={{ display: 'flex', gap: '4px', padding: '10px 13px', background: '#F2F2F7', borderRadius: '3px 14px 14px 14px' }}>
        {[0, 0.15, 0.30].map((d, i) => (
          <motion.span
            key={i}
            style={{ width: 7, height: 7, borderRadius: '50%', background: '#007AFF', display: 'block' }}
            animate={{ y: [0, -4, 0], opacity: [0.3, 1, 0.3] }}
            transition={{ duration: 1.0, delay: d, repeat: Infinity }}
          />
        ))}
      </div>
    </div>
  )
}