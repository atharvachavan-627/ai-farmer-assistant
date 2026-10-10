import { Check } from 'lucide-react';

export default function BulletList({ items }) {
  if (!items?.length) return null;
  return (
    <ul className="bullets">
      {items.map((item, i) => (
        <li key={i}>
          <Check size={16} aria-hidden="true" />
          <span>{item}</span>
        </li>
      ))}
    </ul>
  );
}
