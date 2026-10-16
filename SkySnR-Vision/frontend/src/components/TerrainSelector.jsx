import { TERRAIN_LABEL } from './ui';

export const GUIDANCE = {
  flood: ['Possible water-related access issues', 'Verify water depth and routes', 'Water-rescue resources may be needed'],
  mountain: ['Possible steep terrain and limited approach', 'Verify slope stability', 'Specialist mountain-rescue resources may be needed'],
  urban_earthquake: ['Visible debris and blocked approaches may be present', 'Verify structural safety before entry'],
  forest: ['Restricted visibility; vegetation may obstruct the view', 'Difficult ground access; extra visual inspection may be needed'],
};

export default function TerrainSelector({ value, onChange }) {
  return (
    <div>
      <div className="grid cols-4" role="radiogroup" aria-label="Terrain type">
        {Object.keys(TERRAIN_LABEL).map((t) => (
          <div key={t} role="radio" aria-checked={value === t} tabIndex={0} className={`terrain-opt ${value === t ? 'on' : ''}`}
            onClick={() => onChange(t)} onKeyDown={(e) => (e.key === 'Enter' || e.key === ' ') && onChange(t)}>{TERRAIN_LABEL[t]}</div>
        ))}
      </div>
      <ul className="muted" style={{ marginTop: '.6rem' }}>{GUIDANCE[value].map((g) => <li key={g}>{g}</li>)}</ul>
      <p className="caption">Guidance only. Selecting a terrain does not detect hazards automatically.</p>
    </div>
  );
}
