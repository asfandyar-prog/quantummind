import { create } from 'zustand'

/**
 * useAppState — Global state for QuantumMind
 *
 * Why Zustand over React Context?
 * - No Provider wrapping needed
 * - Components subscribe only to what they use (no re-renders from unrelated state)
 * - Clean, flat API — reads like plain JavaScript
 * - Easy to extend as the backend connects
 *
 * Usage in any component:
 *   const mode = useAppState(s => s.mode)
 *   const setMode = useAppState(s => s.setMode)
 */
const useAppState = create((set) => ({

  // ── LEARNING MODE ─────────────────────────────────────────────
  // 'theory' | 'practice' | 'guided' | null (not yet selected)
  mode: null,
  setMode: (mode) => set({ mode }),

  // ── ACTIVE MODULE ─────────────────────────────────────────────
  // Which lesson the user is on. Used by Sidebar to show active item.
  activeModule: 'quantum-basics',
  setActiveModule: (moduleId) => set({ activeModule: moduleId }),

  // ── ACTIVE RIGHT PANEL TAB ────────────────────────────────────
  // 'circuit' | 'concepts' | 'code'
  activePanel: 'circuit',
  setActivePanel: (panel) => set({ activePanel: panel }),

  // ── CHAT HISTORY ──────────────────────────────────────────────
  // Array of { id, role: 'ai'|'user', content, timestamp, codeBlock? }
  // This will be populated by the backend in Day 2-3.
  // For now it holds the demo messages shown on first load.
  messages: [
    {
      id: '1',
      role: 'ai',
      content: "Welcome to **Quantum Basics**. Let's start from the ground up.\n\nIn classical computing, a bit is either 0 or 1. In quantum computing, a **qubit** can exist in a *superposition* of both states simultaneously — until measured.\n\nHere's a minimal Qiskit circuit that creates superposition using a Hadamard gate:",
      codeBlock: `from qiskit import QuantumCircuit

qc = QuantumCircuit(1, 1)
qc.h(0)       # Hadamard gate
qc.measure(0, 0)
qc.draw('text')`,
      timestamp: new Date().toISOString(),
    },
    {
      id: '2',
      role: 'user',
      content: 'What does the Hadamard gate actually do mathematically?',
      timestamp: new Date().toISOString(),
    },
    {
      id: '3',
      role: 'ai',
      content: "The Hadamard gate maps the computational basis states:\n\n**|0⟩ → (|0⟩ + |1⟩) / √2**\n**|1⟩ → (|0⟩ − |1⟩) / √2**\n\nIt creates an *equal superposition* — a 50/50 probability of measuring either state. This is the foundation of quantum parallelism.",
      timestamp: new Date().toISOString(),
    },
  ],

  // Append a new message to chat history
  addMessage: (message) =>
    set((state) => ({
      messages: [
        ...state.messages,
        {
          id: Date.now().toString(),
          timestamp: new Date().toISOString(),
          ...message,
        },
      ],
    })),

  // Clear chat (used when switching modules)
  clearMessages: () => set({ messages: [] }),

  // ── COURSE PROGRESS ──────────────────────────────────────────
  // Which topics the student has completed in the course
  completedTopics: [],
  markTopicComplete: (topicId) =>
    set((state) => ({
      completedTopics: state.completedTopics.includes(topicId)
        ? state.completedTopics
        : [...state.completedTopics, topicId],
    })),

  // Active course topic
  activeTopicId: null,
  setActiveTopicId: (id) => set({ activeTopicId: id }),

  activeWeek: 1,
  setActiveWeek: (week) => set({ activeWeek: week }),

  // ── STREAMING STATE ───────────────────────────────────────────
  // Whether the AI is currently generating a response.
  // Used to show the typing indicator and disable the send button.
  isStreaming: false,
  setIsStreaming: (val) => set({ isStreaming: val }),

  // ── SIDEBAR ───────────────────────────────────────────────────
  isSidebarOpen: true,
  toggleSidebar: () => set((state) => ({ isSidebarOpen: !state.isSidebarOpen })),

}))

export default useAppState