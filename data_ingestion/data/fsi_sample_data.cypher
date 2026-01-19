// ============================================================
// Vandelay Financial Corporation - Knowledge Graph
// ============================================================
// 
// A focused FSI knowledge graph for demonstrating GraphRAG
// capabilities in banking compliance and risk management.
//
// Usage:
//   python -m data_ingestion.ingest_graph --clear
//
// ============================================================

// ============================================================
// 1. THE BANK
// ============================================================

CREATE (vandelay:Bank {
  id: 'BANK-001',
  name: 'Vandelay Financial Corporation',
  type: 'Commercial Bank',
  tier: 1,
  country: 'US',
  total_assets: 850000000000,
  headquarters: 'New York',
  founded: 1952
});

// ============================================================
// 2. REGULATORY FRAMEWORKS
// ============================================================

CREATE (basel:Regulation {
  id: 'REG-001',
  name: 'Basel III',
  framework: 'Basel',
  description: 'International regulatory framework for banks, focusing on capital adequacy, stress testing, and market liquidity risk.',
  requirements: 'Minimum CET1 4.5%, Tier 1 6%, Total Capital 8%, LCR 100%, NSFR 100%',
  effective_date: date('2013-01-01'),
  jurisdiction: 'International'
})

CREATE (aml:Regulation {
  id: 'REG-002',
  name: 'AML',
  framework: 'Anti-Money Laundering',
  description: 'Anti-Money Laundering regulations requiring financial institutions to detect and prevent money laundering activities.',
  requirements: 'Customer due diligence, transaction monitoring, suspicious activity reporting (SAR), record keeping for 5 years',
  effective_date: date('1970-01-01'),
  jurisdiction: 'International'
})

CREATE (kyc:Regulation {
  id: 'REG-003',
  name: 'KYC',
  framework: 'Know Your Customer',
  description: 'Know Your Customer requirements for verifying customer identity and assessing risk profiles.',
  requirements: 'Identity verification, risk assessment, ongoing monitoring, Enhanced Due Diligence (EDD) for high-risk customers',
  effective_date: date('2001-01-01'),
  jurisdiction: 'International'
})

CREATE (dodd:Regulation {
  id: 'REG-004',
  name: 'Dodd-Frank',
  framework: 'Dodd-Frank Act',
  description: 'US financial reform act for systemic risk oversight, consumer protection, and derivatives regulation.',
  requirements: 'Stress testing, Volcker Rule compliance, derivatives clearing, consumer protection',
  effective_date: date('2010-07-21'),
  jurisdiction: 'US'
})

CREATE (bsa:Regulation {
  id: 'REG-005',
  name: 'BSA',
  framework: 'Bank Secrecy Act',
  description: 'Requires US financial institutions to assist government agencies in detecting and preventing money laundering.',
  requirements: 'Currency Transaction Reports (CTR) for transactions over $10,000, SAR filing within 30 days',
  effective_date: date('1970-10-26'),
  jurisdiction: 'US'
});

// ============================================================
// 3. CUSTOMERS
// ============================================================

// Low-risk individual customer
CREATE (sarah:Customer {
  id: 'CUST-001',
  name: 'Sarah Chen',
  type: 'Individual',
  occupation: 'Software Engineer',
  annual_income: 185000,
  risk_level: 'Low',
  kyc_status: 'Verified',
  kyc_date: date('2022-03-15'),
  country: 'US',
  state: 'California'
})

// Medium-risk corporate customer
CREATE (techstart:Customer {
  id: 'CUST-002',
  name: 'TechStart Solutions LLC',
  type: 'Corporate',
  industry: 'Technology',
  annual_revenue: 12000000,
  risk_level: 'Medium',
  kyc_status: 'Verified',
  kyc_date: date('2023-06-20'),
  country: 'US',
  state: 'Texas',
  employees: 45
})

// High-risk offshore customer - KEY FOR AML DEMO
CREATE (oceanic:Customer {
  id: 'CUST-003',
  name: 'Oceanic Holdings Ltd',
  type: 'Corporate',
  industry: 'Import/Export',
  annual_revenue: 50000000,
  risk_level: 'High',
  kyc_status: 'Enhanced Due Diligence',
  kyc_date: date('2024-01-10'),
  country: 'Cyprus',
  beneficial_owner: 'Complex Structure - Multiple Jurisdictions',
  pep_associated: true,
  edd_reason: 'Offshore jurisdiction, complex ownership, PEP association'
})

