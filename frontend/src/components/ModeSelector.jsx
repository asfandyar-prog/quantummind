import { useNavigate } from 'react-router-dom'
import { motion } from 'framer-motion'
import useAppState from '@/hooks/useAppState'
import Badge from '@/components/ui/Badge'

const MODES = [
  {
    id: 'theory',
    icon: '⚛',
    title: 'Theory',
    description: 'Deep-dive into quantum concepts with your AI tutor. Superposition, entanglement, algorithms — explained with clarity.',
    tags: ['Concepts', 'Q&A', 'Explanations'],
    accent: '#007AFF',
    tint: 'rgba(0,122,255,0.06)',
    iconBg: 'rgba(0,122,255,0.1)',
  },
  {
    id: 'practice',
    icon: '⟨ψ|',
    title: 'Practice',
    description: 'Write and execute real Qiskit code. Build circuits, run on IBM Quantum simulators, get instant AI review.',
    tags: ['Qiskit', 'Circuits', 'Execution'],
    accent: '#32ADE6',
    tint: 'rgba(50,173,230,0.06)',
    iconBg: 'rgba(50,173,230,0.1)',
  },
  {
    id: 'guided',
    icon: '∞',
    title: 'Guided Learning',
    description: 'Structured lessons combining theory, interactive code, and circuit visualization in one seamless flow.',
    tags: ['Theory', 'Code', 'Circuits'],
    accent: '#5856D6',
    tint: 'rgba(88,86,214,0.06)',
    iconBg: 'rgba(88,86,214,0.1)',
  },
  {
    id: 'course',
    icon: '🎓',
    title: '13-Week Course',
    description: 'Structured quantum computing curriculum with weekly chapters, lecture notes, lab code, and RAG-powered AI tutor.',
    tags: ['Curriculum', 'RAG', 'Labs'],
    accent: '#34C759',
    tint: 'rgba(52,199,89,0.06)',
    iconBg: 'rgba(52,199,89,0.1)',
  },
]

const containerVariants = {
  hidden: {},
  visible: { transition: { staggerChildren: 0.1, delayChildren: 0.25 } },
}
const cardVariants = {
  hidden:  { opacity: 0, y: 18 },
  visible: { opacity: 1, y: 0, transition: { duration: 0.4, ease: [0.16, 1, 0.3, 1] } },
}

export default function ModeSelector() {
  const navigate = useNavigate()
  const setMode  = useAppState((s) => s.setMode)

  function handleSelect(modeId) {
    setMode(modeId)
    navigate('/app')
  }

  return (
    <div
      className="w-full h-full flex flex-col items-center justify-center px-12 py-16"
      style={{
        background: 'linear-gradient(160deg, #EEF4FF 0%, #F2F2F7 50%, #EAF5FF 100%)',
        fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif',
      }}
    >
      {/* Header */}
      <motion.div
        className="text-center"
        style={{ marginBottom: '56px' }}
        initial={{ opacity: 0, y: 14 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.45 }}
      >
        {/* Eyebrow pill */}
        <div
          className="inline-flex items-center gap-2 rounded-full"
          style={{
            background: 'rgba(0,122,255,0.08)',
            border: '1px solid rgba(0,122,255,0.15)',
            padding: '6px 16px',
            marginBottom: '20px',
          }}
        >
          <div className="w-1.5 h-1.5 rounded-full flex-shrink-0" style={{ background: '#007AFF' }} />
          <span style={{ color: '#007AFF', fontSize: '11px', letterSpacing: '0.1em', textTransform: 'uppercase', fontWeight: 600 }}>
            Select your path
          </span>
        </div>

        {/* Heading */}
        <h1 style={{ fontSize: '42px', fontWeight: 700, letterSpacing: '-0.5px', color: '#1C1C1E', lineHeight: 1.2, marginBottom: '14px' }}>
          What do you want to{' '}
          <span className="text-gradient-qm">learn today?</span>
        </h1>

        {/* Subtitle */}
        <p style={{ fontSize: '17px', color: '#6C6C70', fontWeight: 400, lineHeight: 1.5 }}>
          Choose a mode to begin your quantum journey
        </p>
      </motion.div>

      {/* Cards grid */}
      <motion.div
        className="grid grid-cols-3 w-full"
        style={{ gap: '24px', maxWidth: '980px', gridTemplateColumns: 'repeat(2, 1fr)' }}
        variants={containerVariants}
        initial="hidden"
        animate="visible"
      >
        {MODES.map((mode) => (
          <ModeCard key={mode.id} mode={mode} onSelect={handleSelect} />
        ))}
      </motion.div>
    </div>
  )
}

