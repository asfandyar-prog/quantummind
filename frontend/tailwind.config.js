/** @type {import('tailwindcss').Config} */
export default {
  content: [
    './index.html',
    './src/**/*.{js,jsx}',
  ],
  theme: {
    extend: {
      // ── APPLE-STYLE LIGHT DESIGN SYSTEM ─────────────────
      colors: {
        qm: {
          // Backgrounds — layered off-whites like macOS
          bg:       '#F2F2F7',   // iOS system background (light gray)
          surface:  '#FFFFFF',   // card / panel surface (pure white)
          surface2: '#F9F9FB',   // slightly lifted surface
          sidebar:  '#F7F7FA',   // sidebar tint

          // Borders — ultra-subtle like macOS
          border:   'rgba(0,0,0,0.08)',
          border2:  'rgba(0,122,255,0.25)',

          // Apple Blue system color — primary accent
          accent:   '#007AFF',
          // Quantum cyan — secondary accent for circuit elements
          accent2:  '#32ADE6',
          // Indigo — guided mode / concept tags
          accent3:  '#5856D6',

          // Text — iOS text hierarchy
          text:     '#1C1C1E',   // primary (near black)
          secondary:'#3C3C43',   // secondary labels
          muted:    '#6C6C70',   // tertiary labels
          dim:      '#AEAEB2',   // quaternary / placeholder
        },
        theory:   { DEFAULT: '#007AFF' },
        practice: { DEFAULT: '#32ADE6' },
        guided:   { DEFAULT: '#5856D6' },
      },

      // ── FONTS ────────────────────────────────────────────
      fontFamily: {
        display: ['-apple-system', 'SF Pro Display', 'Inter', 'sans-serif'],
        mono:    ['SF Mono', 'ui-monospace', 'Menlo', 'monospace'],
        body:    ['-apple-system', 'SF Pro Text', 'Inter', 'sans-serif'],
      },

      // ── ANIMATIONS ───────────────────────────────────────
      keyframes: {
        'fade-up': {
          '0%':   { opacity: '0', transform: 'translateY(14px)' },
          '100%': { opacity: '1', transform: 'translateY(0)'    },
        },
        'fade-in': {
          '0%':   { opacity: '0' },
          '100%': { opacity: '1' },
        },
        'scale-in': {
          '0%':   { opacity: '0', transform: 'scale(0.96)' },
          '100%': { opacity: '1', transform: 'scale(1)'    },
        },
        'typing': {
          '0%, 100%': { transform: 'translateY(0)',    opacity: '0.35' },
          '50%':      { transform: 'translateY(-3px)', opacity: '1'   },
        },
        'bar-load': {
          '0%':   { width: '0%'   },
          '100%': { width: '100%' },
        },
        'atom-spin': {
          '0%':   { transform: 'rotate(0deg)'   },
          '100%': { transform: 'rotate(360deg)' },
        },
        'pulse-ring': {
          '0%, 100%': { opacity: '0.6', transform: 'scale(1)'    },
          '50%':      { opacity: '1',   transform: 'scale(1.06)' },
        },
      },
      animation: {
        'fade-up':    'fade-up 0.45s ease forwards',
        'fade-in':    'fade-in 0.35s ease forwards',
        'scale-in':   'scale-in 0.4s ease forwards',
        'typing':     'typing 1.2s ease-in-out infinite',
        'bar-load':   'bar-load 1.8s ease forwards',
        'atom-spin':  'atom-spin 8s linear infinite',
        'pulse-ring': 'pulse-ring 3s ease-in-out infinite',
      },

      // ── SPACING + RADIUS ─────────────────────────────────
      borderRadius: {
        'qm':    '12px',   // cards, inputs
        'qm-lg': '20px',   // mode cards, modals
        'qm-xl': '28px',   // splash hero card
      },

      // ── SHADOWS — Apple-style ─────────────────────────────
      boxShadow: {
        'qm-sm':   '0 1px 3px rgba(0,0,0,0.08), 0 1px 2px rgba(0,0,0,0.05)',
        'qm-md':   '0 4px 16px rgba(0,0,0,0.08), 0 1px 4px rgba(0,0,0,0.05)',
        'qm-lg':   '0 8px 32px rgba(0,0,0,0.10), 0 2px 8px rgba(0,0,0,0.06)',
        'qm-blue': '0 4px 16px rgba(0,122,255,0.20)',
      },

      backdropBlur: {
        'qm': '20px',
      },

      fontSize: {
        '2xs': ['10px', { lineHeight: '14px' }],
        'xs':  ['12px', { lineHeight: '16px' }],
        'sm':  ['13px', { lineHeight: '18px' }],
        'base':['15px', { lineHeight: '22px' }],
        'md':  ['16px', { lineHeight: '24px' }],
        'lg':  ['18px', { lineHeight: '26px' }],
        'xl':  ['20px', { lineHeight: '28px' }],
        '2xl': ['24px', { lineHeight: '32px' }],
        '3xl': ['30px', { lineHeight: '38px' }],
        '4xl': ['36px', { lineHeight: '44px' }],
        '5xl': ['48px', { lineHeight: '56px' }],
      },
    },
  },
  plugins: [],
}