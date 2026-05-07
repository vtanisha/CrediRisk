const BASE_URL = (import.meta.env.VITE_API_URL as string | undefined) || 'http://localhost:8000';

export interface Customer {
  id: number;
  name: string;
  age: number;
  income: number;
  loan_amount: number;
  employment_type: string;
  credit_score: number;
  risk_tier: string;
  default_probability: number;
  notes?: string;
}

export interface ShapValue {
  feature_name: string;
  contribution: number;
}

export interface CustomerDetail extends Customer {
  shap_values: ShapValue[];
}

export interface PredictionResult {
  new_default_probability: number;
  delta: number;
  mock_shap_values: ShapValue[];
}

export interface PortfolioAnalytics {
  risk_distribution: { tier: string; count: number }[];
  income_histogram: { bucket: string; count: number }[];
  default_probability_distribution: { bucket: string; count: number }[];
  avg_default_probability: number;
  total_customers: number;
  high_risk_percentage: number;
}

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE_URL}${path}`, {
    headers: { 'Content-Type': 'application/json' },
    ...options,
  });
  if (!res.ok) {
    const text = await res.text();
    throw new Error(`API ${res.status}: ${text}`);
  }
  return res.json() as Promise<T>;
}

export const api = {
  fetchCustomers: (skip = 0, limit = 100) =>
    request<Customer[]>(`/customers?skip=${skip}&limit=${limit}`),

  fetchCustomer: (id: number) =>
    request<CustomerDetail>(`/customers/${id}`),

  predictWhatIf: (customerId: number, income?: number, loanAmount?: number) =>
    request<PredictionResult>('/predict/whatif', {
      method: 'POST',
      body: JSON.stringify({ customer_id: customerId, income, loan_amount: loanAmount }),
    }),

  chat: (customerId: number, query: string) =>
    request<{ reply: string }>('/chat', {
      method: 'POST',
      body: JSON.stringify({ customer_id: customerId, query }),
    }),

  fetchPortfolioAnalytics: () =>
    request<PortfolioAnalytics>('/analytics/portfolio'),

  getWsUrl: (customerId: number) =>
    `${BASE_URL.replace(/^http/, 'ws')}/ws/predict/${customerId}`,
};
