// Reusable skeleton primitives — pulse animation, matches Luméra design system.
// Place at: frontend/src/components/Skeleton.tsx

const base = 'animate-pulse rounded-xl bg-gray-200';

export const Sk = {
  Box: ({ className = '' }: { className?: string }) => (
    <div className={`${base} ${className}`} />
  ),
  Line: ({ className = '' }: { className?: string }) => (
    <div className={`${base} h-4 ${className}`} />
  ),
  Circle: ({ className = '' }: { className?: string }) => (
    <div className={`animate-pulse rounded-full bg-gray-200 ${className}`} />
  ),
  Card: ({ className = '', children }: { className?: string; children: React.ReactNode }) => (
    <div className={`bg-white/90 backdrop-blur-sm rounded-xl shadow-sm border border-white/60 ${className}`}>
      {children}
    </div>
  ),
};

export default Sk;