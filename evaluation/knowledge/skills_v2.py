"""Knowledge v2: the platform vocabulary plus non-technical domains.

Why: error analysis (validation) showed most missed Good Fit pairs come from accounting/finance and CRM jobs, where
the platform's (technical) vocabulary recognises almost no required skill. The terms below are standard skill names of
those professions and of other common non-technical jobs, written from domain knowledge, not taken from validation data.
Their coverage is measured on the training jobs only (coverage_check in knowledge.py).
"""
EXTRA: dict[str, list[str]] = {
    # accounting and finance
    "gaap": ["gaap", "us gaap", "generally accepted accounting principles"], "ifrs": ["ifrs"],
    "cpa": ["cpa", "certified public accountant"], "cma": ["cma", "certified management accountant"],
    "general ledger": ["general ledger", "gl accounting", "gl reconciliation"],
    "reconciliation": ["reconciliation", "reconciliations", "account reconciliation", "bank reconciliation"],
    "accounts payable": ["accounts payable", "a/p"], "accounts receivable": ["accounts receivable", "a/r"],
    "month-end close": ["month-end close", "month end close", "month-end", "year-end close", "financial close"],
    "financial reporting": ["financial reporting", "financial statements", "financial statement preparation"],
    "audit": ["audit", "auditing", "internal audit", "external audit"], "tax": ["tax", "taxation", "tax returns", "tax compliance"],
    "budgeting": ["budgeting", "forecasting", "budget preparation", "fp&a", "financial planning"],
    "payroll": ["payroll"], "bookkeeping": ["bookkeeping"], "cost accounting": ["cost accounting", "job costing"],
    "journal entries": ["journal entries", "journal entry", "accruals"], "fixed assets": ["fixed assets", "depreciation"],
    "sox": ["sox", "sarbanes-oxley", "internal controls"], "quickbooks": ["quickbooks"], "netsuite": ["netsuite"],
    "erp": ["erp", "oracle financials", "sap fico", "dynamics 365", "microsoft dynamics"],
    "financial analysis": ["financial analysis", "variance analysis", "financial modeling", "financial modelling"],
    "construction accounting": ["construction accounting", "wip schedule", "percentage of completion"],
    # CRM, Salesforce and sales operations
    "salesforce": ["salesforce", "sfdc", "salesforce.com"], "apex": ["apex"], "lightning": ["lightning web components", "lwc", "salesforce lightning"],
    "vlocity": ["vlocity", "salesforce industries", "communications cloud", "omnistudio"],
    "service cloud": ["service cloud"], "sales cloud": ["sales cloud"], "soql": ["soql"],
    "hubspot": ["hubspot"], "lead generation": ["lead generation", "prospecting", "pipeline management"],
    "account management": ["account management", "client relationship", "key accounts"],
    # management and business
    "stakeholder management": ["stakeholder management", "stakeholder engagement"],
    "people management": ["people management", "team leadership", "managing teams", "direct reports"],
    "strategic planning": ["strategic planning", "business strategy"], "operations management": ["operations management"],
    "business analysis": ["business analysis", "requirements gathering", "business requirements"],
    "process improvement": ["process improvement", "lean six sigma", "six sigma", "continuous improvement"],
    "risk management": ["risk management", "risk assessment"], "compliance": ["compliance", "regulatory compliance"],
    "vendor management": ["vendor management", "procurement", "purchasing"], "supply chain": ["supply chain", "logistics", "inventory management"],
    "hr": ["human resources", "recruiting", "talent acquisition", "onboarding", "employee relations", "hris"],
    "customer success": ["customer success", "client success"],
    # engineering and construction
    "autocad": ["autocad"], "solidworks": ["solidworks"], "revit": ["revit"], "plc": ["plc", "programmable logic controller"],
    "electrical engineering": ["electrical engineering", "electrical design", "power systems"],
    "mechanical engineering": ["mechanical engineering", "mechanical design"], "civil engineering": ["civil engineering"],
    "construction management": ["construction management", "project scheduling", "primavera"],
    "embedded": ["embedded systems", "embedded software", "firmware", "rtos"], "c/c++": ["c/c++"],
    "qa": ["quality assurance", "qa testing", "test automation"],
    # healthcare, legal, education, design
    "healthcare": ["healthcare", "clinical", "patient care", "hipaa", "ehr", "epic systems"],
    "legal": ["litigation", "paralegal", "contract management"], "teaching": ["teaching", "curriculum"],
    "adobe": ["adobe", "photoshop", "illustrator", "indesign", "adobe creative suite"],
    "microsoft office": ["microsoft office", "ms office", "microsoft word", "powerpoint"],
    "data entry": ["data entry"],
}