function ModeCard({ mode, onSelect }) {
  return (
    <motion.div
      variants={cardVariants}
      className="relative flex flex-col cursor-pointer overflow-hidden"
      style={{
        background: '#FFFFFF',
        borderRadius: '20px',
        boxShadow: '0 2px 20px rgba(0,0,0,0.07), 0 1px 4px rgba(0,0,0,0.04)',
        border: '1px solid rgba(0,0,0,0.06)',
        padding: '32px 28px 28px',
        fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif',
      }}
      whileHover={{
        y: -6,
        boxShadow: `0 16px 40px rgba(0,0,0,0.11), 0 0 0 1.5px ${mode.accent}`,
        transition: { duration: 0.2, ease: 'easeOut' },
      }}
      whileTap={{ scale: 0.985 }}
      onClick={() => onSelect(mode.id)}
    >
      {/* Hover tint */}
      <motion.div
        className="absolute inset-0 pointer-events-none"
        style={{ borderRadius: '20px', background: `radial-gradient(ellipse at 55% 0%, ${mode.tint} 0%, transparent 60%)` }}
        initial={{ opacity: 0 }}
        whileHover={{ opacity: 1 }}
        transition={{ duration: 0.25 }}
      />

      {/* Icon */}
      <div
        className="relative z-10 flex-shrink-0"
        style={{
          width: '52px', height: '52px',
          borderRadius: '14px',
          background: mode.iconBg,
          display: 'flex', alignItems: 'center', justifyContent: 'center',
          fontSize: mode.id === 'practice' ? '14px' : '22px',
          color: mode.accent,
          marginBottom: '22px',
          fontFamily: 'SF Mono, ui-monospace, monospace',
        }}
      >
        {mode.icon}
      </div>

      {/* Title */}
      <h2
        className="relative z-10"
        style={{ fontSize: '20px', fontWeight: 600, color: '#1C1C1E', marginBottom: '10px', letterSpacing: '-0.2px' }}
      >
        {mode.title}
      </h2>

      {/* Description */}
      <p
        className="relative z-10 flex-1"
        style={{ fontSize: '14px', color: '#6C6C70', lineHeight: '1.65', marginBottom: '24px' }}
      >
        {mode.description}
      </p>

      {/* Tags — explicit gap so they never run together */}
      <div className="relative z-10" style={{ display: 'flex', flexWrap: 'wrap', gap: '8px' }}>
        {mode.tags.map((tag) => (
          <span
            key={tag}
            style={{
              display: 'inline-block',
              fontSize: '12px',
              fontWeight: 500,
              color: mode.accent,
              background: mode.iconBg,
              border: `1px solid ${mode.accent}33`,
              borderRadius: '6px',
              padding: '4px 10px',
              letterSpacing: '0.01em',
            }}
          >
            {tag}
          </span>
        ))}
      </div>

      {/* Arrow on hover */}
      <motion.div
        className="absolute"
        style={{
          bottom: '28px', right: '28px',
          width: '28px', height: '28px',
          borderRadius: '50%',
          background: mode.iconBg,
          color: mode.accent,
          display: 'flex', alignItems: 'center', justifyContent: 'center',
          fontSize: '14px',
        }}
        initial={{ opacity: 0, scale: 0.6 }}
        whileHover={{ opacity: 1, scale: 1 }}
        transition={{ duration: 0.18 }}
      >
        →
      </motion.div>
    </motion.div>
  )
}