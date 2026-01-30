import { Link } from 'react-router-dom';

export default function HomePage() {
  return (
    <div style={{ padding: '2rem', maxWidth: '1200px', margin: '0 auto' }}>
      <header style={{ textAlign: 'center', marginBottom: '3rem' }}>
        <h1 style={{ fontSize: '3rem', marginBottom: '1rem' }}>
          Classical Guitar Music Database
        </h1>
        <p style={{ fontSize: '1.2rem', color: '#666' }}>
          Explore 67,000+ classical guitar works from composers worldwide
        </p>
      </header>

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(250px, 1fr))', gap: '2rem', marginBottom: '3rem' }}>
        <Link to="/composers" style={{ textDecoration: 'none' }}>
          <div style={{ padding: '2rem', background: '#f5f5f5', borderRadius: '8px', textAlign: 'center', cursor: 'pointer' }}>
            <h2>Browse Composers</h2>
            <p>Discover composers by period, country, and style</p>
          </div>
        </Link>

        <Link to="/search" style={{ textDecoration: 'none' }}>
          <div style={{ padding: '2rem', background: '#f5f5f5', borderRadius: '8px', textAlign: 'center', cursor: 'pointer' }}>
            <h2>Search Works</h2>
            <p>Find specific pieces, arrangements, and editions</p>
          </div>
        </Link>
      </div>

      <section style={{ marginTop: '3rem', textAlign: 'center' }}>
        <h2>About This Database</h2>
        <p style={{ maxWidth: '800px', margin: '1rem auto', lineHeight: '1.6' }}>
          This database aggregates classical guitar repertoire from Sheerpluck and other sources,
          providing a comprehensive resource for guitarists, teachers, and researchers.
          All data is curated and regularly updated.
        </p>
      </section>
    </div>
  );
}
