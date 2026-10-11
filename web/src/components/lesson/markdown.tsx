import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

/** Lesson explanations. Content is authored in the repo, and react-markdown never renders raw HTML. */
export function Markdown({ children }: { children: string }) {
  return (
    <div className="prose-lesson">
      <ReactMarkdown remarkPlugins={[remarkGfm]}>{children}</ReactMarkdown>
    </div>
  );
}
