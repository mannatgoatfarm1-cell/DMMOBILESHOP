import { useCallback, useEffect, useState } from "react";
import { MessageCircle, Send, X } from "lucide-react";
import { api, apiError } from "@/api";
import { toast } from "sonner";

export function CustomerLiveChat({ user, hidden = false, collapsed = false }) {
  const [open, setOpen] = useState(false); const [messages, setMessages] = useState([]); const [text, setText] = useState("");
  const load = useCallback(() => api.get("/api/chat/thread").then(({ data }) => setMessages(data.messages)).catch(() => {}), []);
  useEffect(() => { if (user && user.role !== "admin") setOpen(!collapsed); }, [user, collapsed]);
  useEffect(() => { if (!user || user.role === "admin" || !open) return; load(); const timer = setInterval(load, 1000); return () => clearInterval(timer); }, [user, open, load]);
  const send = async (event) => { event.preventDefault(); if (!text.trim()) return; try { await api.post("/api/chat/messages", { message: text }); setText(""); load(); } catch (error) { toast.error(apiError(error)); } };
  if (hidden || !user || user.role === "admin") return null;
  return <aside className={`customer-chat ${open ? "open" : ""}`} data-testid="customer-live-chat"><button className="chat-fab" onClick={() => setOpen((value) => !value)} aria-expanded={open} data-testid="customer-chat-toggle">{open ? <X size={19} /> : <MessageCircle size={19} />}<span>Live support</span></button>{open && <div className="chat-panel"><header><b>DM Mobile Support</b><small>Usually replies within minutes</small></header><div className="chat-messages" data-testid="customer-chat-messages">{messages.length ? messages.map((item) => <p className={item.sender_role} key={item.id}><span>{item.message}</span><small>{item.sender_role === "admin" ? "Support" : "You"}</small></p>) : <p className="chat-empty">Hello! Ask us about your order, return or payment.</p>}</div><form onSubmit={send}><input value={text} onChange={(event) => setText(event.target.value)} placeholder="Type your message" data-testid="customer-chat-input" /><button data-testid="customer-chat-send"><Send size={15} /></button></form></div>}</aside>;
}

export function AdminChatManager({ query = "" }) {
  const [threads, setThreads] = useState([]); const [selected, setSelected] = useState(null); const [messages, setMessages] = useState([]); const [text, setText] = useState("");
  const load = useCallback(() => api.get("/api/admin/chats").then(({ data }) => setThreads(data)).catch((error) => { if (error?.response?.status !== 401) toast.error(apiError(error)); }), []);
  useEffect(() => { load(); const timer = setInterval(load, 1000); return () => clearInterval(timer); }, [load]);
  const open = async (thread) => { setSelected(thread); const { data } = await api.get(`/api/admin/chats/${thread.id}`); setMessages(data.messages); };
  useEffect(() => { if (!selected) return; const timer = setInterval(() => api.get(`/api/admin/chats/${selected.id}`).then(({ data }) => setMessages(data.messages)).catch(() => {}), 1000); return () => clearInterval(timer); }, [selected]);
  const send = async (event) => { event.preventDefault(); if (!selected || !text.trim()) return; try { await api.post(`/api/admin/chats/${selected.id}/messages`, { message: text }); setText(""); open(selected); } catch (error) { toast.error(apiError(error)); } };
  const visible = threads.filter((thread) => `${thread.user_name} ${thread.user_email}`.toLowerCase().includes(query.toLowerCase()));
  return <section className="admin-chat" data-testid="admin-chat-manager"><div className="admin-panel chat-thread-list"><div className="panel-head"><div><h2>Live customer chat</h2><span>{visible.length} active conversations</span></div></div>{visible.map((thread) => <button key={thread.id} className={selected?.id === thread.id ? "active" : ""} onClick={() => open(thread)} data-testid={`open-chat-${thread.id}`}><b>{thread.user_name}</b><small>{thread.user_email}</small></button>)}</div><div className="admin-panel chat-conversation">{selected ? <><div className="panel-head"><div><h2>{selected.user_name}</h2><span>Live conversation</span></div></div><div className="chat-messages">{messages.map((item) => <p className={item.sender_role} key={item.id}><span>{item.message}</span><small>{item.sender_role === "admin" ? "You" : selected.user_name}</small></p>)}</div><form onSubmit={send}><input value={text} onChange={(event) => setText(event.target.value)} placeholder="Write a reply" data-testid="admin-chat-input" /><button className="primary-btn" data-testid="admin-chat-send">Send</button></form></> : <p className="admin-empty-copy">Select a customer conversation.</p>}</div></section>;
}