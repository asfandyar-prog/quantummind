import QuantumField from './QuantumField';
import BlurText from './BlurText';
import RevealOnView from './RevealOnView';

export default function Hero() {
  return (
    <>
      <nav
        style={{
          position: 'fixed',
          top: 16,
          left: 0,
          right: 0,
          zIndex: 50,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          padding: '0 clamp(1rem, 4vw, 4rem)',
        }}
      >
        <div
          className="liquid-glass"
          style={{
            width: 48,
            height: 48,
            borderRadius: 9999,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            fontFamily: "'Instrument Serif', serif",
            fontStyle: 'italic',
            fontSize: 22,
          }}
        >
          ⚛
        </div>

        <div
          className="liquid-glass nav-center"
          style={{ display: 'flex', alignItems: 'center', gap: 2, padding: 6, borderRadius: 9999 }}
        >
          {['Theory', 'Practice', 'Guided', 'Course', 'About'].map((label) => (
            <a
              key={label}
              href="#"
              className="nav-link"
              style={{
                padding: '8px 12px',
                fontSize: 14,
                fontWeight: 500,
                color: 'rgba(255,255,255,0.9)',
                textDecoration: 'none',
                borderRadius: 9999,
              }}
            >
              {label}
            </a>
          ))}
          <a
            href="#"
            style={{
              display: 'inline-flex',
              alignItems: 'center',
              gap: 6,
              background: '#fff',
              color: '#000',
              padding: '8px 14px',
              borderRadius: 9999,
              fontSize: 14,
              fontWeight: 600,
              whiteSpace: 'nowrap',
              textDecoration: 'none',
              marginLeft: 6,
            }}
          >
            Start Learning
            <ArrowUpRight />
          </a>
        </div>

        <div style={{ width: 48, height: 48 }} />
      </nav>

      <section style={{ position: 'relative', minHeight: '100vh', overflow: 'hidden' }}>
        <QuantumField count={34} />
        <div
          style={{
            position: 'relative',
            zIndex: 10,
            minHeight: '100vh',
            display: 'flex',
            flexDirection: 'column',
            padding: '0 16px',
          }}
        >
          <div
            style={{
              flex: 1,
              display: 'flex',
              flexDirection: 'column',
              alignItems: 'center',
              justifyContent: 'center',
              textAlign: 'center',
              paddingTop: 96,
            }}
          >
            <RevealOnView
              delay={0.4}
              className="liquid-glass"
              style={{ display: 'inline-flex', alignItems: 'center', gap: 10, borderRadius: 9999, padding: '5px 14px 5px 5px' }}
            >
              <span style={{ background: '#fff', color: '#000', borderRadius: 9999, padding: '4px 12px', fontSize: 12, fontWeight: 600 }}>
                New
              </span>
              <span style={{ fontSize: 14, color: 'rgba(255,255,255,0.9)' }}>Multi-Agent AI Now Live</span>
            </RevealOnView>

            <BlurText
              text="Where Quantum Theory Meets Practice"
              style={{
                fontFamily: "'Instrument Serif', serif",
                fontStyle: 'italic',
                fontWeight: 400,
                fontSize: 'clamp(3.75rem, 7vw, 5.5rem)',
                lineHeight: 0.8,
                letterSpacing: '-4px',
                color: '#fff',
                maxWidth: '46rem',
                marginTop: 24,
              }}
            />

            <RevealOnView
              as="p"
              delay={0.8}
              style={{
                marginTop: 20,
                fontSize: 'clamp(0.95rem, 1.2vw, 1.05rem)',
                color: '#fff',
                maxWidth: '42rem',
                fontWeight: 300,
                lineHeight: 1.35,
              }}
            >
              An AI-powered learning platform that teaches quantum computing through real conversation,
              real Qiskit code, and real circuit execution — not just slides.
            </RevealOnView>

            <RevealOnView delay={1.1} style={{ display: 'flex', alignItems: 'center', gap: 24, marginTop: 28 }}>
              <a
                href="#"
                className="liquid-glass-strong btn-primary"
                style={{
                  display: 'inline-flex',
                  alignItems: 'center',
                  gap: 8,
                  borderRadius: 9999,
                  padding: '10px 20px',
                  fontSize: 14,
                  fontWeight: 500,
                  color: '#fff',
                  textDecoration: 'none',
                }}
              >
                Start Learning
                <ArrowUpRight size={20} />
              </a>
              <a
                href="#"
                className="btn-ghost"
                style={{ display: 'inline-flex', alignItems: 'center', gap: 8, fontSize: 14, color: '#fff', textDecoration: 'none', opacity: 0.9 }}
              >
                Watch Demo
                <PlayIcon />
              </a>
            </RevealOnView>

            <RevealOnView delay={1.3} style={{ display: 'flex', gap: 16, marginTop: 36, flexWrap: 'wrap', justifyContent: 'center' }}>
              <StatCard icon={<GraduationCapIcon />} value="60+" label="Students Taught" />
              <StatCard icon={<LayersIcon />} value="3" label="Learning Modes" />
            </RevealOnView>
          </div>

          <RevealOnView
            delay={1.4}
            style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 18, paddingBottom: 32 }}
          >
            <span className="liquid-glass" style={{ borderRadius: 9999, padding: '5px 14px', fontSize: 12, fontWeight: 500 }}>
              Built on the tools real quantum teams use
            </span>
            <div
              style={{
                display: 'flex',
                flexWrap: 'wrap',
                justifyContent: 'center',
                alignItems: 'center',
                gap: 'clamp(1.5rem, 4vw, 3.5rem)',
                fontFamily: "'Instrument Serif', serif",
                fontStyle: 'italic',
                fontSize: 'clamp(1.5rem, 2.6vw, 1.875rem)',
                letterSpacing: '-0.5px',
              }}
            >
              {['Qiskit', 'LangGraph', 'FastAPI', 'ChromaDB', 'Groq'].map((name) => (
                <span key={name}>{name}</span>
              ))}
            </div>
          </RevealOnView>
        </div>
      </section>
    </>
  );
}

function StatCard({ icon, value, label }) {
  return (
    <div className="liquid-glass" style={{ padding: 20, width: 220, borderRadius: 20, textAlign: 'left', display: 'flex', flexDirection: 'column' }}>
      <div style={{ width: 28, height: 28 }}>{icon}</div>
      <div style={{ marginTop: 16, fontFamily: "'Instrument Serif', serif", fontStyle: 'italic', fontSize: '2.25rem', letterSpacing: '-1px', lineHeight: 1 }}>
        {value}
      </div>
      <div style={{ fontSize: 12, fontWeight: 300, marginTop: 8 }}>{label}</div>
    </div>
  );
}

function ArrowUpRight({ size = 16 }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
      <path d="M7 7h10v10" />
      <path d="M7 17 17 7" />
    </svg>
  );
}

function PlayIcon() {
  return (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor">
      <polygon points="6 3 20 12 6 21 6 3" />
    </svg>
  );
}

function GraduationCapIcon() {
  return (
    <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
      <path d="M22 10v6M2 10l10-5 10 5-10 5z" />
      <path d="M6 12v5c3 3 9 3 12 0v-5" />
    </svg>
  );
}

function LayersIcon() {
  return (
    <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
      <path d="m12 2 9 5-9 5-9-5 9-5z" />
      <path d="m3 12 9 5 9-5" />
      <path d="m3 17 9 5 9-5" />
    </svg>
  );
}
