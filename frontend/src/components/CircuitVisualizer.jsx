import { motion } from 'framer-motion'

/**
 * CircuitVisualizer
 *
 * Displays a quantum circuit diagram, measurement probabilities,
 * and circuit metadata (depth, gate count, backend).
 *
 * Currently shows a hardcoded Bell State circuit for the demo.
 *
 * Day 3 plan:
 * This component will receive `circuitData` as a prop from the
 * MCP `circuit_draw` tool response. The data will include:
 * - gates: array of { type, qubit, position }
 * - probabilities: { [state]: percentage }
 * - metadata: { depth, gateCount, qubits, backend }
 *
 * The rendering logic is already structured to accept that shape.
 */

// Demo data — will be replaced by real MCP tool response
const DEMO_CIRCUIT = {
  name: 'Bell State Circuit',
  qubits: ['q₀', 'q₁'],
  gates: [
    // Each gate: { qubit (0-indexed), type, position (column) }
    { qubit: 0, type: 'H',  position: 1 },
    { qubit: 0, type: '●',  position: 2, control: true  }, // CNOT control
    { qubit: 1, type: '⊕',  position: 2, target: true   }, // CNOT target
    { qubit: 0, type: 'M',  position: 3, measure: true  },
    { qubit: 1, type: 'M',  position: 3, measure: true  },
  ],
  probabilities: [
    { state: '|00⟩', value: 50, color: '#63b3ed' },
    { state: '|11⟩', value: 50, color: '#76e4f7' },
  ],
  metadata: {
    depth: 3,
    gates: 3,
    qubits: 2,
    backend: 'ibmq_qasm_simulator',
  },
}

export default function CircuitVisualizer({ circuit = DEMO_CIRCUIT }) {
  return (
    <div className="flex flex-col gap-3">

      {/* Circuit diagram */}
      <motion.div
        className="bg-qm-surface border border-[rgba(99,179,237,0.12)] rounded-qm p-3.5"
        initial={{ opacity: 0, y: 8 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.4 }}
      >
        <p className="font-mono text-[9px] uppercase tracking-[2px] text-qm-accent mb-3">
          {circuit.name}
        </p>

        {/* Wire diagram */}
        <div className="flex flex-col gap-1">
          {circuit.qubits.map((qubit, qi) => {
            // Get all gates for this qubit
            const qubitGates = circuit.gates.filter((g) => g.qubit === qi)

            return (
              <div key={qubit} className="flex items-center gap-1">
                {/* Qubit label */}
                <span className="font-mono text-[10px] text-qm-muted w-7 flex-shrink-0">
                  {qubit}
                </span>

                {/* Wire with gates */}
                <div className="flex-1 flex items-center">
                  {/* Before first gate */}
                  <WireSegment />

                  {/* Render gates for each column position */}
                  {[1, 2, 3].map((col) => {
                    const gate = qubitGates.find((g) => g.position === col)
                    const isControl = gate?.control
                    const isTarget  = gate?.target
                    const isMeasure = gate?.measure

                    return (
                      <div key={col} className="flex items-center">
                        {gate ? (
                          <Gate
                            type={gate.type}
                            isControl={isControl}
                            isMeasure={isMeasure}
                          />
                        ) : (
                          <WireSegment wide />
                        )}
                        {col < 3 && <WireSegment />}
                      </div>
                    )
                  })}

                  {/* After last gate */}
                  <WireSegment />
                </div>
              </div>
            )
          })}
        </div>
      </motion.div>

      {/* State probabilities */}
      <div>
        <p className="font-mono text-[10px] uppercase tracking-[1.5px] text-qm-dim mb-2">
          State probabilities
        </p>
        <div className="grid grid-cols-2 gap-2">
          {circuit.probabilities.map((prob, i) => (
            <motion.div
              key={prob.state}
              className="bg-qm-surface border border-[rgba(99,179,237,0.12)] rounded-qm p-2.5"
              initial={{ opacity: 0, scale: 0.95 }}
              animate={{ opacity: 1, scale: 1 }}
              transition={{ delay: 0.1 + i * 0.1 }}
            >
              <div className="font-mono text-[11px] text-qm-muted mb-1">{prob.state}</div>
              <div
                className="font-display text-[20px] font-bold"
                style={{ color: prob.color }}
              >
                {prob.value}%
              </div>
              {/* Bar */}
              <div className="mt-1.5 h-[3px] bg-[rgba(99,179,237,0.12)] rounded-full overflow-hidden">
                <motion.div
                  className="h-full rounded-full"
                  style={{ background: prob.color }}
                  initial={{ width: '0%' }}
                  animate={{ width: `${prob.value}%` }}
                  transition={{ duration: 0.8, delay: 0.4 + i * 0.1, ease: 'easeOut' }}
                />
              </div>
            </motion.div>
          ))}
        </div>
      </div>

      {/* Metadata */}
      <motion.div
        className="font-mono text-[10px] text-qm-dim border border-dashed border-[rgba(99,179,237,0.12)] rounded-qm p-2.5 leading-[1.7]"
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ delay: 0.5 }}
      >
        Depth: {circuit.metadata.depth} · Gates: {circuit.metadata.gates} · Qubits: {circuit.metadata.qubits}
        <br />
        <span className="text-qm-accent3">IBM Quantum</span> · {circuit.metadata.backend}
      </motion.div>
    </div>
  )
}

/**
 * Gate — individual quantum gate box on the circuit wire
 */
function Gate({ type, isControl, isMeasure }) {
  const accentColor = isMeasure ? '#b794f4' : isControl ? '#76e4f7' : '#63b3ed'

  if (isControl) {
    // Control dot (filled circle) for CNOT
    return (
      <div
        className="w-2 h-2 rounded-full flex-shrink-0"
        style={{ background: '#76e4f7', margin: '0 4px' }}
      />
    )
  }

  return (
    <div
      className="w-[26px] h-[26px] rounded-[5px] bg-qm-surface2 flex items-center justify-center flex-shrink-0 mx-1"
      style={{
        border: `1px solid ${accentColor}`,
        color: accentColor,
        fontFamily: 'Space Mono, monospace',
        fontSize: '10px',
        fontWeight: '700',
      }}
    >
      {type}
    </div>
  )
}

/**
 * WireSegment — horizontal line between gates
 */
function WireSegment({ wide }) {
  return (
    <div
      className={`h-px bg-qm-dim ${wide ? 'w-[26px]' : 'w-[10px]'} flex-shrink-0`}
    />
  )
}