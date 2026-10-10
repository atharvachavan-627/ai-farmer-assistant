import { useId } from 'react';

export default function TextField({ label, error, hint, children, inputRef, ...inputProps }) {
  const id = useId();
  const errId = `${id}-err`;
  const hintId = `${id}-hint`;
  const describedBy = [error ? errId : null, hint ? hintId : null].filter(Boolean).join(' ') || undefined;
  return (
    <div className={`field ${error ? 'field--error' : ''}`}>
      <label htmlFor={id} className="field__label">
        {label}
      </label>
      <div className="field__control">
        <input
          id={id}
          ref={inputRef}
          className="field__input"
          aria-invalid={error ? 'true' : 'false'}
          aria-describedby={describedBy}
          {...inputProps}
        />
        {children}
      </div>
      {hint ? (
        <p id={hintId} className="field__hint">
          {hint}
        </p>
      ) : null}
      {error ? (
        <p id={errId} className="field__error" role="alert">
          {error}
        </p>
      ) : null}
    </div>
  );
}
