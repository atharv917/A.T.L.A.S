import Panel from './Panel';

function healthClass(v) {
  if (v == null) return '';
  if (v >= 0.85) return 'status-ok';
  if (v >= 0.6) return 'status-warn';
  return 'status-crit';
}
function healthPill(v) {
  if (v == null) return 'pill';
  if (v >= 0.85) return 'pill ok';
  if (v >= 0.6) return 'pill warn';
  return 'pill crit';
}

function EngineRow({ d, selected, onSelect }) {
  if (!d) return null;
  const h = d.health?.overall;
  return (
    <button
      className="scenario-card"
      style={{
        textAlign: 'left',
        cursor: 'pointer',
        borderColor: selected ? 'var(--border-bright)' : 'var(--border)',
        width: '100%',
      }}
      onClick={() => onSelect(d.engineId)}
    >
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline' }}>
        <span className="num mid">{d.engineCode}</span>
        <span className="mono-caption">{d.position}</span>
      </div>
      <div className="kv"><span className="k">Regime</span><span className="v">{d.regime ?? '—'}</span></div>
      <div className="kv"><span className="k">RPM</span><span className="v">{d.telemetry?.rpm ?? '—'}</span></div>
      <div className="kv">
        <span className="k">Overall health</span>
        <span className={healthPill(h)}>
          {h == null ? 'n/a' : h.toFixed(2)} {d.health?.limitedBy ? `· ${d.health.limitedBy}` : ''}
        </span>
      </div>
      <div className="kv">
        <span className="k">Twin</span>
        <span className={d.twin ? 'status-ok' : 'status-crit'} style={{ fontFamily: 'var(--mono)', fontSize: 12 }}>
          {d.twin ? 'ONLINE' : 'UNAVAILABLE'}
        </span>
      </div>
      {d.faultAlerts?.length > 0 && (
        <div className="mono-caption" style={{ marginTop: 6, color: 'var(--warn)' }}>
          ⚠ {d.faultAlerts[0].message}
        </div>
      )}
    </button>
  );
}

export default function OverviewTile({ engines, selectedId, onSelect, source }) {
  const list = Object.values(engines).filter(Boolean);
  const worst = Math.min(...list.map((e) => e.health?.overall ?? 1));
  return (
    <Panel title="Platform Overview" stepNo={1} source={source}
      right={<span className={`pill ${worst >= 0.85 ? 'ok' : worst >= 0.6 ? 'warn' : 'crit'}`}>
        {list.length} ENGINES · {worst >= 0.85 ? 'ALL NOMINAL' : worst >= 0.6 ? 'ATTENTION' : 'CRITICAL'}
      </span>}
    >
      <div className="mono-caption" style={{ marginBottom: 8 }}>
        {list[0]?.platformId ?? 'TAPAS'} · click an engine to inspect
      </div>
      <div className="scenario-cards">
        {[1, 2].map((id) => (
          <EngineRow key={id} d={engines[id]} selected={selectedId === id} onSelect={onSelect} />
        ))}
      </div>
    </Panel>
  );
}
