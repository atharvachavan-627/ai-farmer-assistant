export default function Spinner({ size = 20, label }) {
  return (
    <span className="spinner" role="status" aria-live="polite">
      <span className="spinner__ring" style={{ width: size, height: size }} aria-hidden="true" />
      {label ? <span className="visually-hidden">{label}</span> : null}
    </span>
  );
}
