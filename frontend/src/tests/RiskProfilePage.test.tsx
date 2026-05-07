import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import RiskProfilePage from '../pages/RiskProfilePage';
import * as client from '../api/client';

vi.mock('../api/client', () => ({
  api: {
    fetchCustomers: vi.fn(),
    fetchCustomer: vi.fn(),
    predictWhatIf: vi.fn(),
    chat: vi.fn(),
    fetchPortfolioAnalytics: vi.fn(),
    getWsUrl: vi.fn(() => 'ws://localhost:8000/ws/predict/1'),
  },
}));

// Mock WebSocket
vi.stubGlobal('WebSocket', class {
  onopen: (() => void) | null = null;
  onmessage: ((e: MessageEvent) => void) | null = null;
  onclose: (() => void) | null = null;
  onerror: (() => void) | null = null;
  readyState = 1; // OPEN
  send = vi.fn();
  close = vi.fn();
});

const mockCustomer = {
  id: 1,
  name: 'Alice Test',
  age: 30,
  income: 60000,
  loan_amount: 200000,
  employment_type: 'Employed',
  credit_score: 650,
  risk_tier: 'Medium',
  default_probability: 0.45,
  notes: null,
  shap_values: [
    { feature_name: 'Income', contribution: -0.12 },
    { feature_name: 'Loan Amount', contribution: 0.25 },
    { feature_name: 'Age', contribution: -0.05 },
    { feature_name: 'Credit Score', contribution: -0.08 },
  ],
};

function renderPage(search = '?id=1&name=Alice%20Test') {
  return render(
    <MemoryRouter initialEntries={[`/risk-profile${search}`]}>
      <Routes>
        <Route path="/risk-profile" element={<RiskProfilePage />} />
      </Routes>
    </MemoryRouter>
  );
}

describe('RiskProfilePage', () => {
  beforeEach(() => {
    vi.mocked(client.api.fetchCustomer).mockResolvedValue(mockCustomer as any);
  });

  it('displays customer name in page title', async () => {
    renderPage();
    await waitFor(() => expect(screen.getByText(/Alice Test/i)).toBeInTheDocument());
  });

  it('shows probability from loaded customer', async () => {
    renderPage();
    await waitFor(() => expect(screen.getByText('45%')).toBeInTheDocument());
  });

  it('renders SHAP chart container', async () => {
    renderPage();
    await waitFor(() => screen.getByText(/Feature Contributions/i));
    expect(screen.getByText(/SHAP Values/i)).toBeInTheDocument();
  });

  it('shows AI explanation button', async () => {
    renderPage();
    await waitFor(() => screen.getByText(/Generate New Report/i));
    expect(screen.getByRole('button', { name: /Generate New Report/i })).toBeInTheDocument();
  });

  it('shows error when customer not found', async () => {
    vi.mocked(client.api.fetchCustomer).mockRejectedValue(new Error('Customer not found'));
    renderPage('?id=999');
    await waitFor(() => expect(screen.getByText(/Error loading customer/i)).toBeInTheDocument());
  });
});
