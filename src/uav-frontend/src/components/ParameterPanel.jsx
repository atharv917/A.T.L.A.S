import Panel from './Panel';

const META = {
  volumetric_efficiency: { label: 'Volumetric efficiency', unit: '', range: [0.7, 1.0] },
  cooling_factor: { label: 'Cooling factor', unit: '', range: [0.7, 1.1] },
  boost_capability: { label: 'Boost capability', unit: '', range: [0.7, 1.1] },
  oil_system_health: { label: 'Oil-system health', unit: '', range: [0.7, 1.05] },
};

function Gauge({ value, sigma, nominal, range }) {
  const [lo, hi] = range;
  const pct = (x) => `${((x - lo) / (hi - lo)) * 100}%`;
  const dev = nominal ? Math.abs(value - nominal) / nominal : 0;
  const cls = dev > 0.05 ? 'crit' : dev > 0.02 ? 'warn' : 'ok';
  return (
    <div className="bar-track" style={{ height: 18, margin: '4px 0 2px' }}>
      {/* ± sigma band */}
      {sigma != null && (
        <div
          style={{
            position: 'absolute', top: 0, bottom: 0, background: 'var(--accent-dim)',
            opacity: 0.35, left: pct(value - sigma), width: `calc(${pct(value + sigma)} - ${pct(value - sigma)})`,
          }}
        />
      )}
      <div className={`bar-fill ${cls}`} style={{ width: pct(value), opacity: 0.55 }} />
      {nominal != null && <div className="bar-marker" style={{ left: pct(nominal) }} title={`nominal ${nominal}`} />}
      <div
        style={{
          position: 'absolute', top: -3, bottom: -3, width: 3, background: 'var(--text)',
          left: pct(value),
        }}
      />
    </div>
  );
}

/**
 * Panel #3 — estimated PHYSICAL parameters with units and uncertainty, each as a
 * bar with a nominal marker (not a bare number). Deviation from nominal drives
 * the colour.
 */
export default function ParameterPanel({ data, source }) {
  const params = data?.twin?.parameters;
  if (!params) {
    return (
      <Panel title="Estimated Parameters" stepNo={3} source={source}>
        <div className="mono-caption">Twin unavailable — no parameter estimates.</div>
      </Panel>
    );
  }
  return (
    <Panel title="Estimated Parameters" stepNo={3} source={source}
      right={<span className="mono-caption">est. method: {data?.twin?.estimatorMethod ?? 'wls'}</span>}>
      {Object.entries(params).map(([key, p]) => {
        const m = META[key] ?? { label: key, unit: '', range: [0.6, 1.1] };
        const value = typeof p === 'object' ? p.value : p;
        const sigma = typeof p === 'object' ? p.sigma : undefined;
        const nominal = typeof p === 'object' ? p.nominal : undefined;
        return (
          <div key={key} style={{ marginBottom: 12 }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline' }}>
              <span style={{ color: 'var(--text-dim)' }}>{m.label}</span>
              <span className="num">
                {value?.toFixed(3)}
                {sigma != null && <span style={{ color: 'var(--text-faint)' }}> ± {sigma.toFixed(3)}</span>}
              </span>
            </div>
            <Gauge value={value} sigma={sigma} nominal={nominal} range={m.range} />
            <div className="mono-caption">
              nominal {nominal ?? '—'}
              {nominal != null && (
                <> · Δ {(((value - nominal) / nominal) * 100).toFixed(1)}%</>
              )}
            </div>
          </div>
        );
      })}
    </Panel>
  );
}