// Another high-risk customer for pattern detection
CREATE (globalimport:Customer {
  id: 'CUST-004',
  name: 'Global Import Partners',
  type: 'Corporate',
  industry: 'Trading',
  annual_revenue: 25000000,
  risk_level: 'High',
  kyc_status: 'Enhanced Due Diligence',
  kyc_date: date('2024-02-05'),
  country: 'British Virgin Islands',
  beneficial_owner: 'Undisclosed',
  pep_associated: false,
  edd_reason: 'Tax haven jurisdiction, undisclosed beneficial ownership'
});

// ============================================================
// 4. ACCOUNTS
// ============================================================

CREATE (sarah_checking:Account {
  id: 'ACC-001',
  name: 'Sarah Chen - Personal Checking',
  type: 'Checking',
  balance: 45000.00,
  currency: 'USD',
  status: 'Active',
  opened_date: date('2022-03-15'),
  monthly_avg_balance: 38000
})

CREATE (sarah_savings:Account {
  id: 'ACC-002',
  name: 'Sarah Chen - Savings',
  type: 'Savings',
  balance: 125000.00,
  currency: 'USD',
  status: 'Active',
  opened_date: date('2022-03-15'),
  interest_rate: 4.5
})

CREATE (techstart_business:Account {
  id: 'ACC-003',
  name: 'TechStart Solutions - Business',
  type: 'Business Checking',
  balance: 850000.00,
  currency: 'USD',
  status: 'Active',
  opened_date: date('2023-06-20'),
  monthly_avg_balance: 720000
})

CREATE (oceanic_corp:Account {
  id: 'ACC-004',
  name: 'Oceanic Holdings - Corporate',
  type: 'Corporate',
  balance: 15000000.00,
  currency: 'USD',
  status: 'Under Review',
  opened_date: date('2023-08-10'),
  monthly_avg_balance: 8500000
})

CREATE (globalimport_corp:Account {
  id: 'ACC-005',
  name: 'Global Import - Corporate',
  type: 'Corporate',
  balance: 3200000.00,
  currency: 'USD',
  status: 'Under Review',
  opened_date: date('2023-11-01'),
  monthly_avg_balance: 2100000
});

// ============================================================
// 5. TRANSACTIONS
// ============================================================

// Normal transaction - Sarah paycheck
CREATE (txn1:Transaction {
  id: 'TXN-001',
  type: 'Direct Deposit',
  amount: 12500.00,
  currency: 'USD',
  date: datetime('2024-01-15T08:00:00'),
  description: 'Payroll - Tech Corp Inc',
  counterparty: 'Tech Corp Inc',
  status: 'Completed',
  channel: 'ACH'
})

// Normal transaction - TechStart vendor payment
CREATE (txn2:Transaction {
  id: 'TXN-002',
  type: 'Wire Transfer',
  amount: 45000.00,
  currency: 'USD',
  date: datetime('2024-01-16T10:30:00'),
  description: 'Cloud services payment - AWS',
  counterparty: 'Amazon Web Services',
  status: 'Completed',
  channel: 'Wire'
})

// FLAGGED - Oceanic suspicious wire
CREATE (txn3:Transaction {
  id: 'TXN-003',
  type: 'Wire Transfer',
  amount: 2500000.00,
  currency: 'USD',
  date: datetime('2024-01-17T14:45:00'),
  description: 'Trade settlement',
  counterparty: 'Meridian Trading FZE',
  counterparty_country: 'UAE',
  status: 'Flagged',
  flag_reason: 'Large wire to high-risk jurisdiction, inconsistent with account history',
  channel: 'SWIFT',
  risk_score: 85
})

// FLAGGED - Oceanic structuring pattern
CREATE (txn4:Transaction {
  id: 'TXN-004',
  type: 'Wire Transfer',
  amount: 9800.00,
  currency: 'USD',
  date: datetime('2024-01-18T09:15:00'),
  description: 'Consulting fee',
  counterparty: 'Cyprus Consulting Group',
  counterparty_country: 'Cyprus',
  status: 'Flagged',
  flag_reason: 'Potential structuring - amount just below $10,000 CTR threshold',
  channel: 'Wire',
  risk_score: 75
})

