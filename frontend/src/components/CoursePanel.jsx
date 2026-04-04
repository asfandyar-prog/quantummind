import { useState, useRef, useEffect } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { CURRICULUM, getTopicById } from '@/data/curriculum'

const FONT    = '-apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif'
const MONO    = 'SF Mono, ui-monospace, Menlo, Consolas, monospace'
const BACKEND = 'http://localhost:8000'

function getThreadId() {
  let id = localStorage.getItem('qm_thread_id')
  if (!id) { id = 'thread_' + Date.now() + '_' + Math.random().toString(36).slice(2); localStorage.setItem('qm_thread_id', id) }
  return id
}

export default function CoursePanel({ activeTopicId, activeWeek, onMarkComplete, completedTopics = [] }) {
  const [messages, setMessages]      = useState([])
  const [isStreaming, setIsStreaming] = useState(false)
  const [activeTab, setActiveTab]    = useState('lesson')
  const textareaRef = useRef(null)
  const bottomRef   = useRef(null)

  const topicInfo = getTopicById(activeTopicId)
  const topic     = topicInfo?.topic
  const week      = topicInfo?.week
  const isDone    = completedTopics.includes(activeTopicId)

  useEffect(() => { setMessages([]); setActiveTab('lesson') }, [activeTopicId])
  useEffect(() => { bottomRef.current?.scrollIntoView({ behavior: 'smooth' }) }, [messages, isStreaming])

  async function handleSend(text) {
    const msg = (text ?? textareaRef.current?.value ?? '').trim()
    if (!msg || isStreaming) return
    if (!text && textareaRef.current) { textareaRef.current.value = ''; textareaRef.current.style.height = 'auto' }

    const userMsg = { id: Date.now().toString(), role: 'user', content: msg }
    const aiId    = (Date.now() + 1).toString()
    setMessages(prev => [...prev, userMsg, { id: aiId, role: 'ai', content: '' }])
    setIsStreaming(true)
    let aiResponse = ''

    try {
      const res = await fetch(`${BACKEND}/api/stream`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: msg, mode: 'course', chat_history: [], thread_id: `${getThreadId()}_w${activeWeek}_${activeTopicId}`, week: activeWeek }),
      })
      const reader = res.body.getReader(); const decoder = new TextDecoder()
      while (true) {
        const { done, value } = await reader.read(); if (done) break
        for (const line of decoder.decode(value, { stream: true }).split('\n')) {
          if (!line.startsWith('data: ')) continue
          try {
            const event = JSON.parse(line.slice(6))
            if (event.type === 'token') { aiResponse += event.content; setMessages(prev => prev.map(m => m.id === aiId ? { ...m, content: aiResponse } : m)) }
          } catch (_) { continue }
        }
      }
    } catch (e) {
      setMessages(prev => prev.map(m => m.id === aiId ? { ...m, content: 'Something went wrong. Please try again.' } : m))
    } finally { setIsStreaming(false) }
  }

  // Welcome screen — no topic selected
  if (!topic) {
    return (
      <div style={{ flex:1, display:'flex', alignItems:'center', justifyContent:'center', background:'#FFFFFF', fontFamily:FONT }}>
        <div style={{ textAlign:'center', maxWidth:'400px', padding:'40px' }}>
          <div style={{ fontSize:'56px', marginBottom:'20px' }}>📚</div>
          <h2 style={{ fontSize:'22px', fontWeight:700, color:'#1C1C1E', marginBottom:'10px' }}>Start Learning</h2>
          <p style={{ fontSize:'15px', color:'#6C6C70', lineHeight:1.6 }}>
            Select a week and topic from the sidebar to begin your quantum computing journey.
          </p>
        </div>
      </div>
    )
  }

  return (
    <div style={{ flex:1, display:'flex', flexDirection:'column', overflow:'hidden', background:'#FFFFFF', fontFamily:FONT }}>

      {/* Topic header */}
      <div style={{ padding:'28px 48px 0', borderBottom:'1px solid rgba(0,0,0,0.07)', flexShrink:0 }}>
        <div style={{ display:'flex', alignItems:'flex-start', justifyContent:'space-between', marginBottom:'20px' }}>
          <div>
            {/* Breadcrumb */}
            <div style={{ display:'flex', alignItems:'center', gap:'8px', marginBottom:'8px' }}>
              <span style={{ fontSize:'12px', fontWeight:600, color:'#34C759', letterSpacing:'0.06em', textTransform:'uppercase' }}>
                Week {week?.week}
              </span>
              <span style={{ color:'#AEAEB2', fontSize:'14px' }}>›</span>
              <span style={{ fontSize:'12px', color:'#6C6C70' }}>{week?.title}</span>
            </div>
            <h1 style={{ fontSize:'28px', fontWeight:700, color:'#1C1C1E', letterSpacing:'-0.5px', lineHeight:1.2 }}>
              {topic.title}
            </h1>
          </div>

          {/* Mark complete */}
          <button
            onClick={() => onMarkComplete(activeTopicId)}
            style={{
              padding:'10px 20px', borderRadius:'12px', border:'none',
              background: isDone ? 'rgba(52,199,89,0.1)' : 'linear-gradient(135deg, #34C759, #30D158)',
              color: isDone ? '#34C759' : '#fff',
              fontSize:'14px', fontWeight:600, cursor:'pointer', fontFamily:FONT,
              boxShadow: isDone ? 'none' : '0 4px 14px rgba(52,199,89,0.35)',
              display:'flex', alignItems:'center', gap:'7px', flexShrink:0,
              transition:'all 0.2s',
            }}
          >
            {isDone ? '✓ Completed' : '✓ Mark Complete'}
          </button>
        </div>

        {/* Tabs */}
        <div style={{ display:'flex', gap:'4px' }}>
          {[{ id:'lesson', label:'📖 Lesson' }, { id:'chat', label:'🤖 Ask AI' }].map(tab => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              style={{
                padding:'10px 24px', border:'none', background:'transparent',
                fontSize:'14px', fontWeight: activeTab === tab.id ? 600 : 400,
                color: activeTab === tab.id ? '#34C759' : '#6C6C70',
                borderBottom:`2px solid ${activeTab === tab.id ? '#34C759' : 'transparent'}`,
                cursor:'pointer', fontFamily:FONT, transition:'all 0.15s',
              }}
            >
              {tab.label}
            </button>
          ))}
        </div>
      </div>

      {/* Content */}
      <AnimatePresence mode="wait">
        {activeTab === 'lesson' ? (
          <motion.div
            key="lesson"
            style={{ flex:1, overflowY:'auto', padding:'36px 48px', scrollbarWidth:'thin' }}
            initial={{ opacity:0, y:8 }} animate={{ opacity:1, y:0 }} exit={{ opacity:0 }}
            transition={{ duration:0.2 }}
          >
            <LessonContent topic={topic} week={week} onAskAI={q => { setActiveTab('chat'); setTimeout(() => handleSend(q), 100) }} />
          </motion.div>
        ) : (
          <motion.div
            key="chat"
            style={{ flex:1, display:'flex', flexDirection:'column', overflow:'hidden' }}
            initial={{ opacity:0, y:8 }} animate={{ opacity:1, y:0 }} exit={{ opacity:0 }}
            transition={{ duration:0.2 }}
          >
            {/* Messages */}
            <div style={{ flex:1, overflowY:'auto', padding:'28px 48px', display:'flex', flexDirection:'column', gap:'22px', scrollbarWidth:'thin' }}>
              {messages.length === 0 && (
                <div style={{ textAlign:'center', padding:'60px 20px', color:'#AEAEB2' }}>
                  <div style={{ fontSize:'40px', marginBottom:'14px' }}>🤖</div>
                  <p style={{ fontSize:'16px', fontWeight:600, color:'#6C6C70', marginBottom:'6px' }}>Course AI Tutor</p>
                  <p style={{ fontSize:'14px', lineHeight:1.6 }}>
                    Ask me anything about <strong style={{ color:'#1C1C1E' }}>{topic.title}</strong>.<br />
                    My answers are grounded in your Week {activeWeek} course materials.
                  </p>
                </div>
              )}
              {messages.map(msg => (
                <div key={msg.id} style={{ display:'flex', flexDirection:'column', gap:'6px', alignItems: msg.role === 'ai' ? 'flex-start' : 'flex-end' }}>
                  <span style={{ fontSize:'11px', fontWeight:600, letterSpacing:'0.07em', textTransform:'uppercase', color: msg.role === 'ai' ? '#34C759' : '#AEAEB2' }}>
                    {msg.role === 'ai' ? 'Course AI' : 'You'}
                  </span>
                  <div style={{
                    maxWidth:'78%', padding:'14px 18px', fontSize:'15px', lineHeight:'1.7', fontFamily:FONT,
                    color: msg.role === 'ai' ? '#1C1C1E' : '#fff',
                    background: msg.role === 'ai' ? '#F2F2F7' : 'linear-gradient(135deg, #34C759, #30D158)',
                    borderRadius: msg.role === 'ai' ? '4px 18px 18px 18px' : '18px 4px 18px 18px',
                    boxShadow: msg.role === 'ai' ? '0 1px 4px rgba(0,0,0,0.06)' : '0 3px 12px rgba(52,199,89,0.25)',
                  }}>
                    {msg.content || <motion.span animate={{ opacity:[0.4,1,0.4] }} transition={{ duration:1.2, repeat:Infinity }}>●●●</motion.span>}
                  </div>
                </div>
              ))}
              <div ref={bottomRef} />
            </div>

            {/* Input */}
            <div style={{ padding:'14px 48px 20px', borderTop:'1px solid rgba(0,0,0,0.07)', background:'rgba(247,247,250,0.9)', display:'flex', gap:'12px', alignItems:'flex-end' }}>
              <textarea
                ref={textareaRef}
                rows={1}
                placeholder={`Ask about ${topic.title}…`}
                onKeyDown={e => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); handleSend() } }}
                onInput={e => { e.target.style.height = 'auto'; e.target.style.height = Math.min(e.target.scrollHeight, 120) + 'px' }}
                disabled={isStreaming}
                style={{ flex:1, resize:'none', border:'none', outline:'none', background:'#FFFFFF', borderRadius:'14px', padding:'12px 18px', fontSize:'15px', fontFamily:FONT, lineHeight:'1.5', color:'#1C1C1E', minHeight:'46px', maxHeight:'120px', overflow:'hidden', boxShadow:'0 1px 6px rgba(0,0,0,0.08), 0 0 0 1px rgba(0,0,0,0.07)', transition:'box-shadow 0.2s' }}
                onFocus={e => e.target.style.boxShadow='0 1px 6px rgba(0,0,0,0.08), 0 0 0 2px rgba(52,199,89,0.35)'}
                onBlur={e  => e.target.style.boxShadow='0 1px 6px rgba(0,0,0,0.08), 0 0 0 1px rgba(0,0,0,0.07)'}
              />
              <motion.button
                onClick={() => handleSend()}
                disabled={isStreaming}
                style={{ width:'46px', height:'46px', borderRadius:'50%', border:'none', background:'linear-gradient(135deg, #34C759, #30D158)', color:'#fff', fontSize:'18px', cursor:'pointer', flexShrink:0, display:'flex', alignItems:'center', justifyContent:'center', boxShadow:'0 2px 10px rgba(52,199,89,0.35)', opacity: isStreaming ? 0.5 : 1 }}
                whileHover={!isStreaming ? { scale:1.06 } : {}}
                whileTap={!isStreaming ? { scale:0.94 } : {}}
              >↑</motion.button>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  )
}

