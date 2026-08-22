"use client";

import { FormEvent, useEffect, useRef, useState } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

type Source = { document_id: string; file_name: string | null; index: number | null };
type Message = { role: "user" | "assistant"; content: string; sources?: Source[] };

const initialMessage: Message = {
  role: "assistant",
  content: "Your knowledge base is ready. Ask a precise question and I will trace the answer back to the source passages.",
};

export default function Home() {
  const [messages, setMessages] = useState<Message[]>([initialMessage]);
  const [query, setQuery] = useState("");
  const [busy, setBusy] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [notice, setNotice] = useState("");
  const [collections, setCollections] = useState<string[]>([]);
  const [selectedCollection, setSelectedCollection] = useState("");
  const [loadingCollections, setLoadingCollections] = useState(true);
  const fileRef = useRef<HTMLInputElement>(null);

  async function refreshCollections() {
    setLoadingCollections(true);
    try {
      const response = await fetch("/api/collections", { cache: "no-store" });
      const payload = await response.json();
      if (!response.ok) throw new Error(payload.detail || "Collections could not be loaded.");
      setCollections(payload.collections);
      setSelectedCollection((current) => current || payload.collections[0] || "");
    } catch (error) {
      setNotice(error instanceof Error ? error.message : "Collections could not be loaded.");
    } finally { setLoadingCollections(false); }
  }

  useEffect(() => {
    const controller = new AbortController();
    fetch("/api/collections", { cache: "no-store", signal: controller.signal })
      .then(async (response) => {
        const payload = await response.json();
        if (!response.ok) throw new Error(payload.detail || "Collections could not be loaded.");
        setCollections(payload.collections);
        setSelectedCollection((current) => current || payload.collections[0] || "");
      })
      .catch((error) => {
        if (!controller.signal.aborted) setNotice(error instanceof Error ? error.message : "Collections could not be loaded.");
      })
      .finally(() => {
        if (!controller.signal.aborted) setLoadingCollections(false);
      });
    return () => controller.abort();
  }, []);

  async function submitQuery(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const trimmedQuery = query.trim();
    if (!trimmedQuery || busy || !selectedCollection) return;
    setMessages((current) => [...current, { role: "user", content: trimmedQuery }]);
    setQuery("");
    setBusy(true);
    setNotice("");
    try {
      const response = await fetch("/api/query", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ query: trimmedQuery, collection_name: selectedCollection }) });
      const payload = await response.json();
      if (!response.ok) throw new Error(payload.detail || "The query could not be completed.");
      setMessages((current) => [...current, { role: "assistant", content: payload.answer, sources: payload.sources }]);
    } catch (error) {
      setNotice(error instanceof Error ? error.message : "The query could not be completed.");
    } finally { setBusy(false); }
  }

  async function uploadDocument(event: React.ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0];
    if (!file) return;
    if (!/\.(pdf|txt)$/i.test(file.name)) { setNotice("Choose a PDF or plain text document."); return; }
    if (file.size > 20 * 1024 * 1024) { setNotice("Documents must be smaller than 20 MiB."); return; }
    setUploading(true); setNotice("");
    const formData = new FormData(); formData.append("file", file);
    try {
      const response = await fetch("/api/ingest", { method: "POST", body: formData });
      const payload = await response.json();
      if (!response.ok) throw new Error(payload.detail || "The document could not be indexed.");
      setNotice(`${file.name} indexed in ${payload.collection_name}.`);
      await refreshCollections();
    } catch (error) {
      setNotice(error instanceof Error ? error.message : "The document could not be indexed.");
    } finally { setUploading(false); if (fileRef.current) fileRef.current.value = ""; }
  }

  return (
    <main className="app-shell">
      <header className="topbar"><div className="brand-lockup"><span className="brand-mark">IQ</span><div><p className="eyebrow">Document intelligence</p><h1>AgentIQ</h1></div></div><div className="status-chip"><span /> Knowledge base online</div></header>
      <section className="workspace-heading"><div><p className="eyebrow">Operator workspace / 01</p><h2>Ask better questions<br /><em>of your documents.</em></h2></div><p className="heading-note">Retrieval-led answers with a visible trail back to the source.</p></section>
      <section className="workspace-grid">
        <div className="chat-panel panel"><div className="panel-header"><div><p className="panel-kicker">Live conversation</p><h3>Research desk</h3></div><span className="model-label">Gemini / RAG</span></div><section className="collection-picker" aria-label="Uploaded books"><div className="collection-heading"><span className="message-meta">Choose a book</span><span className="collection-count">{collections.length.toString().padStart(2, "0")} indexed</span></div>{loadingCollections ? <p className="collection-empty">Loading your library...</p> : collections.length === 0 ? <p className="collection-empty">Upload a document to start your library.</p> : <div className="collection-list">{collections.map((collection) => <button className={selectedCollection === collection ? "collection-item selected" : "collection-item"} type="button" key={collection} onClick={() => setSelectedCollection(collection)}><span className="book-spine" /><span>{collection}</span><b>{selectedCollection === collection ? "Selected" : "Select"}</b></button>)}</div>}</section><div className="message-list">
          {messages.map((message, index) => <article className={`message ${message.role}`} key={`${message.role}-${index}`}><div className="message-meta">{message.role === "assistant" ? "AGENTIQ" : "YOU"}</div>{message.role === "assistant" ? <div className="answer-markdown"><ReactMarkdown remarkPlugins={[remarkGfm]}>{message.content}</ReactMarkdown></div> : <p>{message.content}</p>}{message.sources && message.sources.length > 0 && <div className="inline-sources">{message.sources.map((source) => <span key={source.document_id}>{source.file_name || "Source"} - chunk {source.index ?? "-"}</span>)}</div>}</article>)}
          {busy && <article className="message assistant"><div className="message-meta">AGENTIQ</div><p className="typing">Searching the knowledge base<span>.</span><span>.</span><span>.</span></p></article>}
        </div><form className="composer" onSubmit={submitQuery}><textarea value={query} onChange={(event) => setQuery(event.target.value)} placeholder={selectedCollection ? `Ask about ${selectedCollection}...` : "Select a book to begin..."} rows={2} disabled={busy || !selectedCollection} /><button type="submit" disabled={busy || !query.trim() || !selectedCollection}>{busy ? "Working" : "Send question"} <span>↗</span></button></form></div>
        <aside className="side-column"><div className="upload-panel panel"><div className="panel-header"><div><p className="panel-kicker">Knowledge base</p><h3>Add a document</h3></div><span className="plus-mark">+</span></div><p className="panel-copy">Drop a PDF or text file into the index. AgentIQ will split it, embed it, and make it searchable.</p><button className="upload-button" type="button" onClick={() => fileRef.current?.click()} disabled={uploading}>{uploading ? "Indexing document..." : "Choose document"}<span>↑</span></button><input ref={fileRef} type="file" accept=".pdf,.txt" onChange={uploadDocument} hidden /><p className="file-note">PDF or TXT · max 20 MiB</p></div><div className="evidence-panel panel"><div className="panel-header"><div><p className="panel-kicker">How it works</p><h3>Evidence first</h3></div><span className="index-number">02</span></div><ol className="process-list"><li><span>01</span><p><strong>Retrieve</strong> Find the closest passages by meaning.</p></li><li><span>02</span><p><strong>Compose</strong> Ground the response in those passages.</p></li><li><span>03</span><p><strong>Trace</strong> Keep the source trail attached to the answer.</p></li></ol></div></aside>
      </section>
      {notice && <div className="notice" role="status">{notice}<button type="button" onClick={() => setNotice("")}>×</button></div>}
      <footer><span>AGENTIQ / PRIVATE RESEARCH DESK</span><span>SECURE OPERATOR MODE</span></footer>
    </main>
  );
}