// FLAGGED - Link between high-risk customers
CREATE (txn5:Transaction {
  id: 'TXN-005',
  type: 'Wire Transfer',
  amount: 750000.00,
  currency: 'USD',
  date: datetime('2024-01-19T11:30:00'),
  description: 'Investment transfer',
  counterparty: 'Global Import Partners',
  counterparty_country: 'British Virgin Islands',
  status: 'Flagged',
  flag_reason: 'Transfer between two high-risk entities, circular flow pattern detected',
  channel: 'SWIFT',
  risk_score: 92
})

// Normal - Sarah mortgage payment
CREATE (txn6:Transaction {
  id: 'TXN-006',
  type: 'Bill Payment',
  amount: 2850.00,
  currency: 'USD',
  date: datetime('2024-01-20T06:00:00'),
  description: 'Monthly mortgage payment',
  counterparty: 'Vandelay Mortgage Services',
  status: 'Completed',
  channel: 'ACH'
});

// ============================================================
// 6. FINANCIAL PRODUCTS
// ============================================================

CREATE (mortgage30:Product {
  id: 'PROD-001',
  name: 'Fixed Rate Mortgage 30Y',
  type: 'Mortgage',
  category: 'Lending',
  interest_rate: 6.75,
  term_years: 30,
  min_amount: 100000,
  max_amount: 2000000,
  description: 'Traditional 30-year fixed rate mortgage for residential properties'
})

CREATE (mortgage15:Product {
  id: 'PROD-002',
  name: 'Fixed Rate Mortgage 15Y',
  type: 'Mortgage',
  category: 'Lending',
  interest_rate: 6.0,
  term_years: 15,
  min_amount: 50000,
  max_amount: 1500000,
  description: '15-year fixed rate mortgage with lower total interest cost'
})

CREATE (heloc:Product {
  id: 'PROD-003',
  name: 'Home Equity Line of Credit',
  type: 'HELOC',
  category: 'Lending',
  interest_rate: 8.5,
  max_ltv: 85,
  min_amount: 25000,
  max_amount: 500000,
  description: 'Flexible credit line secured by home equity'
})

CREATE (businessloan:Product {
  id: 'PROD-004',
  name: 'Small Business Term Loan',
  type: 'Business Loan',
  category: 'Commercial Lending',
  interest_rate: 9.25,
  term_years: 5,
  min_amount: 50000,
  max_amount: 5000000,
  description: 'Term financing for small and medium businesses'
})

CREATE (savingsacct:Product {
  id: 'PROD-005',
  name: 'High-Yield Savings',
  type: 'Deposit',
  category: 'Deposits',
  interest_rate: 4.5,
  min_balance: 1000,
  fdic_insured: true,
  description: 'Competitive interest savings account'
});

// ============================================================
// 7. PORTFOLIOS & RISK
// ============================================================

CREATE (mortgage_portfolio:Portfolio {
  id: 'PORT-001',
  name: 'Residential Mortgage Portfolio',
  type: 'Lending',
  total_value: 2500000000,
  num_loans: 12500,
  avg_loan_size: 200000,
  delinquency_rate: 2.3
})

CREATE (commercial_portfolio:Portfolio {
  id: 'PORT-002',
  name: 'Commercial Lending Portfolio',
  type: 'Commercial',
  total_value: 850000000,
  num_loans: 340,
  avg_loan_size: 2500000,
  delinquency_rate: 1.8
})

CREATE (credit_risk:Risk {
  id: 'RISK-001',
  category: 'credit_risk',
  name: 'Credit Risk',
  description: 'Risk of loss from borrower or counterparty default',
  current_exposure: 125000000,
  risk_score: 62
})

CREATE (aml_risk:Risk {
  id: 'RISK-002',
  category: 'aml_risk',
  name: 'AML/BSA Risk',
  description: 'Risk of money laundering or terrorist financing through bank services',
  current_exposure: 18500000,
  risk_score: 78,
  high_risk_customers: 2
})

CREATE (operational_risk:Risk {
  id: 'RISK-003',
  category: 'operational_risk',
  name: 'Operational Risk',
  description: 'Risk of loss from failed internal processes, people, or systems',
  current_exposure: 45000000,
  risk_score: 35
})

CREATE (liquidity_risk:Risk {
  id: 'RISK-004',
  category: 'liquidity_risk',
  name: 'Liquidity Risk',
  description: 'Risk of inability to meet short-term financial obligations',
  current_exposure: 200000000,
  risk_score: 28
});

// ============================================================
// 8. EXTERNAL COUNTERPARTIES (for derivative/trading exposure)
// ============================================================

