from fasthtml import FastHTML
from fasthtml.common import *
from ultimate_rules_rag.rag_chat_session import RagChatSession
from ultimate_rules_rag.clients.get_abstract_client import get_abstract_client
import asyncio

# DaisyUI and custom styling
headers = (
    Script(src="https://cdn.tailwindcss.com"),
    Link(rel="stylesheet", href="https://cdn.jsdelivr.net/npm/daisyui@latest/dist/full.min.css"),
    Script(src="https://cdn.jsdelivr.net/npm/marked/marked.min.js"),
    Style("""
        /* Light mode colors */
        [data-theme="light"] {
            --bg-color: #F5F5F5;
            --text-color: #2A3630;
            --input-bg: #FFFFFF;
            --input-border: #D1D5DB;
            --chat-primary: #E8B4B8;
            --chat-primary-text: #1F2924;
            --chat-secondary: #FFFFFF;
            --chat-secondary-text: #2A3630;
            --header-bg: #FFFFFF;
            --input-area-bg: #FFFFFF;
            --input-area-border: #E5E7EB;
        }

        /* Dark mode colors */
        [data-theme="dark"] {
            --bg-color: #2A3630;
            --text-color: #E8E4D9;
            --input-bg: #3A463F;
            --input-border: #4A564F;
            --chat-primary: #8B4F52;
            --chat-primary-text: #E8E4D9;
            --chat-secondary: #3A463F;
            --chat-secondary-text: #E8E4D9;
            --header-bg: #1F2924;
            --input-area-bg: #1F2924;
            --input-area-border: #3A463F;
        }

        body { 
            background-color: var(--bg-color);
            color: var(--text-color);
        }
        .chat-container {
            height: calc(100vh - 120px);
            overflow-y: auto;
            padding: 1rem;
        }
        .input-area {
            position: fixed;
            bottom: 0;
            left: 0;
            right: 0;
            padding: 1rem;
            background: var(--input-area-bg);
            border-top: 1px solid var(--input-area-border);
        }
        .chat-start .chat-bubble {
            background: var(--chat-secondary);
            color: var(--chat-secondary-text);
        }
        .chat-end .chat-bubble {
            background: var(--chat-primary);
            color: var(--chat-primary-text);
        }
        .header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 1rem;
            background: var(--header-bg);
            border-bottom: 1px solid var(--input-area-border);
        }

        /* Add styles for markdown content */
        .chat-bubble ul, .chat-bubble ol {
            list-style: revert;
            margin: revert;
            padding: revert;
        }
        .chat-bubble p {
            margin: 0.5em 0;
        }
        .chat-bubble strong {
            font-weight: bold;
        }
    """),
    Script("""
        function toggleTheme() {
            const html = document.documentElement;
            const currentTheme = html.getAttribute('data-theme');
            const newTheme = currentTheme === 'light' ? 'dark' : 'light';
            html.setAttribute('data-theme', newTheme);
            localStorage.setItem('theme', newTheme);
        }

        // Set initial theme from localStorage or system preference
        document.addEventListener('DOMContentLoaded', function() {
            const savedTheme = localStorage.getItem('theme');
            if (savedTheme) {
                document.documentElement.setAttribute('data-theme', savedTheme);
            } else {
                const systemTheme = window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
                document.documentElement.setAttribute('data-theme', systemTheme);
            }
        });
    """),
    Script("""
        function renderMarkdown(element) {
            if (element && element.classList.contains('chat-bubble')) {
                const text = element.textContent;
                element.innerHTML = marked.parse(text);
            }
        }

        // Process existing messages
        document.addEventListener('DOMContentLoaded', function() {
            document.querySelectorAll('.chat-bubble').forEach(renderMarkdown);
        });

        // Process new messages from streaming
        htmx.on("htmx:afterRequest", function(evt) {
            if (evt.detail.pathInfo.requestPath === "/chat") {
                const assistantMsg = document.getElementById('current-response');
                if (assistantMsg) {
                    const eventSource = new EventSource("/stream?message=" + encodeURIComponent(evt.detail.requestConfig.parameters.message));
                    
                    assistantMsg.removeAttribute('id');
                    let accumulatedText = '';
                    
                    eventSource.onmessage = function(e) {
                        accumulatedText += e.data;
                        assistantMsg.innerHTML = marked.parse(accumulatedText);
                        scrollToBottom();
                    };
                    
                    eventSource.onerror = function() {
                        eventSource.close();
                        assistantMsg.removeAttribute('id');
                        scrollToBottom();
                    };
                }
            }
            scrollToBottom();
        });
    """)
)

