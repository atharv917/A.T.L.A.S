import Panel from './Panel';

const ORDER = ['cooling', 'combustion', 'induction', 'lubrication'];

function cls(v) { return v >= 0.85 ? 'ok' : v >= 0.6 ? 'warn' : 'crit'; }

/**
 * Panel #6 — component health as bars, with the OVERALL number explicitly the
 * MINIMUM of the components and "limited by: X" next to it. These are never
 * silently averaged.
 */
export default function HealthPanel({ data, source }) {
  const health = data?.twin ? data?.health : null;
  if (!health) {
    return (
      <Panel title="Component Health" stepNo={6} source={source}>
        <div className="mono-caption">Twin unavailable — health indices not computed.</div>
      </Panel>
    );
  }
  const comps = health.components ?? {};
  const entries = ORDER.filter((k) => comps[k]).map((k) => [k, comps[k]]);
  const min = Math.min(...entries.map(([, c]) => c.index));
  const limiting = health.limitedBy ?? entries.sort((a, b) => a[1].index - b[1].index)[0]?.[0];

  return (
    <Panel title="Component Health" stepNo={6} source={source}
      right={<span className={`pill ${cls(min)}`}>OVERALL {min.toFixed(2)} = MIN</span>}>
      <div style={{ display: 'flex', alignItems: 'baseline', gap: 10, marginBottom: 10 }}>
        <span className={`num big status-${cls(min)}`}>{min.toFixed(2)}</span>
        <span className="mono-caption">
          overall = <b>min</b>(components), <b>not</b> an average · limited by:{' '}
          <b style={{ color: 'var(--warn)' }}>{limiting}</b>
        </span>
      </div>
      {entries.map(([k, c]) => (
        <div key={k} style={{ marginBottom: 10 }}>
          <div style={{ display: 'flex', justifyContent: 'space-between' }}>
            <span style={{ color: k === limiting ? 'var(--warn)' : 'var(--text-dim)' }}>
              {k}{k === limiting ? ' ◄ limiting' : ''}
            </span>
            <span className="num">
              {c.index.toFixed(2)}
              <span style={{ color: 'var(--text-faint)' }}> · conf {c.confidence?.toFixed?.(2) ?? '—'}</span>
            </span>
          </div>
          <div className="bar-track" style={{ marginTop: 3 }}>
            <div className={`bar-fill ${cls(c.index)}`} style={{ width: `${c.index * 100}%` }} />
            <div className="bar-marker" style={{ left: '85%' }} title="0.85 nominal band" />
          </div>
        </div>
      ))}
    </Panel>
  );
}
