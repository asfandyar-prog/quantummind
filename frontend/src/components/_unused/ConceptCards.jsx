import { motion } from 'framer-motion'
import { useState } from 'react'

/**
 * ConceptCards
 *
 * Displays key quantum concepts relevant to the current lesson.
 * Each card is expandable to show the full definition.
 *
 * Day 3 plan:
 * Concepts will be extracted automatically by the Theory Agent
 * from each AI response. The agent will tag which concepts it
 * referenced, and this panel will populate from that metadata.
 *
 * For now, the cards are hardcoded for the Quantum Basics lesson.
 */

const DEMO_CONCEPTS = [
  {
    id: 'superposition',
    tag: 'Core Concept',
    title: 'Superposition',
    summary: 'A qubit exists in a combination of |0⟩ and |1⟩ until measured.',
    detail: 'Described mathematically by α|0⟩ + β|1⟩ where |α|² + |β|² = 1. The coefficients α and β are complex probability amplitudes. Measurement collapses the state to |0⟩ with probability |α|² or |1⟩ with probability |β|².',
  },
  {
    id: 'hadamard',
    tag: 'Key Gate',
    title: 'Hadamard Gate',
    summary: 'Creates equal superposition from a basis state. H = (1/√2)[[1,1],[1,-1]].',
    detail: 'Applied to |0⟩, produces (|0⟩ + |1⟩)/√2. Applied to |1⟩, produces (|0⟩ − |1⟩)/√2. The Hadamard gate is its own inverse: H² = I. It transforms between the computational basis and the Hadamard basis.',
  },
  {
    id: 'entanglement',
    tag: 'Phenomenon',
    title: 'Entanglement',
    summary: 'Two qubits become correlated — measuring one instantly determines the other.',
    detail: 'An entangled state cannot be written as a product of individual qubit states. The Bell state (|00⟩ + |11⟩)/√2 is the simplest example. Measuring the first qubit in state |0⟩ immediately collapses the second to |0⟩, regardless of distance.',
  },
]

export default function ConceptCards({ concepts = DEMO_CONCEPTS }) {
  return (
    <div className="flex flex-col gap-2.5">
      {concepts.map((concept, i) => (
        <ConceptCard key={concept.id} concept={concept} index={i} />
      ))}
    </div>
  )
}

/**
 * ConceptCard — individual expandable concept card
 */
function ConceptCard({ concept, index }) {
  const [expanded, setExpanded] = useState(false)

  return (
    <motion.div
      className="bg-qm-surface border border-[rgba(99,179,237,0.12)] rounded-qm p-3.5 cursor-pointer"
      style={{ '--hover-border': 'rgba(99,179,237,0.22)' }}
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: 0.1 + index * 0.1 }}
      whileHover={{ borderColor: 'rgba(99,179,237,0.22)' }}
      onClick={() => setExpanded((prev) => !prev)}
    >
      {/* Tag */}
      <p className="font-mono text-[9px] uppercase tracking-[1.5px] text-qm-accent3 mb-1.5">
        {concept.tag}
      </p>

      {/* Title row */}
      <div className="flex items-center justify-between">
        <h3 className="font-display text-[14px] font-semibold text-qm-text">
          {concept.title}
        </h3>
        <motion.span
          className="text-qm-dim text-[12px] font-mono flex-shrink-0 ml-2"
          animate={{ rotate: expanded ? 90 : 0 }}
          transition={{ duration: 0.2 }}
        >
          ›
        </motion.span>
      </div>

      {/* Summary — always visible */}
      <p className="text-[12px] text-qm-muted leading-relaxed mt-1.5">
        {concept.summary}
      </p>

      {/* Detail — expanded only */}
      <motion.div
        initial={false}
        animate={{ height: expanded ? 'auto' : 0, opacity: expanded ? 1 : 0 }}
        transition={{ duration: 0.25, ease: 'easeInOut' }}
        style={{ overflow: 'hidden' }}
      >
        <p className="text-[12px] text-qm-muted leading-relaxed mt-2.5 pt-2.5 border-t border-[rgba(99,179,237,0.08)]">
          {concept.detail}
        </p>
      </motion.div>
    </motion.div>
  )
}