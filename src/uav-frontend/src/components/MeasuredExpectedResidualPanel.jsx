import {
  Bar, BarChart, CartesianGrid, Cell, ComposedChart, Legend, Line,
  ReferenceLine, ResponsiveContainer, Tooltip, XAxis, YAxis,
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

/**
 * Panel #2 — the "this is a twin, not a chart" panel. For the CHT channel it
 * shows, per cylinder: what the sensor measured, what the physics model
 * expected, and the residual (gap). A raw-telemetry dashboard can only draw the
 * first series.
 */
export default function MeasuredExpectedResidualPanel({ data, source }) {
  const measured = data?.telemetry?.chtCylinders ?? [];
  const expected = data?.twin?.expected?.cht_c ?? [];
  const residual = data?.twin?.residual?.cht_c ?? [];

  const rows = measured.map((m, i) => ({
    cyl: `CYL ${i + 1}`,
    measured: m,
    expected: expected[i] ?? null,
    residual: residual[i] ?? (expected[i] != null ? +(m - expected[i]).toFixed(1) : null),
  }));
  const maxAbsRes = Math.max(10, ...rows.map((r) => Math.abs(r.residual ?? 0)));

  return (
    <Panel title="Measured · Expected · Residual — CHT" stepNo={2} source={source}>
      {!data?.twin ? (
        <div className="mono-caption">Twin unavailable — only measured CHT is shown below.</div>
      ) : null}
      <div style={{ display: 'grid', gridTemplateColumns: '1.4fr 1fr', gap: 12 }}>
        <div style={{ height: 200 }}>
          <div className="mono-caption" style={{ marginBottom: 4 }}>measured vs expected (°C)</div>
          <ResponsiveContainer>
            <ComposedChart data={rows} margin={{ top: 6, right: 8, bottom: 0, left: -18 }}>
              <CartesianGrid stroke="var(--grid)" vertical={false} />
              <XAxis dataKey="cyl" />
              <YAxis domain={['dataMin - 8', 'dataMax + 8']} />
              <Tooltip content={<Tip />} />
              <Legend wrapperStyle={{ fontFamily: 'var(--mono)', fontSize: 10 }} />
              <Bar name="measured" dataKey="measured" fill="var(--measured)" barSize={16} opacity={0.35} />
              <Line name="expected" dataKey="expected" stroke="var(--expected)" strokeWidth={2} dot={{ r: 3 }} />
            </ComposedChart>
          </ResponsiveContainer>
        </div>
        <div style={{ height: 200 }}>
          <div className="mono-caption" style={{ marginBottom: 4 }}>residual = measured − expected (°C)</div>
          <ResponsiveContainer>
            <BarChart data={rows} margin={{ top: 6, right: 8, bottom: 0, left: -18 }}>
              <CartesianGrid stroke="var(--grid)" vertical={false} />
              <XAxis dataKey="cyl" />
              <YAxis domain={[-maxAbsRes * 1.15, maxAbsRes * 1.15]} />
              <Tooltip content={<Tip />} />
              <ReferenceLine y={0} stroke="var(--border-bright)" />
              <Bar name="residual" dataKey="residual" barSize={22}>
                {rows.map((r, i) => (
                  <Cell key={i} fill={Math.abs(r.residual ?? 0) > 10 ? 'var(--crit)' : 'var(--residual)'} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>
      <table style={{ width: '100%', marginTop: 10, fontFamily: 'var(--mono)', fontSize: 12, borderCollapse: 'collapse' }}>
        <thead>
          <tr style={{ color: 'var(--text-dim)' }}>
            <th style={{ textAlign: 'left' }}>channel</th>
            {rows.map((r) => <th key={r.cyl} style={{ textAlign: 'right' }}>{r.cyl}</th>)}
          </tr>
        </thead>
        <tbody>
          <tr><td>measured</td>{rows.map((r) => <td key={r.cyl} style={{ textAlign: 'right' }}>{r.measured?.toFixed?.(0) ?? r.measured}</td>)}</tr>
          <tr style={{ color: 'var(--expected)' }}><td>expected</td>{rows.map((r) => <td key={r.cyl} style={{ textAlign: 'right' }}>{r.expected == null ? '—' : r.expected.toFixed(1)}</td>)}</tr>
          <tr style={{ color: 'var(--residual)' }}><td>residual</td>{rows.map((r) => (
            <td key={r.cyl} style={{ textAlign: 'right', color: Math.abs(r.residual ?? 0) > 10 ? 'var(--crit)' : undefined }}>
              {r.residual == null ? '—' : (r.residual > 0 ? '+' : '') + r.residual.toFixed(1)}
            </td>
          ))}</tr>
        </tbody>
      </table>
    </Panel>
  );
}
