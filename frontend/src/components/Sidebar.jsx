import { motion, AnimatePresence } from 'framer-motion'
import useAppState from '@/hooks/useAppState'

const FONT = '-apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif'

// Extract bolded terms from AI messages — these are the key concepts
function extractTopics(messages) {
  const topics = []
  const seen   = new Set()

  for (const msg of messages) {
    if (msg.role !== 'ai') continue
    // Match **bold terms** — these are key concepts the Theory Agent introduces
    const matches = msg.content.match(/\*\*([^*]+)\*\*/g) || []
    for (const match of matches) {
      const term = match.replace(/\*\*/g, '').trim()
      // Filter out very short terms and duplicates
      if (term.length > 3 && !seen.has(term.toLowerCase())) {
        seen.add(term.toLowerCase())
        topics.push({ term, msgId: msg.id })
      }
    }
  }

  return topics.slice(0, 12) // max 12 topics shown
}

export default function Sidebar() {
  const messages      = useAppState(s => s.messages)
  const mode          = useAppState(s => s.mode) ?? 'guided'

  const sessionTopics = extractTopics(messages)
  const hasTopics     = sessionTopics.length > 0

  const modeColor = {
    theory:  '#007AFF',
    guided:  '#5856D6',
    practice:'#32ADE6',
  }[mode] ?? '#5856D6'

  return (
    <motion.aside
      style={{
        width: '220px', minWidth: '220px',
        display: 'flex', flexDirection: 'column',
        background: '#F7F7FA',
        borderRight: '1px solid rgba(0,0,0,0.07)',
        overflow: 'hidden', fontFamily: FONT,
      }}
      initial={{ x: -16, opacity: 0 }}
      animate={{ x: 0, opacity: 1 }}
      transition={{ duration: 0.35, delay: 0.08 }}
    >
      {/* Header */}
      <div style={{ padding: '18px 16px 14px', borderBottom: '1px solid rgba(0,0,0,0.07)' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <div style={{ width: '8px', height: '8px', borderRadius: '50%', background: modeColor, flexShrink: 0 }} />
          <p style={{ fontSize: '11px', fontWeight: 600, letterSpacing: '0.08em', textTransform: 'uppercase', color: '#AEAEB2' }}>
            Session Topics
          </p>
        </div>
      </div>

      {/* Topics list */}
      <div style={{ flex: 1, overflowY: 'auto', padding: '12px 0', scrollbarWidth: 'thin', scrollbarColor: 'rgba(0,0,0,0.1) transparent' }}>
        <AnimatePresence>
          {!hasTopics && (
            <motion.div
              style={{ padding: '20px 16px', textAlign: 'center' }}
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
            >
              <div style={{ fontSize: '28px', marginBottom: '10px' }}>💬</div>
              <p style={{ fontSize: '12px', color: '#AEAEB2', lineHeight: 1.6 }}>
                Key concepts will appear here as you learn
              </p>
            </motion.div>
          )}

          {sessionTopics.map((topic, i) => (
            <motion.div
              key={topic.term}
              style={{
                display: 'flex', alignItems: 'flex-start', gap: '10px',
                padding: '8px 16px', cursor: 'default',
              }}
              initial={{ opacity: 0, x: -12 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ delay: i * 0.05, duration: 0.25 }}
            >
              {/* Dot */}
              <div style={{
                width: '7px', height: '7px', borderRadius: '50%',
                background: modeColor, flexShrink: 0, marginTop: '5px',
                opacity: 0.8,
              }} />

              {/* Term */}
              <span style={{
                fontSize: '13px', fontWeight: 500, color: '#3C3C43',
                lineHeight: 1.4,
              }}>
                {topic.term}
              </span>
            </motion.div>
          ))}
        </AnimatePresence>
      </div>

      {/* Footer — session stats */}
      {hasTopics && (
        <div style={{
          padding: '12px 16px',
          borderTop: '1px solid rgba(0,0,0,0.07)',
        }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
            <span style={{ fontSize: '11px', color: '#AEAEB2', fontWeight: 500 }}>
              Concepts covered
            </span>
            <span style={{
              fontSize: '12px', fontWeight: 700,
              color: modeColor,
              background: `${modeColor}12`,
              padding: '2px 8px', borderRadius: '20px',
            }}>
              {sessionTopics.length}
            </span>
          </div>

          {/* Progress bar — fills as more topics are covered */}
          <div style={{ height: '4px', background: 'rgba(0,0,0,0.07)', borderRadius: '2px', overflow: 'hidden' }}>
            <motion.div
              style={{ height: '100%', borderRadius: '2px', background: `linear-gradient(90deg, ${modeColor}, ${modeColor}88)` }}
              initial={{ width: '0%' }}
              animate={{ width: `${Math.min((sessionTopics.length / 12) * 100, 100)}%` }}
              transition={{ duration: 0.5 }}
            />
          </div>
          <p style={{ fontSize: '10px', color: '#AEAEB2', marginTop: '5px' }}>
            {sessionTopics.length} of 12 concept slots
          </p>
        </div>
      )}
    </motion.aside>
  )
}