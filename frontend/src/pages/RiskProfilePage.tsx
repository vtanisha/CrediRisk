import { useState, useEffect, useCallback } from 'react';
import { useSearchParams } from 'react-router-dom';
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid, Cell } from 'recharts';
import { api, CustomerDetail, ShapValue } from '../api/client';
import { usePredictionWebSocket } from '../hooks/usePredictionWebSocket';

interface ShapData {
  feature: string;
  value: number;
}

function shapToChartData(vals: ShapValue[]): ShapData[] {
  return vals.map(v => ({ feature: v.feature_name, value: v.contribution }));
}

export default function RiskProfilePage() {
  const [searchParams] = useSearchParams();
  const idParam = searchParams.get('id');
  const customerId = idParam ? parseInt(idParam, 10) : NaN;
  const nameParam = searchParams.get('name') || 'Customer';

  const [customer, setCustomer] = useState<CustomerDetail | null>(null);
  const [baseProbability, setBaseProbability] = useState<number>(50);
  const [shapValues, setShapValues] = useState<ShapData[]>([]);
  const [explanation, setExplanation] = useState<string>('');
  const [loadingExpl, setLoadingExpl] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const [income, setIncome] = useState<number>(45000);
  const [creditAmount, setCreditAmount] = useState<number>(250000);

  const ws = usePredictionWebSocket(isNaN(customerId) ? null : customerId);

  // Load customer data on mount
  useEffect(() => {
    if (isNaN(customerId)) return;
    api.fetchCustomer(customerId)
      .then(c => {
        setCustomer(c);
        setIncome(c.income);
        setCreditAmount(c.loan_amount);
        setBaseProbability(Math.round(c.default_probability * 100));
        if (c.shap_values.length > 0) {
          setShapValues(shapToChartData(c.shap_values));
        }
      })
      .catch(e => setError(e.message));
  }, [customerId]);

  // When WebSocket delivers new SHAP values, sync them to local state
  useEffect(() => {
    if (ws.shapValues.length > 0) {
      setShapValues(ws.shapValues.map(v => ({ feature: v.feature_name, value: v.contribution })));
    }
  }, [ws.shapValues]);

  const handleIncomeChange = useCallback((val: number) => {
    setIncome(val);
    ws.sendFeatures(val, creditAmount);
  }, [creditAmount, ws.sendFeatures]);

  const handleLoanChange = useCallback((val: number) => {
    setCreditAmount(val);
    ws.sendFeatures(income, val);
  }, [income, ws.sendFeatures]);

  const handleGenerateExplanation = async () => {
    if (isNaN(customerId)) return;
    setLoadingExpl(true);
    try {
      const data = await api.chat(customerId, `Explain the risk profile for this customer with income ${income} and loan amount ${creditAmount}.`);
      setExplanation(data.reply);
    } catch {
      setExplanation('Unable to connect to AI Explanation service.');
    }
    setLoadingExpl(false);
  };

  // Use WS live probability if available, else fall back to the customer's stored value
  const probability = ws.probability ?? baseProbability;
  const confidenceLow = ws.confidenceLower;
  const confidenceHigh = ws.confidenceUpper;

  // SVG Gauge calculations
  const radius = 120;
  const strokeWidth = 24;
  const normalizedProb = probability / 100;
  const dashArray = radius * Math.PI;
  const dashOffset = dashArray - dashArray * normalizedProb;
  const color = probability > 60 ? 'var(--danger)' : probability > 30 ? 'var(--warning)' : 'var(--success)';

  if (error) {
    return (
      <div style={{ padding: '2rem', color: 'var(--danger)' }}>
        Error loading customer: {error}
      </div>
    );
  }

  const displayName = customer?.name || nameParam;

  return (
    <>
      <div className="page-header">
        <h1 className="page-title">{displayName}'s Risk Profile</h1>
        <div style={{ color: 'var(--text-secondary)' }}>Application ID: #{customerId}</div>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: 'minmax(400px, 1fr) 2fr', gap: '2rem' }}>

        {/* Left Column */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '2rem' }}>

          {/* Gauge Widget */}
          <div className="card" style={{ padding: '2rem', display: 'flex', flexDirection: 'column', alignItems: 'center' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '1rem' }}>
              <h3 style={{ margin: 0 }}>Default Probability</h3>
              <span style={{
                width: 8, height: 8, borderRadius: '50%',
                background: ws.isConnected ? 'var(--success)' : '#aaa',
                display: 'inline-block', title: ws.isConnected ? 'Live' : 'Offline',
              }} />
            </div>
            <svg width={radius * 2} height={radius + strokeWidth} style={{ transform: 'rotate(180deg)' }}>
              <circle
                cx={radius} cy={radius} r={radius - strokeWidth / 2}
                fill="none" stroke="var(--border-color)" strokeWidth={strokeWidth}
                strokeDasharray={dashArray} strokeDashoffset="0"
              />
              <circle
                cx={radius} cy={radius} r={radius - strokeWidth / 2}
                fill="none" stroke={color} strokeWidth={strokeWidth}
                strokeDasharray={dashArray} strokeDashoffset={dashOffset}
                style={{ transition: 'stroke-dashoffset 0.5s ease-out, stroke 0.5s ease' }}
              />
            </svg>
            <div style={{ marginTop: '-40px', textAlign: 'center' }}>
              <div style={{ fontSize: '3rem', fontWeight: 800, color }}>
                {probability}%
              </div>
              {confidenceLow !== null && confidenceHigh !== null && (
                <div style={{ color: 'var(--text-secondary)', fontSize: '0.875rem', marginTop: '4px' }}>
                  {confidenceLow}% – {confidenceHigh}% (95% CI)
                </div>
              )}
              <div style={{ color: 'var(--text-secondary)', fontWeight: 500, marginTop: '10px' }}>
                {probability > 60 ? 'High Risk' : probability > 30 ? 'Medium Risk' : 'Low Risk'}
              </div>
            </div>
          </div>

          {/* What-If Widget */}
          <div className="card" style={{ padding: '2rem' }}>
            <h3 style={{ margin: '0 0 1.5rem 0' }}>What-If Analysis</h3>

            <div style={{ marginBottom: '1.5rem' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '0.5rem' }}>
                <label style={{ fontWeight: 500 }}>Reported Income</label>
                <span style={{ color: 'var(--primary)', fontWeight: 600 }}>${income.toLocaleString()}</span>
              </div>
              <input
                type="range"
                min="20000" max="250000" step="5000"
                value={income}
                onChange={e => handleIncomeChange(parseInt(e.target.value))}
                style={{ width: '100%' }}
              />
            </div>

            <div>
              <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '0.5rem' }}>
                <label style={{ fontWeight: 500 }}>Credit Amount</label>
                <span style={{ color: 'var(--primary)', fontWeight: 600 }}>${creditAmount.toLocaleString()}</span>
              </div>
              <input
                type="range"
                min="10000" max="1000000" step="10000"
                value={creditAmount}
                onChange={e => handleLoanChange(parseInt(e.target.value))}
                style={{ width: '100%' }}
              />
            </div>
          </div>
        </div>

        {/* Right Column */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '2rem' }}>

          {/* SHAP Chart */}
          <div className="card" style={{ padding: '2rem', flex: 1 }}>
            <h3 style={{ margin: '0 0 1rem 0' }}>Feature Contributions (SHAP Values)</h3>
            <p style={{ color: 'var(--text-secondary)', marginBottom: '2rem', fontSize: '0.875rem' }}>
              Displays how specific variables drove the neural network's final decision. Red increases risk, green decreases it.
            </p>
            {shapValues.length === 0 ? (
              <div style={{ textAlign: 'center', color: 'var(--text-secondary)', padding: '2rem' }}>
                Adjust sliders to generate SHAP attribution.
              </div>
            ) : (
              <div style={{ width: '100%', height: 300 }}>
                <ResponsiveContainer>
                  <BarChart data={shapValues} layout="vertical" margin={{ left: 50 }}>
                    <CartesianGrid strokeDasharray="3 3" horizontal={false} />
                    <XAxis type="number" />
                    <YAxis type="category" dataKey="feature" width={100} />
                    <Tooltip formatter={(value: number) => value.toFixed(3)} />
                    <Bar dataKey="value" radius={[0, 4, 4, 0]}>
                      {shapValues.map((entry, index) => (
                        <Cell key={`cell-${index}`} fill={entry.value > 0 ? 'var(--danger)' : 'var(--success)'} />
                      ))}
                    </Bar>
                  </BarChart>
                </ResponsiveContainer>
              </div>
            )}
          </div>

          {/* AI Explanation */}
          <div className="card" style={{ padding: '2rem' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.5rem' }}>
              <h3 style={{ margin: 0 }}>AI Analyst Explanation</h3>
              <button className="btn-primary" onClick={handleGenerateExplanation} disabled={loadingExpl}>
                {loadingExpl ? 'Generating...' : 'Generate New Report'}
              </button>
            </div>

            <div style={{
              background: '#f8fafc',
              padding: '1.5rem',
              borderRadius: '0.5rem',
              border: '1px solid var(--border-color)',
              minHeight: '100px',
            }}>
              {explanation ? (
                <p style={{ lineHeight: 1.6, margin: 0 }}>{explanation}</p>
              ) : (
                <p style={{ color: 'var(--text-secondary)', margin: 0, fontStyle: 'italic', textAlign: 'center' }}>
                  Click "Generate New Report" to query GPT-4 for a plain-English translation of this applicant's deep-learning risk profile.
                </p>
              )}
            </div>
          </div>

        </div>
      </div>
    </>
  );
}
