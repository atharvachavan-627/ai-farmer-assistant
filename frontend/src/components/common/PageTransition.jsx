import { motion, useReducedMotion } from 'framer-motion';

export default function PageTransition({ children, className = '' }) {
  const reduce = useReducedMotion();
  return (
    <motion.div
      className={className}
      initial={reduce ? false : { opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: reduce ? 0 : 0.28, ease: 'easeOut' }}
    >
      {children}
    </motion.div>
  );
}
