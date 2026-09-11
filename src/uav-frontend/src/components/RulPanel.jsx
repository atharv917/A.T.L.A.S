import Panel from './Panel';

/**
 * Panel #7 — RUL as a RANGE, never a bare integer. The CI band is drawn; the
 * more operationally useful number, P(fail this mission), is shown larger and
 * separately. All computed tiers are listed with the reported (most
 * conservative) one highlighted.
 */
export default function RulPanel({ data, source }) {
  const rul = data?.twin ? data?.rul : null;
  if (!rul) {
    return (
      <Panel title="Remaining Useful Life" stepNo={7} source={source}>
        <div className="mono-caption">Twin unavailable — RUL not computed.</div>
      </Panel>
    );
  }
  const { medianHours: med, p05Hours: p05, p95Hours: p95, pFailMission: pf, reportedTier, component, tiers = [] } = rul;
  const lo = Math.min(p05, med);
  const hi = Math.max(p95, med);
  const pctIn = (x) => `${((x - lo) / (hi - lo || 1)) * 100}%`;
  const pfCls = pf >= 0.05 ? 'crit' : pf >= 0.02 ? 'warn' : 'ok';

  return (
    <Panel title="Remaining Useful Life" stepNo={7} source={source}
      right={<span className="mono-caption">component: {component ?? '—'}</span>}>
      <div style={{ display: 'grid', gridTemplateColumns: '1.2fr 1fr', gap: 16 }}>
        <div>
          <div className="mono-caption">reported (Tier {reportedTier}, most conservative)</div>
          <div className="num big">
            {med}<span className="unit">h</span>
          </div>
          <div className="mono-caption" style={{ marginBottom: 6 }}>
            90% CI: {p05}–{p95} h
          </div>
          <div className="bar-track" style={{ height: 16 }}>
            <div style={{
              position: 'absolute', top: 0, bottom: 0, background: 'var(--accent-dim)', opacity: 0.5,
              left: pctIn(p05), width: `calc(${pctIn(p95)} - ${pctIn(p05)})`,
            }} />
            <div style={{ position: 'absolute', top: -3, bottom: -3, width: 3, background: 'var(--text)', left: pctIn(med) }} />
          </div>
          <div className="mono-caption" style={{ display: 'flex', justifyContent: 'space-between', marginTop: 2 }}>
            <span>{lo} h</span><span>{hi} h</span>
          </div>
        </div>
        <div style={{ borderLeft: '1px solid var(--border)', paddingLeft: 14 }}>
          <div className="mono-caption">P(fail this mission)</div>
          <div className={`num big status-${pfCls}`}>{(pf * 100).toFixed(1)}<span className="unit">%</span></div>
          <div className="mono-caption">the number an operator acts on</div>
        </div>
      </div>

      <table style={{ width: '100%', marginTop: 12, fontFamily: 'var(--mono)', fontSize: 12, borderCollapse: 'collapse' }}>
        <thead>
          <tr style={{ color: 'var(--text-dim)' }}>
            <th style={{ textAlign: 'left' }}>tier</th>
            <th style={{ textAlign: 'left' }}>method</th>
            <th style={{ textAlign: 'right' }}>median / note</th>
          </tr>
        </thead>
        <tbody>
          {tiers.map((t) => (
            <tr key={t.tier} style={{ color: t.tier === reportedTier ? 'var(--text)' : 'var(--text-faint)' }}>
              <td>{t.tier === reportedTier ? '► ' : ''}T{t.tier}</td>
              <td>{TIER_METHOD[t.tier] ?? '—'}</td>
              <td style={{ textAlign: 'right' }}>
                {t.medianHours != null ? `${t.medianHours} h` : t.onsetHoursAgo != null ? `onset ${t.onsetHoursAgo} h ago` : '—'}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </Panel>
  );
}

const TIER_METHOD = {
  1: 'Arrhenius valve recession',
  2: 'health-trend extrapolation',
  3: 'onset-rate (no life claim)',
};
