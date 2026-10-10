/** Always-visible notice while UI preview mode is active. */
export default function PreviewBanner() {
  return (
    <div
      role="status"
      style={{
        position: 'fixed',
        bottom: 0,
        left: 0,
        right: 0,
        zIndex: 1000,
        background: '#92400e',
        color: '#fff',
        textAlign: 'center',
        padding: '6px 12px',
        fontSize: '0.8rem',
        fontWeight: 600,
      }}
    >
      UI PREVIEW MODE: no backend connected. Accounts, predictions and history are simulated sample data, not real results.
    </div>
  );
}