app = FastHTML(hdrs=headers)

def ChatMessage(msg, role="assistant", message_id=None):
    """Create a chat message bubble"""
    return Div(
        Div(msg, cls="chat-bubble", id=message_id),
        cls=f"chat chat-{'end' if role == 'user' else 'start'}"
    )

def ChatBox(messages):
    """Create the chat container with messages"""
    return Div(
        *[ChatMessage(msg["content"], msg["role"]) for msg in messages],
        cls="chat-container",
        id="chat-container"
    )

def InputArea():
    """Create the input area with form"""
    return Div(
        Form(
            Input(
                type="text",
                name="message",
                placeholder="Ask a question about Ultimate rules...",
                cls="w-full p-2 rounded border",
                id="message-input",
                autocomplete="off",
                required=True,
                minlength="2"
            ),
            Button(
                "Send",
                type="submit",
                cls="ml-2 px-4 py-2 rounded bg-blue-500 text-white"
            ),
            cls="flex gap-2",
            hx_post="/chat",
            hx_target="#chat-container",
            hx_swap="beforeend"
        ),
        cls="input-area"
    )

def Header():
    return Div(
        H1("Ultimate Rules Assistant", cls="text-2xl font-bold"),
        Button(
            "🌓", 
            onclick="toggleTheme()",
            cls="px-4 py-2 rounded bg-opacity-20 hover:bg-opacity-30 transition-colors"
        ),
        cls="header"
    )

@app.get("/")
def home():
    return Title("Ultimate Rules Chat"), Main(
        Header(),
        ChatBox([]),
        InputArea(),
        Script("""
            function scrollToBottom() {
                const container = document.getElementById('chat-container');
                container.scrollTop = container.scrollHeight;
            }
            
            htmx.on("htmx:afterRequest", function(evt) {
                if (evt.detail.pathInfo.requestPath === "/chat") {
                    const assistantMsg = document.getElementById('current-response');
                    if (assistantMsg) {
                        const eventSource = new EventSource("/stream?message=" + encodeURIComponent(evt.detail.requestConfig.parameters.message));
                        
                        assistantMsg.removeAttribute('id');
                        
                        eventSource.onmessage = function(e) {
                            assistantMsg.innerHTML += e.data;
                            scrollToBottom();
                        };
                        
                        eventSource.onerror = function() {
                            eventSource.close();
                            assistantMsg.removeAttribute('id');
                            scrollToBottom();
                        };
                    }
                }
                scrollToBottom();
            });
        """)
    )

# Initialize RAG chat session
client = get_abstract_client(model="gpt-4o-mini")
retriever_kwargs = {
    "limit": 5,
    "expand_context": 0,
    "search_type": "hybrid",
    "fts_operator": "OR"
}
session = RagChatSession(
    llm_client=client,
    stream_output=True,
    memory_size=3,
    context_size=1
)

@app.post("/chat")
def chat(message: str):
    # Validate message server-side
    message = message.strip()
    if not message:
        return ""
        
    # Return messages and a cleared input with OOB swap
    return (
        ChatMessage(message, role="user"),
        ChatMessage("", role="assistant", message_id="current-response"),
        Input(
            type="text",
            name="message",
            placeholder="Ask a question about Ultimate rules...",
            cls="w-full p-2 rounded border",
            id="message-input",
            autocomplete="off",
            value="",
            hx_swap_oob="true"
        ),
        Script("scrollToBottom();")
    )

@app.get("/stream")
async def stream(message: str):
    response = session.answer_question(message, retriever_kwargs=retriever_kwargs)
    
    async def event_stream():
        try:
            for chunk in response:
                # Properly format as SSE data with newlines
                yield chunk
                # Add a small delay to ensure proper streaming
                await asyncio.sleep(0.01)
        except Exception as e:
            print(f"Streaming error: {e}")
            yield 'data: [Error generating response]\n\n'
    
    return EventSourceResponse(event_stream())

if __name__ == "__main__":
    import uvicorn
    from sse_starlette.sse import EventSourceResponse
    uvicorn.run(app, host="0.0.0.0", port=5000)
