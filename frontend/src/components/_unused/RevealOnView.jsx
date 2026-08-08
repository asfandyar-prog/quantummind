import { useEffect, useRef, useState } from 'react';

/**
 * Wraps any element and reveals it with a blur + rise transition the first
 * time it's 10% visible in the viewport. Used for everything in the design
 * marked "data-blur" in the original spec: badges, CTAs, stat cards, mode
 * cards.
 */
export default function RevealOnView({
  children,
  delay = 0,
  distance = 20,
  as: Tag = 'div',
  style = {},
  className,
}) {
  const ref = useRef(null);
  const [shown, setShown] = useState(false);

  useEffect(() => {
    if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) {
      setShown(true);
      return;
    }
    const el = ref.current;
    if (!el) return;
    const observer = new IntersectionObserver(
      ([entry]) => {
        if (entry.isIntersecting) {
          setShown(true);
          observer.disconnect();
        }
      },
      { threshold: 0.1 }
    );
    observer.observe(el);
    return () => observer.disconnect();
  }, []);

  return (
    <Tag
      ref={ref}
      className={className}
      style={{
        ...style,
        opacity: shown ? 1 : 0,
        filter: shown ? 'none' : 'blur(10px)',
        transform: shown ? 'none' : `translateY(${distance}px)`,
        transition: `opacity 0.6s cubic-bezier(0.33,1,0.68,1) ${delay}s, filter 0.6s cubic-bezier(0.33,1,0.68,1) ${delay}s, transform 0.6s cubic-bezier(0.33,1,0.68,1) ${delay}s`,
      }}
    >
      {children}
    </Tag>
  );
}
