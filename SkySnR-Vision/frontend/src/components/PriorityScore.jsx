import { Badge } from './ui';

export default function PriorityScore({ score, level, finalLevel, breakdown = [], explanation, override }) {
  if (score === undefined || score === null) return <p className="muted">No score. Priority applies to person detections only.</p>;
  return (
    <div className="stack">
      <div className="row"><span className="score-ring">{score}</span><span className="muted">/ 100</span><Badge value={level} /></div>
      <div className="bar" aria-hidden="true"><i style={{ width: `${score}%` }} /></div>
      <ul style={{ margin: 0, paddingLeft: '1.1rem' }}>
        {breakdown.map((b) => <li key={b.factor}><strong>+{b.points}</strong> {b.factor.replace(/_/g, ' ')} <span className="muted">— {b.detail}</span></li>)}
      </ul>
      {explanation && <p className="muted">{explanation}</p>}
      {override && <div className="alert">Manager decision: <Badge value={finalLevel} /> — {override.justification}</div>}
      <p className="caption">Calculated score is a review aid, not a prediction of survival or medical condition.</p>
    </div>
  );
}
