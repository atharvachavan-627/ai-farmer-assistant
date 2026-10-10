export default function SectionCard({ icon: Icon, title, children, tone = '' }) {
  return (
    <section className={`card section-card ${tone ? `section-card--${tone}` : ''}`}>
      <h3 className="section-card__title">
        {Icon ? <Icon size={18} aria-hidden="true" /> : null}
        {title}
      </h3>
      {children}
    </section>
  );
}
