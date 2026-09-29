import { Component, ReactNode } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

type Props = {
  content: string;
};

type State = { failed: boolean };

/** Renders Markdown; falls back to plain text if remark crashes mid-stream. */
export default class Markdown extends Component<Props, State> {
  state: State = { failed: false };

  static getDerivedStateFromError() {
    return { failed: true };
  }

  componentDidUpdate(prev: Props) {
    if (prev.content !== this.props.content && this.state.failed) {
      this.setState({ failed: false });
    }
  }

  render(): ReactNode {
    if (this.state.failed) {
      return <div className="assistant-text">{this.props.content}</div>;
    }
    return (
      <div className="md-body">
        <ReactMarkdown remarkPlugins={[remarkGfm]}>
          {this.props.content}
        </ReactMarkdown>
      </div>
    );
  }
}
