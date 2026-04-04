// src/data/curriculum.js
// QuantumMind — 13-week course curriculum
// Taught by Asfand Yar at University of Debrecen
// RAG content (PDFs + notebooks) ingested per week via /api/upload

export const CURRICULUM = [
  {
    week: 1,
    title: "Introduction to Quantum Computing",
    description: "Foundations of quantum computing, classical vs quantum, why it matters.",
    topics: [
      { id: "w1t1", title: "Classical vs Quantum Computing",     done: false },
      { id: "w1t2", title: "What is a Qubit?",                   done: false },
      { id: "w1t3", title: "Superposition Intuition",            done: false },
      { id: "w1t4", title: "Overview of Qiskit",                 done: false },
    ],
  },
  {
    week: 2,
    title: "Bloch Sphere and Single-Qubit Gates",
    description: "Visualizing qubit states and applying single-qubit transformations.",
    topics: [
      { id: "w2t1", title: "The Bloch Sphere",                   done: false },
      { id: "w2t2", title: "Pauli Gates (X, Y, Z)",              done: false },
      { id: "w2t3", title: "Hadamard Gate",                      done: false },
      { id: "w2t4", title: "Phase Gates (S, T)",                 done: false },
    ],
  },
  {
    week: 3,
    title: "Multi-Qubit Systems and Controlled Operations",
    description: "Extending to multiple qubits and introducing controlled gates.",
    topics: [
      { id: "w3t1", title: "Tensor Products",                    done: false },
      { id: "w3t2", title: "CNOT Gate",                          done: false },
      { id: "w3t3", title: "Toffoli Gate",                       done: false },
      { id: "w3t4", title: "Multi-Qubit Circuits in Qiskit",    done: false },
    ],
  },
  {
    week: 4,
    title: "Quantum Circuits in Qiskit",
    description: "Hands-on circuit building, simulation, and measurement.",
    topics: [
      { id: "w4t1", title: "Building Circuits in Qiskit",       done: false },
      { id: "w4t2", title: "Measurement and Collapse",          done: false },
      { id: "w4t3", title: "AerSimulator Basics",               done: false },
      { id: "w4t4", title: "Circuit Visualization",             done: false },
    ],
  },
  {
    week: 5,
    title: "Entanglement and Bell States",
    description: "Quantum entanglement, Bell states, and non-locality.",
    topics: [
      { id: "w5t1", title: "What is Entanglement?",             done: false },
      { id: "w5t2", title: "The Four Bell States",              done: false },
      { id: "w5t3", title: "Creating Bell States in Qiskit",    done: false },
      { id: "w5t4", title: "EPR Paradox",                       done: false },
    ],
  },
  {
    week: 6,
    title: "Quantum Teleportation",
    description: "Using entanglement and classical communication to transfer quantum states.",
    topics: [
      { id: "w6t1", title: "Teleportation Protocol",            done: false },
      { id: "w6t2", title: "Classical Communication Channel",   done: false },
      { id: "w6t3", title: "Implementing Teleportation",        done: false },
      { id: "w6t4", title: "Limitations and Misconceptions",    done: false },
    ],
  },
  {
    week: 7,
    title: "Bernstein–Vazirani Algorithm",
    description: "First quantum advantage — finding a hidden string in one query.",
    topics: [
      { id: "w7t1", title: "The Hidden String Problem",         done: false },
      { id: "w7t2", title: "Classical vs Quantum Approach",    done: false },
      { id: "w7t3", title: "BV Circuit Construction",           done: false },
      { id: "w7t4", title: "Qiskit Implementation",             done: false },
    ],
  },
  {
    week: 8,
    title: "Deutsch–Jozsa Algorithm (Part 1)",
    description: "Problem statement, oracles, and the quantum speedup.",
    topics: [
      { id: "w8t1", title: "Constant vs Balanced Functions",    done: false },
      { id: "w8t2", title: "Classical Complexity",              done: false },
      { id: "w8t3", title: "Quantum Oracles",                   done: false },
      { id: "w8t4", title: "The Deutsch Algorithm",             done: false },
    ],
  },
  {
    week: 9,
    title: "Deutsch–Jozsa Algorithm (Part 2)",
    description: "Full DJ algorithm, proof of correctness, and Qiskit implementation.",
    topics: [
      { id: "w9t1", title: "Generalising to n Qubits",         done: false },
      { id: "w9t2", title: "DJ Circuit in Qiskit",             done: false },
      { id: "w9t3", title: "Proof of Correctness",             done: false },
      { id: "w9t4", title: "Comparison with BV Algorithm",     done: false },
    ],
  },
  {
    week: 10,
    title: "Grover's Algorithm (Part 1)",
    description: "Unstructured search, amplitude amplification, and the oracle.",
    topics: [
      { id: "w10t1", title: "Unstructured Search Problem",      done: false },
      { id: "w10t2", title: "Grover Oracle",                    done: false },
      { id: "w10t3", title: "Amplitude Amplification",          done: false },
      { id: "w10t4", title: "Geometric Interpretation",         done: false },
    ],
  },
  {
    week: 11,
    title: "Grover's Algorithm (Part 2)",
    description: "Full implementation, iteration count, and applications.",
    topics: [
      { id: "w11t1", title: "Optimal Number of Iterations",     done: false },
      { id: "w11t2", title: "Grover Circuit in Qiskit",         done: false },
      { id: "w11t3", title: "Multi-Solution Grover",            done: false },
      { id: "w11t4", title: "Real-World Applications",          done: false },
    ],
  },
  {
    week: 12,
    title: "Quantum ML and Post-Quantum Cryptography",
    description: "Frontier topics — QML basics and why quantum threatens RSA.",
    topics: [
      { id: "w12t1", title: "Quantum Machine Learning Overview", done: false },
      { id: "w12t2", title: "Variational Quantum Circuits",     done: false },
      { id: "w12t3", title: "Post-Quantum Cryptography",        done: false },
      { id: "w12t4", title: "Shor's Algorithm (Overview)",      done: false },
    ],
  },
  {
    week: 13,
    title: "Project Presentations and Defense",
    description: "Students present their quantum computing projects.",
    topics: [
      { id: "w13t1", title: "Project Guidelines",               done: false },
      { id: "w13t2", title: "Presentation Structure",           done: false },
      { id: "w13t3", title: "Evaluation Criteria",              done: false },
      { id: "w13t4", title: "Q&A and Defense",                  done: false },
    ],
  },
]

// Helper: get a topic by its ID
export function getTopicById(topicId) {
  for (const week of CURRICULUM) {
    const topic = week.topics.find(t => t.id === topicId)
    if (topic) return { topic, week }
  }
  return null
}

// Helper: get all topic IDs flat
export function getAllTopicIds() {
  return CURRICULUM.flatMap(w => w.topics.map(t => t.id))
}

