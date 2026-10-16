import { Link } from 'react-router-dom';

const STEPS = [
  ['Upload', 'A manager creates a mission and uploads a drone image.'],
  ['Analyse', 'The configured AI model finds supported objects such as people and vehicles.'],
  ['Review', 'The manager checks each detection and decides what is real.'],
  ['Assign', 'Confirmed cases are given a priority score and assigned to a team member.'],
  ['Respond', 'The team member acknowledges, responds and records the outcome.'],
  ['Report', 'A PDF report is built from the saved records.'],
];

export default function LandingPage() {
  return (
    <div>
      <header className="pub-nav">
        <span className="brand">SkySnR Vision</span>
        <div className="row"><Link to="/login" className="btn secondary sm">Sign in</Link><Link to="/register" className="btn sm">Register</Link></div>
      </header>
      <section className="hero">
        <div className="stack">
          <h1>Drone images, turned into a clear rescue plan.</h1>
          <p>SkySnR Vision helps rescue teams review drone imagery, decide which cases to look at first, assign them to people, and keep a record of what happened.</p>
          <p className="muted">It supports human decisions. It does not replace emergency services or rescue professionals.</p>
          <div className="row"><Link to="/register" className="btn">Request access</Link><Link to="/login" className="btn secondary">Sign in</Link></div>
        </div>
        <figure style={{ margin: 0 }}>
          <img src="/images/incidents/urban-flood-illustration.svg" alt="Illustration of a flooded urban neighbourhood seen from above" />
          <figcaption className="caption">Illustration. Not a real incident and not an analysed image.</figcaption>
        </figure>
      </section>
      <section className="section">
        <h2>How it works</h2>
        <div className="grid cols-4">
          {STEPS.map(([t, d], i) => <div className="card" key={t}><div className="step-num">{i + 1}</div><h3>{t}</h3><p className="muted">{d}</p></div>)}
        </div>
      </section>
      <section className="section">
        <h2>Situations it is designed for</h2>
        <div className="grid cols-2">
          {[['Urban flooding', 'urban-flood-illustration.svg'], ['Building collapse', 'building-collapse-illustration.svg'], ['Fire aftermath', 'urban-fire-illustration.svg'], ['Blocked roads and debris', 'blocked-road-illustration.svg']].map(([t, f]) => (
            <figure className="card" key={t} style={{ margin: 0 }}>
              <img src={`/images/incidents/${f}`} alt={`Illustration: ${t}`} style={{ width: '100%', borderRadius: 10 }} />
              <figcaption><strong>{t}</strong> <span className="sample">Illustration</span></figcaption>
            </figure>
          ))}
        </div>
      </section>
      <section className="section"><div className="card"><h3>Three roles, one workflow</h3>
        <p><strong>Admin</strong> approves who can use the system. <strong>Rescue Operations Managers</strong> analyse images, verify detections and assign cases. <strong>Rescue Team Members</strong> see only their own assigned cases and record progress.</p>
        <p className="muted">New accounts must be approved by an admin before they can sign in.</p></div></section>
    </div>
  );
}
