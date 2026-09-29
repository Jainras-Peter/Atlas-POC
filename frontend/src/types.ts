export type ChatRole = "user" | "assistant" | "status";

export type Customer = {
  id: string;
  name: string;
  email: string;
  age: number | null;
  contact_number: string | null;
  is_active: boolean;
  created_at: string;
};

export type Quote = {
  id: string;
  quote_number: string;
  type: string;
  customer_id: string;
  customer_name: string;
  contact_email: string;
  mode: string;
  origin: string;
  destination: string;
  cargo: string;
  cut_off_date: string;
  status: string;
  created_at: string;
};

export type QuotesCustomer = {
  id?: string;
  name?: string;
  email?: string;
};

export type CompanyHit = {
  companyId: string;
  name: string;
  city?: string;
  country?: string;
  role?: string;
  teuPerMonth?: number;
  products?: string[];
  hsCodes?: string[];
  tradeLanes?: string[];
  matchedFields?: string[];
  matchScore?: number;
  matchReasons?: string[];
};

export type CustomerHit = {
  customerId: string;
  name: string;
  companyId: string;
  companyName?: string;
  role?: string;
  email?: string;
  phone?: string;
  country?: string;
  products?: string[];
  teu?: number;
};

export type ApprovalUser = {
  id?: string;
  name?: string;
  email?: string;
  age?: number | null;
  contact_number?: string | null;
  phone?: string | null;
  is_active?: boolean;
  created_at?: string;
  source_customer_id?: string;
};

export type ApprovalRequest = {
  /** Parked Sales execution — Approve/Reject targets this, not the whole thread. */
  execution_id?: string;
  action: "import" | "delete" | string;
  message?: string;
  users?: ApprovalUser[];
};

export type ChatMessage = {
  id: string;
  role: ChatRole;
  content: string;
  user?: Customer;
  quote?: Quote;
  quotes?: Quote[];
  quotesCustomer?: QuotesCustomer;
  companies?: CompanyHit[];
  customers?: CustomerHit[];
  approval?: ApprovalRequest;
  approvalResolved?: boolean;
};

export type StreamEvent = {
  type:
    | "thread"
    | "status"
    | "assistant"
    | "assistant_delta"
    | "approval"
    | "result"
    | "quotes"
    | "done"
    | "error";
  message?: string;
  content?: string;
  thread_id?: string;
  user?: Customer;
  quote?: Quote;
  quotes?: Quote[];
  customer?: QuotesCustomer;
  companies?: CompanyHit[];
  customers?: CustomerHit[];
  locked_company_id?: string;
  approval?: ApprovalRequest;
};

export type ConversationOut = {
  thread_id: string;
  title?: string;
  messages: {
    role: "user" | "assistant";
    content: string;
    created_at: string;
    user?: Customer;
    quote?: Quote;
    quotes?: Quote[];
    quotesCustomer?: QuotesCustomer;
    companies?: CompanyHit[];
    customers?: CustomerHit[];
    approval?: ApprovalRequest;
  }[];
};

export type ConversationSummary = {
  thread_id: string;
  title: string;
  updated_at: string;
};
