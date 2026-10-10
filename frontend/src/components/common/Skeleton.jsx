export function Skeleton({ height = 16, width = '100%', radius = 8 }) {
  return <span className="skeleton" style={{ height, width, borderRadius: radius }} aria-hidden="true" />;
}

export function CardSkeleton() {
  return (
    <div className="card card--skeleton" aria-hidden="true">
      <Skeleton height={140} radius={12} />
      <Skeleton height={18} width="70%" />
      <Skeleton height={14} width="45%" />
      <Skeleton height={14} />
    </div>
  );
}

export function SkeletonGrid({ count = 6, label }) {
  return (
    <div className="grid grid--cards" role="status" aria-live="polite" aria-busy="true">
      {label ? <span className="visually-hidden">{label}</span> : null}
      {Array.from({ length: count }, (_, i) => (
        <CardSkeleton key={i} />
      ))}
    </div>
  );
}
