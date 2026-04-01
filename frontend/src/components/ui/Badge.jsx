import clsx from 'clsx'

/**
 * Badge — small label pill used for mode tags, status indicators
 *
 * Usage:
 *   <Badge color="theory">Concepts</Badge>
 *   <Badge color="practice">Qiskit</Badge>
 *   <Badge color="guided">Theory</Badge>
 *   <Badge>Default</Badge>
 */
export default function Badge({ children, color = 'default', className }) {
  const colors = {
    default:  'border-[rgba(99,179,237,0.3)]  text-qm-accent',
    theory:   'border-[rgba(99,179,237,0.3)]  text-qm-accent',
    practice: 'border-[rgba(118,228,247,0.3)] text-qm-accent2',
    guided:   'border-[rgba(183,148,244,0.3)] text-qm-accent3',
    success:  'border-[rgba(104,211,145,0.3)] text-green-400',
    warning:  'border-[rgba(246,173,85,0.3)]  text-amber-400',
  }

  return (
    <span
      className={clsx(
        'inline-flex items-center',
        'font-mono text-[10px] tracking-[0.5px]',
        'px-2 py-[3px] rounded-[4px]',
        'border',
        'opacity-70',
        colors[color] ?? colors.default,
        className,
      )}
    >
      {children}
    </span>
  )
}