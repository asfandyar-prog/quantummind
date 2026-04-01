import clsx from 'clsx'

/**
 * Button — reusable button with variant system
 *
 * Variants:
 *   primary   — solid accent blue, main CTAs
 *   ghost     — transparent with border, secondary actions
 *   icon      — square icon button (topbar, toolbar)
 *
 * Usage:
 *   <Button variant="primary" onClick={handleSend}>Send</Button>
 *   <Button variant="ghost" size="sm">Cancel</Button>
 *   <Button variant="icon" title="Settings">⚙</Button>
 */
export default function Button({
  children,
  variant = 'primary',
  size = 'md',
  className,
  disabled,
  onClick,
  title,
  type = 'button',
}) {
  const base = clsx(
    // Base styles shared by all variants
    'inline-flex items-center justify-center',
    'font-mono tracking-wide',
    'transition-all duration-200',
    'cursor-pointer select-none',
    'disabled:opacity-40 disabled:cursor-not-allowed',
    'focus:outline-none focus-visible:ring-2 focus-visible:ring-qm-accent focus-visible:ring-offset-2 focus-visible:ring-offset-qm-bg',
  )

  const variants = {
    primary: clsx(
      'bg-qm-accent text-qm-bg',
      'hover:bg-qm-accent2 hover:scale-[1.02]',
      'active:scale-[0.98]',
      'rounded-[10px]',
    ),
    ghost: clsx(
      'bg-transparent text-qm-muted',
      'border border-[rgba(99,179,237,0.12)]',
      'hover:border-[rgba(99,179,237,0.22)] hover:text-qm-text',
      'active:scale-[0.98]',
      'rounded-[10px]',
    ),
    icon: clsx(
      'bg-transparent text-qm-muted',
      'border border-[rgba(99,179,237,0.12)]',
      'hover:border-qm-accent hover:text-qm-accent',
      'rounded-[8px]',
      'aspect-square',
    ),
  }

  const sizes = {
    sm:   'px-3 py-1.5 text-[10px]',
    md:   'px-4 py-2 text-[11px]',
    lg:   'px-6 py-3 text-[12px]',
    icon: 'w-[30px] h-[30px] text-sm',
  }

  // Icon variant always uses icon size
  const resolvedSize = variant === 'icon' ? 'icon' : size

  return (
    <button
      type={type}
      disabled={disabled}
      onClick={onClick}
      title={title}
      className={clsx(base, variants[variant], sizes[resolvedSize], className)}
    >
      {children}
    </button>
  )
}