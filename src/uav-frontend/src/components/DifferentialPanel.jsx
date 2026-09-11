import {
  Bar, BarChart, CartesianGrid, Cell, Legend, ReferenceLine,
  ResponsiveContainer, Tooltip, XAxis, YAxis,
} from 'recharts';
import Panel from './Panel';

function Tip({ active, payload, label }) {
  if (!active || !payload?.length) return null;
  return (
    <div className="rc-tip">
      <div style={{ color: 'var(--text-dim)' }}>{label}</div>
      {payload.map((p) => (
        <div key={p.name} style={{ color: p.color }}>{p.name}: {Number(p.value).toFixed(1)}</div>
      ))}
    </div>
  );
}

function mean(a) { return a.length ? a.reduce((s, x) => s + x, 0) / a.length : 0; }

/**
 * Panel #4 — the localization argument, made visually.
 *
 *  (a) this engine vs the other engine, same channel: if PORT CHT sits above
 *      STARBOARD CHT, it cannot be the weather (both fly the same air).
 *  (b) the 4 cylinders of THIS engine: if one cylinder's EGT stands off from
 *      the other three, it cannot be a whole-engine effect (they share coolant,
 *      oil, intake).
 *
 *  Both together: "not environmental (other engine is fine), not whole-engine
 *  (other cylinders are fine) — it's cylinder N."
 */
export default function DifferentialPanel({ data, source }) {
  const thisCode = data?.engineCode ?? 'THIS';
  const otherCode = data?.engineOther?.engineCode ?? 'OTHER';

  const chtThis = data?.telemetry?.chtCylinders ?? [];
  const chtOther = data?.engineOther?.chtCylinders ?? [];
  const egtThis = data?.telemetry?.egtCylinders ?? [];

  const engRows = chtThis.map((v, i) => ({
    cyl: `CYL ${i + 1}`,
    [thisCode]: v,
    [otherCode]: chtOther[i] ?? null,
  }));

  const egtMeanRest = (i) => mean(egtThis.filter((_, j) => j !== i));
  const egtRows = egtThis.map((v, i) => ({
    cyl: `CYL ${i + 1}`,
    egt: v,
    offset: +(v - egtMeanRest(i)).toFixed(1),
  }));
  const hottest = egtRows.reduce((h, r, i) => (r.offset > (egtRows[h]?.offset ?? -1e9) ? i : h), 0);
  const spread = egtThis.length ? Math.max(...egtThis) - Math.min(...egtThis) : 0;
  const chtMeanDiff = +(mean(chtThis) - mean(chtOther)).toFixed(1);

  return (
    <Panel title="Differential — Engine ↔ Engine · Cylinder ↔ Cylinder" stepNo={4} source={source}
      right={<span className={`pill ${Math.abs(chtMeanDiff) > 6 ? 'warn' : 'ok'}`}>
        Δ CHT {chtMeanDiff > 0 ? '+' : ''}{chtMeanDiff}°C vs {otherCode}
      </span>}>
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 14 }}>
        <div>
          <div className="mono-caption" style={{ marginBottom: 4 }}>
            (a) {thisCode} vs {otherCode} — CHT per cylinder (°C)
          </div>
          <div style={{ height: 210 }}>
            <ResponsiveContainer>
              <BarChart data={engRows} margin={{ top: 6, right: 8, bottom: 0, left: -18 }}>
                <CartesianGrid stroke="var(--grid)" vertical={false} />
                <XAxis dataKey="cyl" />
                <YAxis domain={['dataMin - 6', 'dataMax + 6']} />
                <Tooltip content={<Tip />} />
                <Legend wrapperStyle={{ fontFamily: 'var(--mono)', fontSize: 10 }} />
                <Bar name={thisCode} dataKey={thisCode} fill="var(--accent)" barSize={14} />
                <Bar name={otherCode} dataKey={otherCode} fill="var(--text-faint)" barSize={14} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>
        <div>
          <div className="mono-caption" style={{ marginBottom: 4 }}>
            (b) {thisCode} — each cylinder EGT vs mean of the other three (°C)
          </div>
          <div style={{ height: 210 }}>
            <ResponsiveContainer>
              <BarChart data={egtRows} margin={{ top: 6, right: 8, bottom: 0, left: -18 }}>
                <CartesianGrid stroke="var(--grid)" vertical={false} />
                <XAxis dataKey="cyl" />
                <YAxis domain={[(dm) => Math.min(-8, dm), (dm) => Math.max(8, dm)]} />
                <Tooltip content={<Tip />} />
                <ReferenceLine y={0} stroke="var(--border-bright)" />
                <Bar name="EGT offset" dataKey="offset" barSize={26}>
                  {egtRows.map((r, i) => (
                    <Cell key={i} fill={i === hottest && r.offset > 12 ? 'var(--crit)' : 'var(--residual)'} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>
      </div>
      <div className="ratio-callout" style={{ color: 'var(--text)', borderColor: 'var(--border-bright)', background: 'var(--bg-panel-2)' }}>
        {spread > 20
          ? <>Cylinder {hottest + 1} EGT is <b style={{ color: 'var(--crit)' }}>+{egtRows[hottest].offset}°C</b> vs its siblings while {otherCode} stays flat →
            not environmental, not whole-engine — <b>localized to {thisCode} cylinder {hottest + 1}</b>.</>
          : <>All cylinders within {spread.toFixed(0)}°C and both engines tracking — no localized fault.</>}
      </div>
    </Panel>
  );
}