CREATE (meridian:Counterparty {
  id: 'CP-001',
  name: 'Meridian Trading FZE',
  type: 'Trading Company',
  country: 'UAE',
  risk_rating: 'High',
  sanction_status: 'Clear',
  last_reviewed: date('2024-01-15'),
  notes: 'Received flagged wire from Oceanic Holdings'
})

CREATE (cyprusgroup:Counterparty {
  id: 'CP-002',
  name: 'Cyprus Consulting Group',
  type: 'Consulting',
  country: 'Cyprus',
  risk_rating: 'Medium',
  sanction_status: 'Clear',
  last_reviewed: date('2024-01-10')
});

// ============================================================
// 9. RELATIONSHIPS
// ============================================================

// Bank regulatory compliance
MATCH (v:Bank {name: 'Vandelay Financial Corporation'}), (r:Regulation {name: 'Basel III'})
CREATE (v)-[:COMPLIES_WITH {status: 'Compliant', last_audit: date('2024-01-01'), next_audit: date('2025-01-01')}]->(r);

MATCH (v:Bank {name: 'Vandelay Financial Corporation'}), (r:Regulation {name: 'AML'})
CREATE (v)-[:COMPLIES_WITH {status: 'Compliant', last_audit: date('2024-01-01'), next_audit: date('2025-01-01')}]->(r);

MATCH (v:Bank {name: 'Vandelay Financial Corporation'}), (r:Regulation {name: 'KYC'})
CREATE (v)-[:COMPLIES_WITH {status: 'Compliant', last_audit: date('2024-01-01'), next_audit: date('2025-01-01')}]->(r);

MATCH (v:Bank {name: 'Vandelay Financial Corporation'}), (r:Regulation {name: 'Dodd-Frank'})
CREATE (v)-[:COMPLIES_WITH {status: 'Compliant', last_audit: date('2024-01-01'), next_audit: date('2025-01-01')}]->(r);

MATCH (v:Bank {name: 'Vandelay Financial Corporation'}), (r:Regulation {name: 'BSA'})
CREATE (v)-[:COMPLIES_WITH {status: 'Compliant', last_audit: date('2024-01-01'), next_audit: date('2025-01-01')}]->(r);

// Bank offers products
MATCH (v:Bank {name: 'Vandelay Financial Corporation'}), (p:Product)
CREATE (v)-[:OFFERS]->(p);

// Bank has portfolios
MATCH (v:Bank {name: 'Vandelay Financial Corporation'}), (p:Portfolio)
CREATE (v)-[:MANAGES]->(p);

// Bank has risk exposures
MATCH (v:Bank {name: 'Vandelay Financial Corporation'}), (r:Risk)
CREATE (v)-[:HAS_RISK]->(r);

// Customers are clients of bank
MATCH (v:Bank {name: 'Vandelay Financial Corporation'}), (c:Customer)
CREATE (c)-[:CUSTOMER_OF]->(v);

// Customer-Account ownership
MATCH (c:Customer {id: 'CUST-001'}), (a:Account {id: 'ACC-001'})
CREATE (c)-[:OWNS]->(a);

MATCH (c:Customer {id: 'CUST-001'}), (a:Account {id: 'ACC-002'})
CREATE (c)-[:OWNS]->(a);

MATCH (c:Customer {id: 'CUST-002'}), (a:Account {id: 'ACC-003'})
CREATE (c)-[:OWNS]->(a);

MATCH (c:Customer {id: 'CUST-003'}), (a:Account {id: 'ACC-004'})
CREATE (c)-[:OWNS]->(a);

MATCH (c:Customer {id: 'CUST-004'}), (a:Account {id: 'ACC-005'})
CREATE (c)-[:OWNS]->(a);

// Account-Transaction relationships
MATCH (a:Account {id: 'ACC-001'}), (t:Transaction {id: 'TXN-001'})
CREATE (a)-[:HAS_TRANSACTION]->(t);

MATCH (a:Account {id: 'ACC-001'}), (t:Transaction {id: 'TXN-006'})
CREATE (a)-[:HAS_TRANSACTION]->(t);

MATCH (a:Account {id: 'ACC-003'}), (t:Transaction {id: 'TXN-002'})
CREATE (a)-[:HAS_TRANSACTION]->(t);

MATCH (a:Account {id: 'ACC-004'}), (t:Transaction {id: 'TXN-003'})
CREATE (a)-[:HAS_TRANSACTION]->(t);

