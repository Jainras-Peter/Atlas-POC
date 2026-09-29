import { RefObject } from "react";
import QuoteCard from "../QuoteCard";
import QuotesTable from "../QuotesTable";
import UserCard from "../UserCard";
import { unwrapAssistantContent } from "../../lib/unwrapContent";
import type { ChatMessage } from "../../types";
import ApprovalCard from "./ApprovalCard";
import CompanyResultsCard from "./CompanyResultsCard";
import CustomerResultsCard from "./CustomerResultsCard";
import Markdown from "./Markdown";

type Props = {
  messages: ChatMessage[];
  busy: boolean;
  onSelectCompany?: (companyId: string) => void;
  onApprove?: (messageId: string) => void;
  onReject?: (messageId: string) => void;
  bottomRef: RefObject<HTMLDivElement>;
};

export default function ChatTranscript({
  messages,
  busy,
  onSelectCompany,
  onApprove,
  onReject,
  bottomRef,
}: Props) {
  return (
    <div className="atlas-transcript">
      {messages.map((message) => (
        <div key={message.id} className={`bubble ${message.role}`}>
          {message.role !== "status" && (
            <div className="bubble-label">
              {message.role === "user" ? "You" : "Atlas"}
            </div>
          )}
          {message.role === "assistant" ? (
            <>
              {message.content ? (
                <Markdown content={unwrapAssistantContent(message.content)} />
              ) : null}
              {message.user && <UserCard user={message.user} />}
              {message.quote && <QuoteCard quote={message.quote} />}
              {message.quotes && message.quotes.length > 0 && (
                <QuotesTable
                  quotes={message.quotes}
                  customerId={message.quotesCustomer?.id}
                  email={message.quotesCustomer?.email}
                />
              )}
              {message.companies && message.companies.length > 0 && (
                <CompanyResultsCard
                  companies={message.companies}
                  onSelect={onSelectCompany}
                />
              )}
              {message.customers && message.customers.length > 0 && (
                <CustomerResultsCard customers={message.customers} />
              )}
              {message.approval && !message.approvalResolved && (
                <ApprovalCard
                  approval={message.approval}
                  disabled={busy}
                  onApprove={() => onApprove?.(message.id)}
                  onReject={() => onReject?.(message.id)}
                />
              )}
              {message.approval && message.approvalResolved && (
                <p className="muted approval-resolved">Decision submitted.</p>
              )}
            </>
          ) : (
            <div>{message.content}</div>
          )}
        </div>
      ))}
      {busy && <div className="bubble status">Working…</div>}
      <div ref={bottomRef} />
    </div>
  );
}
