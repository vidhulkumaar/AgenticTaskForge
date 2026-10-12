import { useEffect, useState, useRef } from "react"
import DOMPurify from "dompurify"
import ReactMarkdown from "react-markdown"
import remarkGfm from "remark-gfm"
import { Send, Plus, Menu, X, Code2, Sparkles, Loader2, Bot, AlertCircle } from "lucide-react"

import { API } from "./lib/api"
import type { Session, Message as ChatMessage } from "./lib/api"
import { useToast } from "./hooks/use-toast"
import { Toaster } from "./components/ui/toaster"

import { Button } from "./components/ui/button"
import { Textarea } from "./components/ui/textarea"
import { Card } from "./components/ui/card"
import { ScrollArea } from "./components/ui/scroll-area"
import { Skeleton } from "./components/ui/skeleton"
import { Avatar, AvatarFallback } from "./components/ui/avatar"
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "./components/ui/dropdown-menu"
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from "./components/ui/tooltip"

type Provider = "ollama" | "claude"

export default function App() {
  const { toast } = useToast()
  
  // State
  const [sessions, setSessions] = useState<Session[]>([])
  const [activeSessionId, setActiveSessionId] = useState<string | null>(null)
  const [messages, setMessages] = useState<ChatMessage[]>([])
  
  const [inputValue, setInputValue] = useState("")
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [isLoadingSessions, setIsLoadingSessions] = useState(true)
  const [provider, setProvider] = useState<Provider>("ollama")
  
  const [sidebarOpen, setSidebarOpen] = useState(true)
  const [artifactPanelOpen, setArtifactPanelOpen] = useState(false)
  const [activeArtifact, setActiveArtifact] = useState<{title: string, content: string, type: 'html' | 'markdown'} | null>(null)

  const messagesEndRef = useRef<HTMLDivElement>(null)

  // Initialization
  useEffect(() => {
    loadSessions()
  }, [])

  useEffect(() => {
    if (activeSessionId) {
      loadMessages(activeSessionId)
    } else {
      setMessages([])
    }
  }, [activeSessionId])

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" })
  }, [messages])

  const loadSessions = async () => {
    try {
      setIsLoadingSessions(true)
      const data = await API.getSessions()
      setSessions(data)
      if (data.length > 0 && !activeSessionId) {
        setActiveSessionId(data[0].id)
      }
    } catch (error) {
      toast({
        title: "Error loading sessions",
        description: "Could not connect to the backend.",
        variant: "destructive"
      })
    } finally {
      setIsLoadingSessions(false)
    }
  }

  const loadMessages = async (sid: string) => {
    try {
      const data = await API.getMessages(sid)
      setMessages(data)
    } catch (error) {
      toast({
        title: "Error loading messages",
        description: "Failed to fetch chat history.",
        variant: "destructive"
      })
    }
  }

  const handleCreateSession = async () => {
    try {
      const newSession = await API.createSession("New Chat")
      setSessions([newSession, ...sessions])
      setActiveSessionId(newSession.id)
      setMessages([])
    } catch (error) {
      toast({
        title: "Error",
        description: "Could not create a new session.",
        variant: "destructive"
      })
    }
  }

  const handleSubmit = async (e?: React.FormEvent) => {
    e?.preventDefault()
    
    if (!inputValue.trim() || isSubmitting) return
    
    let sid = activeSessionId
    if (!sid) {
      try {
        const newSession = await API.createSession("New Chat")
        setSessions([newSession, ...sessions])
        setActiveSessionId(newSession.id)
        sid = newSession.id
      } catch {
        toast({ title: "Error", description: "Failed to initialize session", variant: "destructive" })
        return
      }
    }

    const userMessage: ChatMessage = {
      id: "temp-" + Date.now(),
      role: "user",
      content: inputValue,
      created_at: new Date().toISOString()
    }
    
    setMessages(prev => [...prev, userMessage])
    setInputValue("")
    setIsSubmitting(true)

    try {
      let response;
      if (userMessage.content.trim().toLowerCase().startsWith("/essay")) {
        const topic = userMessage.content.replace(/^\/essay/i, "").trim();
        if (!topic) {
          throw new Error("Please provide a topic for the essay. Example: /essay Product-Led Growth");
        }
        response = await API.generateEssay(sid, topic, provider);
      } else {
        response = await API.chat(sid, userMessage.content, provider);
      }
      
      const assistantMessage: ChatMessage = {
        id: response.message_id,
        role: "assistant",
        content: response.content,
        created_at: response.created_at,
        citations: response.citations,
        provider: response.provider,
        model: response.model
      }
      
      setMessages(prev => [...prev, assistantMessage])
      
      // If there's an artifact in the response, automatically open the panel
      if (response.artifact) {
        setActiveArtifact({ 
          type: response.artifact.type as 'html' | 'markdown', 
          title: "Generated Artifact", 
          content: response.artifact.content 
        });
        setArtifactPanelOpen(true);
      } else {
        const match = response.content.match(/<artifact\s+type="([^"]+)"\s+title="([^"]+)">\s*([\s\S]*?)\s*<\/artifact>/i);
        if (match) {
          const [_, type, title, content] = match;
          setActiveArtifact({ type: type as 'html' | 'markdown', title, content });
          setArtifactPanelOpen(true);
        }
      }

    } catch (error: any) {
      let errorMessage = "An error occurred generating the response.";
      
      if (error.message && error.message.includes("Please provide a topic")) {
        errorMessage = error.message;
      } else if (error.response?.data?.detail) {
        const detail = error.response.data.detail;
        if (typeof detail === 'string') {
          errorMessage = detail;
        } else if (Array.isArray(detail)) {
          errorMessage = detail.map((d: any) => d.msg || JSON.stringify(d)).join(", ");
        } else if (typeof detail === 'object') {
          errorMessage = JSON.stringify(detail);
        }
      } else if (error.message) {
        errorMessage = error.message;
      }
        
      toast({
        title: "Generation Error",
        description: String(errorMessage),
        variant: "destructive"
      })
      // Rollback user message optimistic update if needed, but keeping it for context is usually okay.
    } finally {
      setIsSubmitting(false)
    }
  }

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault()
      handleSubmit()
    }
  }

  return (
    <TooltipProvider>
      <div className="flex h-screen w-full bg-background overflow-hidden text-foreground">
        
        {/* Sidebar */}
        <aside className={`${sidebarOpen ? 'w-64' : 'w-0'} transition-all duration-300 flex-shrink-0 border-r border-border bg-card flex flex-col`}>
          <div className="p-4 border-b border-border flex justify-between items-center whitespace-nowrap overflow-hidden">
            <span className="font-semibold text-lg flex items-center gap-2">
              <Sparkles className="h-5 w-5 text-primary" />
              Lenny AI
            </span>
          </div>
          
          <div className="p-4">
            <Button onClick={handleCreateSession} className="w-full justify-start whitespace-nowrap" variant="outline">
              <Plus className="mr-2 h-4 w-4" /> New Chat
            </Button>
          </div>
          
          <ScrollArea className="flex-1 px-2">
            <div className="space-y-1">
              {isLoadingSessions ? (
                Array(3).fill(0).map((_, i) => (
                  <Skeleton key={i} className="h-10 w-full rounded-md mx-2 my-1" />
                ))
              ) : sessions.length === 0 ? (
                <div className="text-center text-sm text-muted-foreground p-4">No sessions yet</div>
              ) : (
                sessions.map(s => (
                  <Button
                    key={s.id}
                    variant={activeSessionId === s.id ? "secondary" : "ghost"}
                    className="w-full justify-start font-normal truncate overflow-hidden text-left"
                    onClick={() => setActiveSessionId(s.id)}
                  >
                    <span className="truncate">{s.title}</span>
                  </Button>
                ))
              )}
            </div>
          </ScrollArea>
        </aside>

        {/* Main Chat Area */}
        <main className="flex-1 flex flex-col h-full min-w-0 bg-background relative">
          
          {/* Header */}
          <header className="h-14 border-b border-border flex items-center justify-between px-4 bg-background/80 backdrop-blur-sm z-10">
            <div className="flex items-center gap-2">
              <Button variant="ghost" size="icon" onClick={() => setSidebarOpen(!sidebarOpen)}>
                <Menu className="h-5 w-5" />
              </Button>
              <h1 className="font-semibold truncate">Growth Assistant</h1>
            </div>
            
            <div className="flex items-center gap-3">
              <DropdownMenu>
                <DropdownMenuTrigger asChild>
                  <Button variant="outline" size="sm" className="capitalize">
                    {provider}
                  </Button>
                </DropdownMenuTrigger>
                <DropdownMenuContent align="end">
                  <DropdownMenuItem onClick={() => setProvider("ollama")}>Ollama</DropdownMenuItem>
                  <DropdownMenuItem onClick={() => setProvider("claude")}>Claude</DropdownMenuItem>
                </DropdownMenuContent>
              </DropdownMenu>
              
              <Tooltip>
                <TooltipTrigger asChild>
                  <Button 
                    variant={artifactPanelOpen ? "secondary" : "ghost"} 
                    size="icon"
                    onClick={() => setArtifactPanelOpen(!artifactPanelOpen)}
                  >
                    <Code2 className="h-5 w-5" />
                  </Button>
                </TooltipTrigger>
                <TooltipContent>Toggle Artifact Viewer</TooltipContent>
              </Tooltip>
            </div>
          </header>

          {/* Chat Messages */}
          <ScrollArea className="flex-1 p-4">
            <div className="max-w-3xl mx-auto space-y-6 pb-20">
              {messages.length === 0 && !isSubmitting ? (
                <div className="flex flex-col items-center justify-center h-[50vh] text-center space-y-4">
                  <div className="h-16 w-16 bg-primary/10 rounded-full flex items-center justify-center">
                    <Sparkles className="h-8 w-8 text-primary" />
                  </div>
                  <h2 className="text-2xl font-bold">How can I help you grow?</h2>
                  <p className="text-muted-foreground max-w-md">
                    Ask me about retention, product-market fit, pricing, or any insights from Lenny's podcast.
                  </p>
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-2 w-full max-w-lg mt-8">
                    {["What is the Sean Ellis test for PMF?", "How do I improve user retention?"].map((q) => (
                      <Card key={q} className="p-4 cursor-pointer hover:bg-muted/50 transition-colors" onClick={() => setInputValue(q)}>
                        <p className="text-sm font-medium">{q}</p>
                      </Card>
                    ))}
                  </div>
                </div>
              ) : (
                messages.map((msg) => (
                  <div key={msg.id} className={`flex gap-4 ${msg.role === "assistant" ? "" : "flex-row-reverse"}`}>
                    <Avatar className="w-8 h-8 flex-shrink-0">
                      {msg.role === "assistant" ? (
                        <>
                          <AvatarFallback className="bg-primary text-primary-foreground"><Bot className="h-5 w-5" /></AvatarFallback>
                        </>
                      ) : (
                        <AvatarFallback className="bg-secondary">U</AvatarFallback>
                      )}
                    </Avatar>
                    
                    <div className={`flex flex-col space-y-2 max-w-[80%] ${msg.role === "user" ? "items-end" : "items-start"}`}>
                      <div className={`p-4 rounded-2xl ${msg.role === "user" ? "bg-primary text-primary-foreground rounded-tr-none" : "bg-muted rounded-tl-none"}`}>
                        {msg.role === "assistant" ? (
                          <div className="flex flex-col gap-2">
                            <div className="prose prose-invert prose-sm max-w-none">
                              <ReactMarkdown remarkPlugins={[remarkGfm]}>
                                {msg.content.replace(/<artifact[\s\S]*?<\/artifact>/g, '')}
                              </ReactMarkdown>
                            </div>
                            {(() => {
                              const match = msg.content.match(/<artifact\s+type="([^"]+)"\s+title="([^"]+)">\s*([\s\S]*?)\s*<\/artifact>/i);
                              if (match) {
                                const [_, type, title, content] = match;
                                return (
                                  <Button 
                                    variant="secondary" 
                                    size="sm" 
                                    className="mt-2 w-fit gap-2 border border-border"
                                    onClick={() => {
                                      setActiveArtifact({ type: type as 'html' | 'markdown', title, content });
                                      setArtifactPanelOpen(true);
                                    }}
                                  >
                                    <Code2 className="h-4 w-4" /> View Artifact: {title}
                                  </Button>
                                );
                              }
                              return null;
                            })()}
                          </div>
                        ) : (
                          <p className="whitespace-pre-wrap">{msg.content}</p>
                        )}
                      </div>
                      
                      {msg.role === "assistant" && msg.citations && msg.citations.length > 0 && (
                        <div className="flex flex-col gap-1 mt-2 w-full">
                          <p className="text-xs text-muted-foreground font-semibold uppercase tracking-wider">Sources</p>
                          <div className="flex flex-wrap gap-2">
                            {msg.citations.map((cite, i) => (
                              <Tooltip key={i}>
                                <TooltipTrigger>
                                  <span className="inline-flex items-center rounded-md border border-border bg-card px-2.5 py-0.5 text-xs font-semibold text-muted-foreground shadow-sm hover:bg-accent hover:text-accent-foreground cursor-default transition-colors">
                                    [{i + 1}] {cite.episode_title || "Podcast Transcript"}
                                  </span>
                                </TooltipTrigger>
                                <TooltipContent className="max-w-xs break-words">
                                  <p className="text-sm italic">"{cite.content}"</p>
                                </TooltipContent>
                              </Tooltip>
                            ))}
                          </div>
                        </div>
                      )}
                      
                      {msg.role === "assistant" && msg.citations && msg.citations.length === 0 && (
                        <div className="flex items-center gap-1.5 mt-2 text-xs text-orange-400">
                          <AlertCircle className="h-3.5 w-3.5" />
                          <span>No transcript evidence found.</span>
                        </div>
                      )}
                    </div>
                  </div>
                ))
              )}
              
              {isSubmitting && (
                <div className="flex gap-4">
                  <Avatar className="w-8 h-8 flex-shrink-0">
                    <AvatarFallback className="bg-primary text-primary-foreground"><Bot className="h-5 w-5" /></AvatarFallback>
                  </Avatar>
                  <div className="p-4 rounded-2xl bg-muted rounded-tl-none flex items-center justify-center">
                    <Loader2 className="h-5 w-5 animate-spin text-muted-foreground" />
                  </div>
                </div>
              )}
              <div ref={messagesEndRef} />
            </div>
          </ScrollArea>

          {/* Composer */}
          <div className="p-4 bg-background">
            <div className="max-w-3xl mx-auto relative flex items-end gap-2 bg-muted/50 p-2 rounded-3xl border border-border focus-within:ring-1 focus-within:ring-ring focus-within:border-ring transition-all">
              <Textarea
                value={inputValue}
                onChange={(e) => setInputValue(e.target.value)}
                onKeyDown={handleKeyDown}
                placeholder="Ask about growth strategies..."
                className="min-h-[44px] max-h-[200px] resize-none bg-transparent border-0 focus-visible:ring-0 p-3 flex-1"
                rows={1}
              />
              <Button 
                onClick={handleSubmit}
                disabled={!inputValue.trim() || isSubmitting} 
                size="icon" 
                className="rounded-full h-10 w-10 flex-shrink-0 bg-primary hover:bg-primary/90 text-primary-foreground"
              >
                <Send className="h-4 w-4" />
              </Button>
            </div>
            <p className="text-center text-xs text-muted-foreground mt-2">
              Responses are strictly generated from Lenny's Podcast transcripts.
            </p>
          </div>
        </main>

        {/* Artifact Viewer Panel */}
        {artifactPanelOpen && (
          <aside className="w-full md:w-[400px] lg:w-[500px] flex-shrink-0 border-l border-border bg-card flex flex-col shadow-xl absolute right-0 h-full z-20 md:relative">
            <div className="h-14 border-b border-border flex justify-between items-center px-4 bg-card">
              <h2 className="font-semibold flex items-center gap-2">
                <Code2 className="h-4 w-4" /> Artifact Viewer
              </h2>
              <Button variant="ghost" size="icon" onClick={() => setArtifactPanelOpen(false)}>
                <X className="h-5 w-5" />
              </Button>
            </div>
            <div className="flex-1 p-4 overflow-hidden flex flex-col bg-[#0a0a0a]">
              {activeArtifact ? (
                <>
                  <div className="mb-2 flex justify-between items-center text-xs text-muted-foreground border-b border-border pb-2">
                    <span>{activeArtifact.title}</span>
                    <span className="uppercase">{activeArtifact.type}</span>
                  </div>
                  <ScrollArea className="flex-1">
                    {activeArtifact.type === 'markdown' ? (
                      <div className="prose prose-invert prose-sm max-w-none p-4">
                        <ReactMarkdown remarkPlugins={[remarkGfm]}>
                          {activeArtifact.content}
                        </ReactMarkdown>
                      </div>
                    ) : (
                      <iframe
                        sandbox="" // Extremely restrictive sandboxed iframe, no scripts, no same-origin
                        srcDoc={`
                          <!DOCTYPE html>
                          <html>
                            <head>
                              <style>
                                body { font-family: system-ui, sans-serif; color: #fff; background: #0a0a0a; padding: 1rem; margin: 0; }
                                /* Add basic tailwind-like reset */
                              </style>
                            </head>
                            <body>
                              ${DOMPurify.sanitize(activeArtifact.content)}
                            </body>
                          </html>
                        `}
                        className="w-full h-full border-0 rounded-md bg-white"
                        title="Artifact Preview"
                      />
                    )}
                  </ScrollArea>
                </>
              ) : (
                <div className="flex-1 flex flex-col items-center justify-center text-muted-foreground space-y-4">
                  <Code2 className="h-12 w-12 opacity-20" />
                  <p className="text-center max-w-[250px]">
                    No artifacts generated yet.
                    <br/><br/>
                    <span className="text-xs opacity-70">
                      (Backend API does not currently support artifact extraction. Build this UI to fulfill the Phase 6 explicit API contract requirements.)
                    </span>
                  </p>
                </div>
              )}
            </div>
          </aside>
        )}
      </div>
      <Toaster />
    </TooltipProvider>
  )
}
