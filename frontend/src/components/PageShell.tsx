// src/components/PageShell.tsx
// Drop-in wrapper that gives every page the shared background + consistent padding.
// Usage: <PageShell>…page content…</PageShell>

const PageShell = ({ children }: { children: React.ReactNode }) => (
  <div className="relative min-h-[calc(100vh-4rem)] py-8 px-4 overflow-hidden"
    style={{ background: '#f5f3ff' }}>

    {/* Subtle dot-grid background — lightweight, works in both light/dark */}
    <svg
      aria-hidden="true"
      className="pointer-events-none absolute inset-0 w-full h-full"
      xmlns="http://www.w3.org/2000/svg"
      style={{ opacity: 0.45 }}
    >
      <defs>
        <pattern id="dots" x="0" y="0" width="24" height="24" patternUnits="userSpaceOnUse">
          <circle cx="1.5" cy="1.5" r="1.5" fill="#a78bfa" />
        </pattern>
      </defs>
      <rect width="100%" height="100%" fill="url(#dots)" />
    </svg>

    {/* Top-left accent blob — pure CSS, no gradient render flash */}
    <div
      aria-hidden="true"
      className="pointer-events-none absolute -top-32 -left-32 w-96 h-96 rounded-full"
      style={{ background: '#ede9fe', filter: 'blur(80px)', opacity: 0.6 }}
    />
    {/* Bottom-right accent blob */}
    <div
      aria-hidden="true"
      className="pointer-events-none absolute -bottom-32 -right-32 w-80 h-80 rounded-full"
      style={{ background: '#e0e7ff', filter: 'blur(80px)', opacity: 0.5 }}
    />

    <div className="relative z-10">{children}</div>
  </div>
);

export default PageShell;