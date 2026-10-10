import { motion, useReducedMotion } from 'framer-motion';

export default function EmptyState({ icon: Icon, title, body, action }) {
  const reduce = useReducedMotion();
  return (
    <motion.div
      className="state"
      initial={reduce ? false : { opacity: 0, scale: 0.97 }}
      animate={{ opacity: 1, scale: 1 }}
      transition={{ duration: reduce ? 0 : 0.3 }}
    >
      {Icon ? (
        <span className="state__icon" aria-hidden="true">
          <Icon size={28} />
        </span>
      ) : null}
      <h2 className="state__title">{title}</h2>
      {body ? <p className="state__body">{body}</p> : null}
      {action || null}
    </motion.div>
  );
}
