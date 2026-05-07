import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { api, Customer } from '../api/client';

export default function CustomersPage() {
  const navigate = useNavigate();
  const [customers, setCustomers] = useState<Customer[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [search, setSearch] = useState('');
  const [page, setPage] = useState(0);
  const PAGE_SIZE = 20;

  useEffect(() => {
    setLoading(true);
    setError(null);
    api.fetchCustomers(page * PAGE_SIZE, PAGE_SIZE)
      .then(setCustomers)
      .catch(e => setError(e.message))
      .finally(() => setLoading(false));
  }, [page]);

  const filtered = customers.filter(c =>
    c.name.toLowerCase().includes(search.toLowerCase()) ||
    c.risk_tier.toLowerCase().includes(search.toLowerCase())
  );

  const scorePct = (prob: number) => Math.round(prob * 100);

  return (
    <>
      <div className="page-header">
        <h1 className="page-title">Customer Directory</h1>
        <div style={{ color: 'var(--text-secondary)' }}>Select a customer to view their ML risk profile</div>
      </div>

      <div className="card">
        <div style={{ padding: '1rem 1rem 0', display: 'flex', gap: '1rem', alignItems: 'center' }}>
          <input
            type="text"
            placeholder="Filter by name or risk tier..."
            value={search}
            onChange={e => setSearch(e.target.value)}
            style={{
              padding: '0.5rem 0.75rem',
              border: '1px solid var(--border-color)',
              borderRadius: '0.375rem',
              fontSize: '0.875rem',
              width: 280,
              outline: 'none',
            }}
          />
          {!loading && (
            <span style={{ color: 'var(--text-secondary)', fontSize: '0.875rem' }}>
              {filtered.length} customer{filtered.length !== 1 ? 's' : ''}
            </span>
          )}
        </div>

        {loading && (
          <div style={{ padding: '3rem', textAlign: 'center', color: 'var(--text-secondary)' }}>
            Loading customers...
          </div>
        )}

        {error && (
          <div style={{ padding: '2rem', textAlign: 'center', color: 'var(--danger)' }}>
            Failed to load customers: {error}
          </div>
        )}

        {!loading && !error && (
          <>
            <table className="table">
              <thead>
                <tr>
                  <th>Application ID</th>
                  <th>Applicant Name</th>
                  <th>Reported Income</th>
                  <th>Initial ML Risk</th>
                  <th>Action</th>
                </tr>
              </thead>
              <tbody>
                {filtered.length === 0 ? (
                  <tr>
                    <td colSpan={5} style={{ textAlign: 'center', color: 'var(--text-secondary)', padding: '2rem' }}>
                      No customers found.
                    </td>
                  </tr>
                ) : (
                  filtered.map(c => {
                    const score = scorePct(c.default_probability);
                    return (
                      <tr key={c.id}>
                        <td style={{ fontWeight: 500 }}>#{c.id}</td>
                        <td>{c.name}</td>
                        <td>${c.income.toLocaleString()}</td>
                        <td>
                          <span className={`badge ${
                            c.risk_tier === 'High' ? 'badge-danger' :
                            c.risk_tier === 'Medium' ? 'badge-warning' : 'badge-success'
                          }`}>
                            {c.risk_tier} Risk ({score}%)
                          </span>
                        </td>
                        <td>
                          <button
                            className="btn-primary"
                            onClick={() => navigate(`/risk-profile?id=${c.id}&name=${encodeURIComponent(c.name)}`)}
                          >
                            Analyze Profile
                          </button>
                        </td>
                      </tr>
                    );
                  })
                )}
              </tbody>
            </table>

            <div style={{ padding: '0.75rem 1rem', display: 'flex', justifyContent: 'flex-end', gap: '0.5rem', borderTop: '1px solid var(--border-color)' }}>
              <button
                className="btn-primary"
                onClick={() => setPage(p => Math.max(0, p - 1))}
                disabled={page === 0}
                style={{ padding: '0.375rem 0.75rem', fontSize: '0.875rem' }}
              >
                Previous
              </button>
              <span style={{ alignSelf: 'center', fontSize: '0.875rem', color: 'var(--text-secondary)' }}>
                Page {page + 1}
              </span>
              <button
                className="btn-primary"
                onClick={() => setPage(p => p + 1)}
                disabled={customers.length < PAGE_SIZE}
                style={{ padding: '0.375rem 0.75rem', fontSize: '0.875rem' }}
              >
                Next
              </button>
            </div>
          </>
        )}
      </div>
    </>
  );
}
