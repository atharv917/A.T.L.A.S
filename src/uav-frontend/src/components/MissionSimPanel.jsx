import { useState } from 'react';
import { DEFAULT_MISSION_PROFILE, simulateMission } from '../api/dashboardApi';
import Panel from './Panel';

/**
 * Panel #8 — the demo closer. Two scenario cards side by side, each with
 * P(complete) and damage consumed, and the comparative ratio called out. This
 * is a POST action: pick a profile (default provided), press Simulate.
 */
export default function MissionSimPanel({ data, engineId, source }) {
  const [result, setResult] = useState(data?.missionSim ?? null);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState(null);
  const [profileText, setProfileText] = useState(
    JSON.stringify(DEFAULT_MISSION_PROFILE, null, 0)
  );

  async function run() {
    setBusy(true);
    setErr(null);
    let profile = DEFAULT_MISSION_PROFILE;
    try {
      profile = JSON.parse(profileText);
    } catch {
      setErr('mission profile is not valid JSON — using default');
    }
    try {
      const r = await simulateMission(engineId, profile, ['as_planned', 'derated_85pct']);
      setResult(r);
    } catch (e) {
      setErr(String(e.message || e));
    } finally {
      setBusy(false);
    }
  }

  const results = result?.results ?? [];
  const ratio = result?.comparativeRatio;
  const best = results.reduce((b, r) => (r.pComplete > (b?.pComplete ?? -1) ? r : b), null);

  return (
    <Panel title="Mission Simulation — As Planned vs De-rated" stepNo={8} source={result?.dataSource ?? source}
      right={<button className="action" onClick={run} disabled={busy}>{busy ? 'simulating…' : 'Simulate ▸'}</button>}>
      <div className="mono-caption" style={{ marginBottom: 6 }}>
        Monte-Carlo forward run of the physics model from the current estimated
        parameters for this engine. A dashboard cannot do this.
      </div>
      <input
        value={profileText}
        onChange={(e) => setProfileText(e.target.value)}
        spellCheck={false}
        style={{
          width: '100%', marginBottom: 10, background: 'var(--bg-panel-2)',
          border: '1px solid var(--border)', color: 'var(--text-dim)',
          fontFamily: 'var(--mono)', fontSize: 11, padding: '6px 8px', borderRadius: 4,
        }}
      />
      {err && <div className="mono-caption" style={{ color: 'var(--warn)', marginBottom: 8 }}>{err}</div>}

      <div className="scenario-cards">
        {results.map((r) => {
          const isBest = best && r.variant === best.variant;
          return (
            <div key={r.variant} className={`scenario-card${isBest ? ' highlight' : ''}`}>
              <h4>{r.label ?? r.variant}{isBest ? ' ◄ higher P(complete)' : ''}</h4>
              <div className="kv"><span className="k">P(complete)</span>
                <span className="num mid" style={{ color: r.pComplete >= 0.95 ? 'var(--ok)' : 'var(--warn)' }}>
                  {(r.pComplete * 100).toFixed(1)}%
                </span>
              </div>
              <div className="kv"><span className="k">damage consumed</span>
                <span className="num">{typeof r.damageConsumed === 'object'
                  ? Object.values(r.damageConsumed)[0]?.toFixed(3)
                  : Number(r.damageConsumed).toFixed(3)}</span>
              </div>
            </div>
          );
        })}
        {results.length === 0 && <div className="mono-caption">Press Simulate to run the comparison.</div>}
      </div>

      {ratio != null && (
        <div className="ratio-callout">
          De-rating to 85% consumes <b>{ratio.toFixed(2)}×</b> less valve damage over this mission
        </div>
      )}
    </Panel>
  );
}
