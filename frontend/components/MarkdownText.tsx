import ReactMarkdown from "react-markdown";
export function MarkdownText({ children }: { children: string }) {
  return (
    <div className="prose-lite">
      <ReactMarkdown>{children || "No details provided."}</ReactMarkdown>
    </div>
  );
}