MATCH (a:Account {id: 'ACC-004'}), (t:Transaction {id: 'TXN-004'})
CREATE (a)-[:HAS_TRANSACTION]->(t);

MATCH (a:Account {id: 'ACC-004'}), (t:Transaction {id: 'TXN-005'})
CREATE (a)-[:HAS_TRANSACTION]->(t);

// Customer KYC compliance
MATCH (c:Customer), (r:Regulation {name: 'KYC'})
CREATE (c)-[:SUBJECT_TO]->(r);

// High-risk customers subject to AML
MATCH (c:Customer {risk_level: 'High'}), (r:Regulation {name: 'AML'})
CREATE (c)-[:SUBJECT_TO {reason: 'High-risk customer classification'}]->(r);

MATCH (c:Customer {risk_level: 'High'}), (r:Regulation {name: 'BSA'})
CREATE (c)-[:SUBJECT_TO {reason: 'Enhanced monitoring required'}]->(r);

// Flagged transactions linked to counterparties
MATCH (t:Transaction {id: 'TXN-003'}), (cp:Counterparty {name: 'Meridian Trading FZE'})
CREATE (t)-[:SENT_TO]->(cp);

MATCH (t:Transaction {id: 'TXN-004'}), (cp:Counterparty {name: 'Cyprus Consulting Group'})
CREATE (t)-[:SENT_TO]->(cp);

// Connection between high-risk customers (for circular flow detection)
MATCH (c1:Customer {id: 'CUST-003'}), (c2:Customer {id: 'CUST-004'})
CREATE (c1)-[:TRANSACTED_WITH {transaction_id: 'TXN-005', amount: 750000, date: date('2024-01-19')}]->(c2);

// Portfolio contains products
MATCH (p:Portfolio {id: 'PORT-001'}), (prod:Product {type: 'Mortgage'})
CREATE (p)-[:CONTAINS]->(prod);

MATCH (p:Portfolio {id: 'PORT-001'}), (prod:Product {type: 'HELOC'})
CREATE (p)-[:CONTAINS]->(prod);

MATCH (p:Portfolio {id: 'PORT-002'}), (prod:Product {type: 'Business Loan'})
CREATE (p)-[:CONTAINS]->(prod);

// Portfolio risk associations
MATCH (p:Portfolio {id: 'PORT-001'}), (r:Risk {category: 'credit_risk'})
CREATE (p)-[:EXPOSED_TO {exposure_amount: 75000000}]->(r);

MATCH (p:Portfolio {id: 'PORT-002'}), (r:Risk {category: 'credit_risk'})
CREATE (p)-[:EXPOSED_TO {exposure_amount: 50000000}]->(r);

// Sarah has a mortgage product
MATCH (c:Customer {id: 'CUST-001'}), (p:Product {id: 'PROD-001'})
CREATE (c)-[:HAS_PRODUCT {loan_amount: 450000, originated: date('2022-04-01'), rate: 5.5}]->(p);

// TechStart has a business loan
MATCH (c:Customer {id: 'CUST-002'}), (p:Product {id: 'PROD-004'})
CREATE (c)-[:HAS_PRODUCT {loan_amount: 250000, originated: date('2023-07-15'), rate: 8.75}]->(p);

// ============================================================
// 10. INDEXES
// ============================================================

CREATE INDEX customer_id IF NOT EXISTS FOR (c:Customer) ON (c.id);
CREATE INDEX customer_risk IF NOT EXISTS FOR (c:Customer) ON (c.risk_level);
CREATE INDEX account_id IF NOT EXISTS FOR (a:Account) ON (a.id);
CREATE INDEX transaction_id IF NOT EXISTS FOR (t:Transaction) ON (t.id);
CREATE INDEX transaction_status IF NOT EXISTS FOR (t:Transaction) ON (t.status);
CREATE INDEX regulation_name IF NOT EXISTS FOR (r:Regulation) ON (r.name);
CREATE INDEX product_type IF NOT EXISTS FOR (p:Product) ON (p.type);
CREATE INDEX portfolio_id IF NOT EXISTS FOR (p:Portfolio) ON (p.id);
CREATE INDEX counterparty_name IF NOT EXISTS FOR (cp:Counterparty) ON (cp.name);

RETURN 'Vandelay Financial Corporation Knowledge Graph Loaded Successfully' as status;
