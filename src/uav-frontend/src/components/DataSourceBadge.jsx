/**
 * DATA SOURCE badge. Rendered by every Panel header and in the top bar. There
 * is deliberately no way to dismiss or hover-collapse it — it is a structural
 * part of the layout. This is the single most important visual element in the
 * UI (honesty: every number on screen is about a simulator).
 */
export default function DataSourceBadge({ source = 'SIMULATED', size }) {
  return (
    <span className={`ds-badge${size === 'lg' ? ' lg' : ''}`} title="All values are model output, not real engine data">
      <span className="dot" />
      DATA SOURCE: {String(source).toUpperCase()}
    </span>
  );
}
