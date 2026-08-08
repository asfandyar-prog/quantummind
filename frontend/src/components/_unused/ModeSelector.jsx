import QuantumField from './QuantumField';
import RevealOnView from './RevealOnView';

const MODES = [
  {
    delay: 0.15,
    tags: ['Concept Explanations', 'Visual Diagrams', 'No Code Needed', 'Self-Paced'],
    title: 'Theory',
    body: "Chat through quantum concepts with an AI tutor. Get plain-language explanations, diagrams, and follow-up questions tailored to where you're stuck.",
    icon: <BookOpenIcon />,
  },
  {
    delay: 0.28,
    tags: ['Live Qiskit Editor', 'Instant Execution', 'AI Code Review', 'Real Circuits'],
    title: 'Practice',
    body: "Write real Qiskit code in a Monaco editor, run it, and see your circuit visualized live. Get AI feedback on your submissions before you're stuck guessing.",
    icon: <CodeIcon />,
  },
  {
    delay: 0.41,
    tags: ['Theory + Code Together', 'Step-by-Step', 'Adaptive Pacing', 'Best for Beginners'],
    title: 'Guided Learning',
    body: 'The full experience — theory explanations, code you can run, and circuit diagrams, woven together in one guided path through each topic.',
    icon: <CompassIcon />,
  },
];

export default function ModeSelector() {
  return (
    <section style={{ position: 'relative', minHeight: '100vh', overflow: 'hidden', padding: '96px clamp(1rem, 4vw, 5rem) 48px' }}>
      <QuantumField count={70} />
      <div style={{ position: 'relative', zIndex: 10 }}>
        <RevealOnView delay={0}>
          <div style={{ fontSize: 14, color: 'rgba(255,255,255,0.8)', marginBottom: 24 }}>// Learning Modes</div>
          <h2
            style={{
              fontFamily: "'Instrument Serif', serif",
              fontStyle: 'italic',
              fontWeight: 400,
              fontSize: 'clamp(3.75rem, 7vw, 6rem)',
              lineHeight: 0.9,
              letterSpacing: '-3px',
              margin: 0,
            }}
          >
            Learn your way
          </h2>
        </RevealOnView>

        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: 24, marginTop: 64 }}>
          {MODES.map((mode) => (
            <ModeCard key={mode.title} {...mode} />
          ))}
        </div>
      </div>
    </section>
  );
}

function ModeCard({ delay, tags, title, body, icon }) {
  return (
    <RevealOnView
      delay={delay}
      className="liquid-glass mode-card"
      style={{ borderRadius: 20, padding: 24, minHeight: 360, display: 'flex', flexDirection: 'column' }}
    >
      <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', gap: 16 }}>
        <div className="liquid-glass" style={{ width: 44, height: 44, borderRadius: 12, display: 'flex', alignItems: 'center', justifyContent: 'center', flex: 'none' }}>
          {icon}
        </div>
        <div style={{ display: 'flex', flexWrap: 'wrap', justifyContent: 'flex-end', gap: 6, maxWidth: '70%' }}>
          {tags.map((tag) => (
            <span key={tag} className="liquid-glass" style={{ borderRadius: 9999, padding: '4px 12px', fontSize: 11, color: 'rgba(255,255,255,0.9)', whiteSpace: 'nowrap' }}>
              {tag}
            </span>
          ))}
        </div>
      </div>
      <div style={{ flex: 1 }} />
      <h3
        style={{
          fontFamily: "'Instrument Serif', serif",
          fontStyle: 'italic',
          fontWeight: 400,
          fontSize: 'clamp(1.875rem, 2.4vw, 2.25rem)',
          letterSpacing: '-1px',
          lineHeight: 1,
          margin: '24px 0 0',
        }}
      >
        {title}
      </h3>
      <p style={{ margin: '12px 0 0', fontSize: 14, color: 'rgba(255,255,255,0.9)', fontWeight: 300, lineHeight: 1.4, maxWidth: '32ch' }}>
        {body}
      </p>
      <a
        href="#"
        className="liquid-glass card-cta"
        style={{ alignSelf: 'flex-start', marginTop: 24, display: 'inline-flex', alignItems: 'center', gap: 6, borderRadius: 9999, padding: '8px 16px', fontSize: 14, color: '#fff', textDecoration: 'none' }}
      >
        Start →
      </a>
    </RevealOnView>
  );
}

function BookOpenIcon() {
  return (
    <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
      <path d="M12 7v14" />
      <path d="M3 18a1 1 0 0 1-1-1V4a1 1 0 0 1 1-1h5a4 4 0 0 1 4 4 4 4 0 0 1 4-4h5a1 1 0 0 1 1 1v13a1 1 0 0 1-1 1h-6a3 3 0 0 0-3 3 3 3 0 0 0-3-3z" />
    </svg>
  );
}

function CodeIcon() {
  return (
    <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
      <path d="m18 16 4-4-4-4" />
      <path d="m6 8-4 4 4 4" />
      <path d="m14.5 4-5 16" />
    </svg>
  );
}

function CompassIcon() {
  return (
    <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
      <circle cx="12" cy="12" r="10" />
      <polygon points="16.24 7.76 14.12 14.12 7.76 16.24 9.88 9.88 16.24 7.76" />
    </svg>
  );
}
