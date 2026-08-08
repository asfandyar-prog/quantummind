import Hero from './components/Hero';
import ModeSelector from './components/ModeSelector';
import './index.css';

export default function App() {
  return (
    <div style={{ background: '#050507', color: '#fff', fontFamily: "'Barlow', sans-serif", position: 'relative', overflowX: 'hidden' }}>
      <Hero />
      <ModeSelector />
    </div>
  );
}
