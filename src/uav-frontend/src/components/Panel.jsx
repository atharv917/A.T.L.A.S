import DataSourceBadge from './DataSourceBadge';

/**
 * Shared panel chrome. Every panel gets the DATA SOURCE badge in its header for
 * free — a component cannot opt out, which is the point.
 */
export default function Panel({ title, stepNo, source = 'SIMULATED', right, className = '', children }) {
  return (
    <section className={`panel ${className}`}>
      <header className="panel-head">
        {stepNo != null && <span className="step-no">#{stepNo}</span>}
        <span className="title">{title}</span>
        <span className="spacer" />
        {right}
        <DataSourceBadge source={source} />
      </header>
      <div className="panel-body">{children}</div>
    </section>
  );
}
