import { useState, useEffect } from 'react';
import React from 'react';
import {
  PieChart, Pie, Cell, Tooltip, ResponsiveContainer,
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Legend,
  ScatterChart, Scatter, ZAxis,
} from 'recharts';
import { api, PortfolioAnalytics } from '../api/client';

const TIER_COLORS: Record<string, string> = {
  High: 'var(--danger)',
  Medium: 'var(--warning)',
  Low: 'var(--success)',
};

export default function DashboardPage() {
  const [analytics, setAnalytics] = useState<PortfolioAnalytics | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const tableauUrl = import.meta.env.VITE_TABLEAU_REPORT_URL as string | undefined;

  useEffect(() => {
    api.fetchPortfolioAnalytics()
      .then(setAnalytics)
      .catch(e => setError(e.message))
      .finally(() => setLoading(false));
  }, []);

  return (
    <>
      <div className="page-header">
        <h1 className="page-title">Portfolio Analytics Dashboard</h1>
        <div style={{ color: 'var(--text-secondary)' }}>
          {analytics ? `${analytics.total_customers} customers · Avg risk ${(analytics.avg_default_probability * 100).toFixed(1)}%` : 'Loading...'}
        </div>
      </div>

      {loading && (
        <div style={{ padding: '3rem', textAlign: 'center', color: 'var(--text-secondary)' }}>
          Loading portfolio analytics...
        </div>
      )}
      {error && (
        <div style={{ padding: '2rem', textAlign: 'center', color: 'var(--danger)' }}>
          Failed to load analytics: {error}
        </div>
      )}

      {analytics && (
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '2rem' }}>

          {/* Risk Tier Donut */}
          <div className="card" style={{ padding: '2rem' }}>
            <h3 style={{ margin: '0 0 1.5rem 0' }}>Risk Tier Distribution</h3>
            <ResponsiveContainer width="100%" height={260}>
              <PieChart>
                <Pie
                  data={analytics.risk_distribution}
                  dataKey="count"
                  nameKey="tier"
                  innerRadius={60}
                  outerRadius={100}
                  paddingAngle={3}
                  label={({ tier, percent }) => `${tier} ${(percent * 100).toFixed(0)}%`}
                >
                  {analytics.risk_distribution.map(entry => (
                    <Cell key={entry.tier} fill={TIER_COLORS[entry.tier] || '#8884d8'} />
                  ))}
                </Pie>
                <Tooltip formatter={(v: number) => [`${v} customers`, 'Count']} />
              </PieChart>
            </ResponsiveContainer>
          </div>

          {/* Default Probability Histogram */}
          <div className="card" style={{ padding: '2rem' }}>
            <h3 style={{ margin: '0 0 1.5rem 0' }}>Default Probability Distribution</h3>
            <ResponsiveContainer width="100%" height={260}>
              <BarChart data={analytics.default_probability_distribution} margin={{ left: 0 }}>
                <CartesianGrid strokeDasharray="3 3" vertical={false} />
                <XAxis dataKey="bucket" tick={{ fontSize: 11 }} />
                <YAxis />
                <Tooltip />
                <Bar dataKey="count" fill="var(--primary)" radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>

          {/* Income Histogram */}
          <div className="card" style={{ padding: '2rem' }}>
            <h3 style={{ margin: '0 0 1.5rem 0' }}>Income Distribution</h3>
            <ResponsiveContainer width="100%" height={260}>
              <BarChart data={analytics.income_histogram} margin={{ left: 0 }}>
                <CartesianGrid strokeDasharray="3 3" vertical={false} />
                <XAxis dataKey="bucket" tick={{ fontSize: 11 }} />
                <YAxis />
                <Tooltip />
                <Bar dataKey="count" fill="var(--success)" radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>

          {/* KPI Summary */}
          <div className="card" style={{ padding: '2rem' }}>
            <h3 style={{ margin: '0 0 1.5rem 0' }}>Portfolio KPIs</h3>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '1.25rem' }}>
              {[
                { label: 'Total Customers', value: analytics.total_customers.toLocaleString() },
                { label: 'Average Default Probability', value: `${(analytics.avg_default_probability * 100).toFixed(1)}%` },
                { label: 'High-Risk Customers', value: `${(analytics.high_risk_percentage * 100).toFixed(1)}%` },
                {
                  label: 'Risk Breakdown',
                  value: analytics.risk_distribution.map(r => `${r.tier}: ${r.count}`).join(' · '),
                },
              ].map(kpi => (
                <div key={kpi.label} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', borderBottom: '1px solid var(--border-color)', paddingBottom: '0.75rem' }}>
                  <span style={{ color: 'var(--text-secondary)', fontSize: '0.875rem' }}>{kpi.label}</span>
                  <span style={{ fontWeight: 700, fontSize: '1rem' }}>{kpi.value}</span>
                </div>
              ))}
            </div>
          </div>

        </div>
      )}

      {/* Optional Tableau embed */}
      {tableauUrl && (
        <div className="card" style={{ marginTop: '2rem', padding: '1rem', minHeight: 500 }}>
          <h3 style={{ margin: '0 0 1rem 0' }}>Extended Tableau Analytics</h3>
          {React.createElement('tableau-viz', {
            id: 'tableauViz',
            src: tableauUrl,
            toolbar: 'hidden',
            'hide-tabs': 'true',
            style: { width: '100%', height: '500px' },
          })}
        </div>
      )}
    </>
  );
}
