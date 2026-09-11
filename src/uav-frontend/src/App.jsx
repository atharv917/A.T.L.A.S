import { useState } from 'react';
import { USE_MOCK } from './api/dashboardApi';
import { useDashboard } from './hooks/useDashboard';
import DataSourceBadge from './components/DataSourceBadge';
import OverviewTile from './components/OverviewTile';
import MeasuredExpectedResidualPanel from './components/MeasuredExpectedResidualPanel';
import ParameterPanel from './components/ParameterPanel';
import DifferentialPanel from './components/DifferentialPanel';
import AnomalyPanel from './components/AnomalyPanel';
import HealthPanel from './components/HealthPanel';
import RulPanel from './components/RulPanel';
import MissionSimPanel from './components/MissionSimPanel';

export default function App() {
  const [selected, setSelected] = useState(1);

  // Two fixed engines on the platform -> two fixed polling hooks.
  const e1 = useDashboard(1);
  const e2 = useDashboard(2);
  const byId = { 1: e1.data, 2: e2.data };

  const sel = selected === 1 ? e1 : e2;
  const data = sel.data;
  const source = data?.dataSource ?? 'SIMULATED';

  return (
    <div className="app">
      <div className="topbar">
        <h1>UAV DIGITAL TWIN</h1>
        <span className="sub">SIH26054 · DRDO · aero piston engine health & RUL</span>
        <span className="spacer" />
        <div className="engine-switch">
          {[1, 2].map((id) => (
            <button key={id} className={selected === id ? 'active' : ''} onClick={() => setSelected(id)}>
              {byId[id]?.engineCode ?? `ENG-${id}`}
            </button>
          ))}
        </div>
        <DataSourceBadge source={source} size="lg" />
      </div>

      {sel.twinDown && (
        <div className="banner crit">
          TWIN UNAVAILABLE for {data?.engineCode ?? `engine ${selected}`} — showing raw telemetry only.
          Expected / residual / parameters / health / RUL are not being computed.
        </div>
      )}
      {sel.stale && !sel.twinDown && (
        <div className="banner warn">
          Dashboard feed stale — last successful update{' '}
          {sel.lastUpdated ? sel.lastUpdated.toLocaleTimeString() : 'unknown'}. Retrying every 2s.
        </div>
      )}

      {!data ? (
        <div className="foot">Connecting to {USE_MOCK ? 'mock data source' : 'backend /api/v1'}…</div>
      ) : (
        <div className="grid">
          <div className="col-12">
            <OverviewTile engines={byId} selectedId={selected} onSelect={setSelected} source={source} />
          </div>

          <div className="col-7">
            <MeasuredExpectedResidualPanel data={data} source={source} />
          </div>
          <div className="col-5">
            <ParameterPanel data={data} source={source} />
          </div>

          <div className="col-12">
            <DifferentialPanel data={data} source={source} />
          </div>

          <div className="col-7">
            <AnomalyPanel data={data} source={source} />
          </div>
          <div className="col-5">
            <HealthPanel data={data} source={source} />
          </div>

          <div className="col-5">
            <RulPanel data={data} source={source} />
          </div>
          <div className="col-7">
            <MissionSimPanel data={data} engineId={selected} source={source} />
          </div>
        </div>
      )}

      <div className="foot">
        {USE_MOCK
          ? 'MOCK DATA SOURCE — src/mocks/dashboard.json with scripted degradation ramp. Set VITE_USE_MOCK=false to hit the Java backend.'
          : 'LIVE — GET /api/v1/dashboard/{engineId}, POST /api/v1/engines/{engineId}/simulate'}
        {' · '}polling 2s · all values SIMULATED
      </div>
    </div>
  );
}
