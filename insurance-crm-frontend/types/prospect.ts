export type ProspectType = 'individual' | 'business';
export type ProspectStatus = 'new' | 'contacted' | 'qualified' | 'quoted' | 'negotiation' | 'won' | 'lost';
export type RiskCategory = 'low' | 'medium' | 'high';

export interface Prospect {
  id: number;
  type: ProspectType;
  first_name?: string;
  last_name?: string;
  business_name?: string;
  birth_date?: string;
  email: string;
  phone: string;
  tax_code?: string;
  vat_number?: string;
  status: ProspectStatus;
  risk_category: RiskCategory;
  notes?: string;
  assigned_broker_id?: number;
  created_at: string;
  updated_at: string;
}

export interface CreateProspectRequest {
  type: ProspectType;
  first_name?: string;
  last_name?: string;
  business_name?: string;
  birth_date?: string;
  email: string;
  phone: string;
  tax_code?: string;
  vat_number?: string;
  risk_category: RiskCategory;
  notes?: string;
}