function LessonContent({ topic, week, onAskAI }) {
  const suggestions = [
    `Explain ${topic.title} from scratch`,
    `What are the key concepts in ${topic.title}?`,
    `Show me Qiskit code for ${topic.title}`,
    `How does ${topic.title} connect to quantum advantage?`,
  ]

  return (
    <div style={{ maxWidth:'100%', paddingRight: '40px' }}>
      {/* Week description card */}
      <div style={{ padding:'24px 28px', borderRadius:'16px', background:'linear-gradient(135deg, rgba(52,199,89,0.06), rgba(52,199,89,0.03))', border:'1px solid rgba(52,199,89,0.15)', marginBottom:'36px' }}>
        <p style={{ fontSize:'16px', color:'#1C1C1E', lineHeight:'1.7', margin:0 }}>
          {week?.description}
        </p>
      </div>

      {/* Topics in this week */}
      <h3 style={{ fontSize:'12px', fontWeight:600, letterSpacing:'0.1em', textTransform:'uppercase', color:'#AEAEB2', marginBottom:'14px' }}>
        This week covers
      </h3>
      <div style={{ display:'flex', flexDirection:'column', gap:'8px', marginBottom:'40px' }}>
        {week?.topics.map((t, i) => {
          const isCurrentTopic = t.id === topic.id
          return (
            <motion.div
              key={t.id}
              style={{
                display:'flex', alignItems:'center', gap:'14px',
                padding:'14px 18px', borderRadius:'12px',
                background: isCurrentTopic ? 'rgba(52,199,89,0.07)' : '#F9F9FB',
                border:`1px solid ${isCurrentTopic ? 'rgba(52,199,89,0.25)' : 'rgba(0,0,0,0.06)'}`,
              }}
              initial={{ opacity:0, x:-8 }}
              animate={{ opacity:1, x:0 }}
              transition={{ delay: i * 0.06 }}
            >
              <div style={{ width:'28px', height:'28px', borderRadius:'8px', background: isCurrentTopic ? '#34C759' : 'rgba(0,0,0,0.07)', display:'flex', alignItems:'center', justifyContent:'center', fontSize:'12px', fontWeight:700, color: isCurrentTopic ? '#fff' : '#6C6C70', flexShrink:0 }}>
                {i + 1}
              </div>
              <span style={{ fontSize:'15px', color: isCurrentTopic ? '#1C1C1E' : '#6C6C70', fontWeight: isCurrentTopic ? 600 : 400 }}>
                {t.title}
              </span>
              {isCurrentTopic && (
                <span style={{ marginLeft:'auto', fontSize:'11px', fontWeight:600, color:'#34C759', background:'rgba(52,199,89,0.1)', padding:'3px 10px', borderRadius:'20px' }}>
                  Current
                </span>
              )}
            </motion.div>
          )
        })}
      </div>

      {/* Ask AI section */}
      <h3 style={{ fontSize:'12px', fontWeight:600, letterSpacing:'0.1em', textTransform:'uppercase', color:'#AEAEB2', marginBottom:'14px' }}>
        Ask the course AI
      </h3>
      <div style={{ display:'grid', gridTemplateColumns:'1fr 1fr 1fr', gap:'12px' }}>
        {suggestions.map((q, i) => (
          <motion.button
            key={i}
            onClick={() => onAskAI(q)}
            style={{ padding:'16px 18px', borderRadius:'14px', border:'1px solid rgba(0,0,0,0.08)', background:'#FFFFFF', color:'#3C3C43', fontSize:'14px', fontFamily:FONT, textAlign:'left', cursor:'pointer', lineHeight:1.5, boxShadow:'0 1px 4px rgba(0,0,0,0.05)' }}
            initial={{ opacity:0, y:8 }} animate={{ opacity:1, y:0 }} transition={{ delay:0.1 + i * 0.07 }}
            whileHover={{ y:-3, boxShadow:'0 6px 20px rgba(0,0,0,0.09)', borderColor:'rgba(52,199,89,0.3)' }}
            whileTap={{ scale:0.97 }}
          >
            <span style={{ color:'#34C759', marginRight:'10px', fontSize:'16px' }}>→</span>{q}
          </motion.button>
        ))}
      </div>
    </div>
  )
}