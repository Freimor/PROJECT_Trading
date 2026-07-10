type IconProps = { className?: string };

const base = "nav-icon";

export function IconOverview({ className }: IconProps) {
  return (
    <svg className={`${base} ${className ?? ""}`} viewBox="0 0 24 24" aria-hidden>
      <rect x="3" y="3" width="8" height="8" rx="1.5" fill="currentColor" opacity="0.9" />
      <rect x="13" y="3" width="8" height="5" rx="1.5" fill="currentColor" opacity="0.5" />
      <rect x="13" y="10" width="8" height="11" rx="1.5" fill="currentColor" opacity="0.7" />
      <rect x="3" y="13" width="8" height="8" rx="1.5" fill="currentColor" opacity="0.5" />
    </svg>
  );
}

export function IconCrypto({ className }: IconProps) {
  return (
    <svg className={`${base} ${className ?? ""}`} viewBox="0 0 24 24" aria-hidden>
      <circle cx="12" cy="12" r="9" fill="none" stroke="currentColor" strokeWidth="1.75" />
      <path
        d="M10 7h4a2 2 0 0 1 0 4h-3v6M10 11h3"
        fill="none"
        stroke="currentColor"
        strokeWidth="1.75"
        strokeLinecap="round"
      />
    </svg>
  );
}

export function IconMoex({ className }: IconProps) {
  return (
    <svg className={`${base} ${className ?? ""}`} viewBox="0 0 24 24" aria-hidden>
      <path
        d="M4 18V8l4 10 4-6 4 6 4-10v10"
        fill="none"
        stroke="currentColor"
        strokeWidth="1.75"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
}

export function IconNews({ className }: IconProps) {
  return (
    <svg className={`${base} ${className ?? ""}`} viewBox="0 0 24 24" aria-hidden>
      <rect x="4" y="5" width="16" height="14" rx="2" fill="none" stroke="currentColor" strokeWidth="1.75" />
      <path d="M8 9h8M8 13h5" stroke="currentColor" strokeWidth="1.75" strokeLinecap="round" />
    </svg>
  );
}

export function IconEvents({ className }: IconProps) {
  return (
    <svg className={`${base} ${className ?? ""}`} viewBox="0 0 24 24" aria-hidden>
      <rect x="4" y="5" width="16" height="15" rx="2" fill="none" stroke="currentColor" strokeWidth="1.75" />
      <path d="M8 3v4M16 3v4M4 10h16" stroke="currentColor" strokeWidth="1.75" strokeLinecap="round" />
    </svg>
  );
}

export function IconLlm({ className }: IconProps) {
  return (
    <svg className={`${base} ${className ?? ""}`} viewBox="0 0 24 24" aria-hidden>
      <circle cx="12" cy="8" r="3.5" fill="none" stroke="currentColor" strokeWidth="1.75" />
      <path
        d="M6 18c0-3.3 2.7-6 6-6s6 2.7 6 6"
        fill="none"
        stroke="currentColor"
        strokeWidth="1.75"
        strokeLinecap="round"
      />
      <circle cx="18" cy="7" r="1.25" fill="currentColor" />
    </svg>
  );
}

export function IconBenchmark({ className }: IconProps) {
  return (
    <svg className={`${base} ${className ?? ""}`} viewBox="0 0 24 24" aria-hidden>
      <path
        d="M5 19V11M10 19V7M15 19V13M20 19V5"
        stroke="currentColor"
        strokeWidth="2"
        strokeLinecap="round"
      />
    </svg>
  );
}

export function IconPaper({ className }: IconProps) {
  return (
    <svg className={`${base} ${className ?? ""}`} viewBox="0 0 24 24" aria-hidden>
      <path
        d="M8 6h8l4 4v10a2 2 0 0 1-2 2H8a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2z"
        fill="none"
        stroke="currentColor"
        strokeWidth="1.75"
        strokeLinejoin="round"
      />
      <path d="M16 6v4h4M10 13h6M10 17h4" stroke="currentColor" strokeWidth="1.75" strokeLinecap="round" />
    </svg>
  );
}

export function IconResearch({ className }: IconProps) {
  return (
    <svg className={`${base} ${className ?? ""}`} viewBox="0 0 24 24" aria-hidden>
      <path
        d="M6 4h9l3 3v13H6V4z"
        fill="none"
        stroke="currentColor"
        strokeWidth="1.75"
        strokeLinejoin="round"
      />
      <path d="M9 12h6M9 16h4" stroke="currentColor" strokeWidth="1.75" strokeLinecap="round" />
    </svg>
  );
}

export function IconWorkflows({ className }: IconProps) {
  return (
    <svg className={`${base} ${className ?? ""}`} viewBox="0 0 24 24" aria-hidden>
      <circle cx="6" cy="6" r="2.25" fill="currentColor" />
      <circle cx="18" cy="6" r="2.25" fill="currentColor" />
      <circle cx="12" cy="18" r="2.25" fill="currentColor" />
      <path
        d="M8 6h8M7.5 7.5L11 16M16.5 7.5L13 16"
        stroke="currentColor"
        strokeWidth="1.5"
        strokeLinecap="round"
      />
    </svg>
  );
}

export function IconControl({ className }: IconProps) {
  return (
    <svg className={`${base} ${className ?? ""}`} viewBox="0 0 24 24" aria-hidden>
      <path
        d="M12 3v3M12 18v3M3 12h3M18 12h3M6.3 6.3l2.1 2.1M15.6 15.6l2.1 2.1M6.3 17.7l2.1-2.1M15.6 8.4l2.1-2.1"
        stroke="currentColor"
        strokeWidth="1.75"
        strokeLinecap="round"
      />
      <circle cx="12" cy="12" r="3.5" fill="none" stroke="currentColor" strokeWidth="1.75" />
    </svg>
  );
}
