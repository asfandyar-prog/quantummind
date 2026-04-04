import { useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { CURRICULUM } from '@/data/curriculum'

const FONT = '-apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif'

export default function CourseSidebar({ activeTopicId, onSelectTopic, completedTopics = [] }) {
  const [expandedWeeks, setExpandedWeeks] = useState([1])

  const totalTopics    = CURRICULUM.reduce((acc, w) => acc + w.topics.length, 0)
  const completedCount = completedTopics.length
  const progressPct    = Math.round((completedCount / totalTopics) * 100)

  function toggleWeek(weekNum) {
    setExpandedWeeks(prev =>
      prev.includes(weekNum) ? prev.filter(w => w !== weekNum) : [...prev, weekNum]
    )
  }

  return (
    <motion.aside
      style={{
        width: '280px', minWidth: '280px',
        display: 'flex', flexDirection: 'column',
        background: '#FAFAFA',
        borderRight: '1px solid rgba(0,0,0,0.08)',
        overflow: 'hidden', fontFamily: FONT,
      }}
      initial={{ x: -20, opacity: 0 }}
      animate={{ x: 0, opacity: 1 }}
      transition={{ duration: 0.35 }}
    >
      {/* Header */}
      <div style={{ padding: '20px 20px 16px', borderBottom: '1px solid rgba(0,0,0,0.07)', background: '#FFFFFF' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '14px' }}>
          <div style={{ width: '28px', height: '28px', borderRadius: '8px', background: 'linear-gradient(135deg, #34C759, #30D158)', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: '14px' }}>
            🎓
          </div>
          <div>
            <p style={{ fontSize: '13px', fontWeight: 700, color: '#1C1C1E', lineHeight: 1 }}>13-Week Course</p>
            <p style={{ fontSize: '11px', color: '#AEAEB2', marginTop: '2px' }}>Quantum Computing</p>
          </div>
        </div>

        {/* Progress bar */}
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '6px' }}>
          <span style={{ fontSize: '12px', color: '#6C6C70' }}>Overall progress</span>
          <span style={{ fontSize: '12px', fontWeight: 700, color: '#34C759' }}>{progressPct}%</span>
        </div>
        <div style={{ height: '6px', background: 'rgba(0,0,0,0.07)', borderRadius: '3px', overflow: 'hidden' }}>
          <motion.div
            style={{ height: '100%', background: 'linear-gradient(90deg, #34C759, #30D158)', borderRadius: '3px' }}
            initial={{ width: '0%' }}
            animate={{ width: `${progressPct}%` }}
            transition={{ duration: 0.8, ease: 'easeOut' }}
          />
        </div>
        <p style={{ fontSize: '11px', color: '#AEAEB2', marginTop: '5px' }}>
          {completedCount} of {totalTopics} topics completed
        </p>
      </div>

      {/* Week list */}
      <div style={{ flex: 1, overflowY: 'auto', scrollbarWidth: 'thin', scrollbarColor: 'rgba(0,0,0,0.1) transparent' }}>
        {CURRICULUM.map((week) => {
          const isExpanded    = expandedWeeks.includes(week.week)
          const weekCompleted = week.topics.filter(t => completedTopics.includes(t.id)).length
          const hasActive     = week.topics.some(t => t.id === activeTopicId)

          return (
            <div key={week.week} style={{ borderBottom: '1px solid rgba(0,0,0,0.05)' }}>
              {/* Week header */}
              <button
                onClick={() => toggleWeek(week.week)}
                style={{
                  width: '100%', padding: '12px 16px',
                  display: 'flex', alignItems: 'center', gap: '10px',
                  background: hasActive ? 'rgba(52,199,89,0.04)' : 'transparent',
                  border: 'none', cursor: 'pointer', textAlign: 'left',
                  fontFamily: FONT,
                }}
              >
                {/* Week badge */}
                <div style={{
                  width: '24px', height: '24px', borderRadius: '7px', flexShrink: 0,
                  background: weekCompleted === week.topics.length && weekCompleted > 0
                    ? '#34C759'
                    : hasActive ? 'rgba(52,199,89,0.15)' : 'rgba(0,0,0,0.08)',
                  display: 'flex', alignItems: 'center', justifyContent: 'center',
                  fontSize: '10px', fontWeight: 700,
                  color: weekCompleted === week.topics.length && weekCompleted > 0
                    ? '#fff' : hasActive ? '#34C759' : '#6C6C70',
                }}>
                  {week.week}
                </div>

                {/* Week info */}
                <div style={{ flex: 1, minWidth: 0 }}>
                  <p style={{
                    fontSize: '13px', fontWeight: hasActive ? 600 : 500,
                    color: hasActive ? '#1C1C1E' : '#3C3C43',
                    lineHeight: 1.3, marginBottom: '2px',
                    whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis',
                  }}>
                    {week.title}
                  </p>
                  <p style={{ fontSize: '11px', color: '#AEAEB2' }}>
                    {weekCompleted}/{week.topics.length} topics
                  </p>
                </div>

                <motion.span
                  style={{ fontSize: '14px', color: '#AEAEB2', flexShrink: 0 }}
                  animate={{ rotate: isExpanded ? 90 : 0 }}
                  transition={{ duration: 0.18 }}
                >›</motion.span>
              </button>

              {/* Topics */}
              <AnimatePresence initial={false}>
                {isExpanded && (
                  <motion.div
                    initial={{ height: 0, opacity: 0 }}
                    animate={{ height: 'auto', opacity: 1 }}
                    exit={{ height: 0, opacity: 0 }}
                    transition={{ duration: 0.2 }}
                    style={{ overflow: 'hidden', background: 'rgba(0,0,0,0.01)' }}
                  >
                    {week.topics.map((topic, ti) => {
                      const isActive = topic.id === activeTopicId
                      const isDone   = completedTopics.includes(topic.id)

                      return (
                        <motion.button
                          key={topic.id}
                          onClick={() => onSelectTopic(topic.id, week.week)}
                          style={{
                            width: '100%', padding: '9px 16px 9px 50px',
                            display: 'flex', alignItems: 'center', gap: '9px',
                            background: isActive ? 'rgba(52,199,89,0.08)' : 'transparent',
                            border: 'none', cursor: 'pointer', textAlign: 'left',
                            fontFamily: FONT, position: 'relative',
                          }}
                          initial={{ opacity: 0 }}
                          animate={{ opacity: 1 }}
                          transition={{ delay: ti * 0.03 }}
                        >
                          {isActive && (
                            <span style={{ position: 'absolute', left: 0, top: '15%', bottom: '15%', width: '3px', borderRadius: '0 3px 3px 0', background: '#34C759' }} />
                          )}
                          <span style={{
                            width: '8px', height: '8px', borderRadius: '50%', flexShrink: 0,
                            background: isDone ? '#34C759' : isActive ? '#34C759' : 'rgba(0,0,0,0.15)',
                            border: isActive && !isDone ? '2px solid #34C759' : isDone ? 'none' : 'none',
                          }} />
                          <span style={{
                            fontSize: '13px', fontWeight: isActive ? 600 : 400,
                            color: isActive ? '#1C1C1E' : '#3C3C43', lineHeight: 1.4,
                          }}>
                            {topic.title}
                          </span>
                        </motion.button>
                      )
                    })}
                  </motion.div>
                )}
              </AnimatePresence>
            </div>
          )
        })}
      </div>
    </motion.aside>
  )
}