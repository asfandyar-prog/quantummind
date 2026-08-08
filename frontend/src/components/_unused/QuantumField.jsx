import { useEffect, useRef } from 'react';

function hexToRgba(hex, a) {
  let h = hex.replace('#', '');
  if (h.length === 3) h = h.split('').map((c) => c + c).join('');
  const n = parseInt(h, 16);
  return `rgba(${(n >> 16) & 255},${(n >> 8) & 255},${n & 255},${a})`;
}

/**
 * Animated background of drifting "qubit" points connected by faint lines
 * when close together. Replaces stock video backgrounds — free, on-theme,
 * and respects prefers-reduced-motion.
 */
export default function QuantumField({ count = 34, accentColor = '#7C5CFC', speed = 1 }) {
  const canvasRef = useRef(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    const reduced = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    const accent = hexToRgba(accentColor, 0.6);
    let W = 0;
    let H = 0;
    let dpr = 1;
    const pts = [];

    const resize = () => {
      const r = canvas.getBoundingClientRect();
      dpr = Math.min(window.devicePixelRatio || 1, 2);
      W = r.width;
      H = r.height;
      canvas.width = Math.max(1, Math.floor(W * dpr));
      canvas.height = Math.max(1, Math.floor(H * dpr));
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
      if (pts.length === 0 && W > 0 && H > 0) {
        for (let i = 0; i < count; i++) {
          pts.push({
            x: Math.random() * W,
            y: Math.random() * H,
            vx: (Math.random() - 0.5) * 0.28 * speed,
            vy: (Math.random() - 0.5) * 0.28 * speed,
            accent: Math.random() < 0.12,
          });
        }
      }
    };
    resize();

    const maxD = 150;
    let rafId = null;

    const step = () => {
      ctx.clearRect(0, 0, W, H);

      for (const p of pts) {
        p.x += p.vx;
        p.y += p.vy;
        if (p.x < -6) p.x = W + 6;
        else if (p.x > W + 6) p.x = -6;
        if (p.y < -6) p.y = H + 6;
        else if (p.y > H + 6) p.y = -6;
      }

      for (let i = 0; i < pts.length; i++) {
        for (let j = i + 1; j < pts.length; j++) {
          const a = pts[i];
          const b = pts[j];
          const dx = a.x - b.x;
          const dy = a.y - b.y;
          const d = Math.sqrt(dx * dx + dy * dy);
          if (d < maxD) {
            ctx.strokeStyle = `rgba(255,255,255,${(1 - d / maxD) * 0.22})`;
            ctx.lineWidth = 1;
            ctx.beginPath();
            ctx.moveTo(a.x, a.y);
            ctx.lineTo(b.x, b.y);
            ctx.stroke();
          }
        }
      }

      for (const p of pts) {
        ctx.beginPath();
        ctx.arc(p.x, p.y, p.accent ? 2.4 : 1.5, 0, Math.PI * 2);
        ctx.fillStyle = p.accent ? accent : 'rgba(255,255,255,0.5)';
        ctx.fill();
      }

      if (!reduced) rafId = requestAnimationFrame(step);
    };
    step();

    const onResize = () => resize();
    window.addEventListener('resize', onResize);

    return () => {
      if (rafId) cancelAnimationFrame(rafId);
      window.removeEventListener('resize', onResize);
    };
  }, [count, accentColor, speed]);

  return (
    <canvas
      ref={canvasRef}
      style={{ position: 'absolute', inset: 0, width: '100%', height: '100%', zIndex: 0, display: 'block' }}
    />
  );
}
