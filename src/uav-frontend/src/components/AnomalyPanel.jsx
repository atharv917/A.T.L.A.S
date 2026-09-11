import {
  Area, AreaChart, CartesianGrid, ReferenceLine, ResponsiveContainer,
  Tooltip, XAxis, YAxis,
} from 'recharts';
import Panel from './Panel';

function Tip({ active, payload, label }) {
  if (!active || !payload?.length) return null;
  return (
    <div className="rc-tip">
      <div style={{ color: 'var(--text-dim)' }}>{label}</div>
      <div style={{ color: 'var(--accent)' }}>score: {Number(payload[0].value).toFixed(2)}</div>
    </div>
  );
}

/**
 * Panel #5 — anomaly score over time (must sit flat, THEN rise and cross the
 * threshold — the mock ramps it so this happens live), then the ranked fault
 * hypotheses. The lowest-probability hypothesis is ALWAYS rendered — hiding the
 * alternative you considered and rejected is exactly what we do not do.
 */
export default function AnomalyPanel({ data, source }) {
  const twin = data?.twin;
  const hist = twin?.anomalyHistory ?? [];
  const threshold = twin?.anomalyThreshold ?? 3.0;
  const score = twin?.anomalyScore ?? 0;
  const fired = score >= threshold;
  const hyps = data?.diagnosis?.hypotheses ?? [];

  return (
    <Panel title="Anomaly & Diagnosis" stepNo={5} source={source}
      right={<span className={`pill ${fired ? 'crit' : score > threshold * 0.7 ? 'warn' : 'ok'}`}>
        score {score.toFixed(2)} / thr {threshold.toFixed(1)} {fired ? '· FIRED' : ''}
      </span>}>
      {!twin ? (
        <div className="mono-caption">Twin unavailable — anomaly detector offline.</div>
      ) : (
        <>
          <div style={{ height: 150 }}>
            <ResponsiveContainer>
              <AreaChart data={hist} margin={{ top: 6, right: 10, bottom: 0, left: -20 }}>
                <defs>
                  <linearGradient id="anom" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="0%" stopColor="var(--accent)" stopOpacity={0.5} />
                    <stop offset="100%" stopColor="var(--accent)" stopOpacity={0.03} />
                  </linearGradient>
                </defs>
                <CartesianGrid stroke="var(--grid)" vertical={false} />
                <XAxis dataKey="t" />
                <YAxis domain={[0, Math.max(threshold + 1, Math.ceil(score + 1))]} />
                <Tooltip content={<Tip />} />
                <ReferenceLine y={threshold} stroke="var(--crit)" strokeDasharray="4 3"
                  label={{ value: 'threshold', position: 'insidetopright', fill: 'var(--crit)', fontSize: 10, fontFamily: 'var(--mono)' }} />
                <Area type="monotone" dataKey="score" stroke="var(--accent)" strokeWidth={2} fill="url(#anom)" isAnimationActive={false} />
              </AreaChart>
            </ResponsiveContainer>
          </div>
          <div className="mono-caption" style={{ margin: '4px 0 10px' }}>
            Mahalanobis distance over the residual vector, CUSUM-gated — a single
            spike will not fire it.
          </div>

          <div style={{ color: 'var(--text-dim)', fontSize: 12, letterSpacing: 0.5, marginBottom: 4 }}>
            RANKED FAULT HYPOTHESES
          </div>
          {hyps.map((h, i) => (
            <div key={h.fault} className={`hyp-row ${i === hyps.length - 1 && hyps.length > 1 ? 'low' : ''}`}>
              <div>
                <div>{h.label ?? h.fault}</div>
                <div className="hyp-bar-track">
                  <div className="hyp-bar-fill" style={{
                    width: `${(h.probability * 100).toFixed(0)}%`,
                    background: i === 0 ? 'var(--accent)' : 'var(--accent-dim)',
                  }} />
                </div>
              </div>
              <span className="num" style={{ color: i === 0 ? 'var(--text)' : 'var(--text-dim)' }}>
                {(h.probability * 100).toFixed(0)}%
              </span>
            </div>
          ))}
          {hyps.length > 1 && (
            <div className="mono-caption" style={{ marginTop: 6 }}>
              lowest-ranked hypothesis ({hyps[hyps.length - 1].label ?? hyps[hyps.length - 1].fault},
              {' '}{(hyps[hyps.length - 1].probability * 100).toFixed(0)}%) shown deliberately — considered and not discarded.
            </div>
          )}
        </>
      )}
    </Panel>
  );
}
