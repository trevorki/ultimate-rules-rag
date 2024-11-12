from fasthtml.common import *
from ultimate_rules_rag.clients.get_abstract_client import get_abstract_client
from ultimate_rules_rag.rag_chat_session import RagChatSession

# Initialize the chat session
client = get_abstract_client(model="claude-3-5-sonnet-20241022")
session = RagChatSession(
    llm_client=client,
    stream_output=True,
    memory_size=3,
    context_size=1
)

retriever_kwargs = {
    "limit": 5,
    "expand_context": 0,
    "search_type": "hybrid",
    "fts_operator": "OR"
}

# Setup app with DaisyUI and loading indicator styles
hdrs = (
    Link(rel="stylesheet", href="https://cdn.jsdelivr.net/npm/daisyui@4.7.2/dist/full.css", type="text/css"),
    Script(src="https://cdn.tailwindcss.com"),
    Script(src="https://cdn.jsdelivr.net/npm/marked/marked.min.js"),
    Script("""
        marked.setOptions({
            breaks: true,
            gfm: true
        });
        
        function parseMarkdown(element) {
            if (element.classList.contains('markdown')) {
                element.innerHTML = marked.parse(element.textContent);
            }
        }
        
        function scrollToBottom() {
            const messages = document.querySelector('.messages');
            messages.scrollTop = messages.scrollHeight;
        }

        // Theme management
        document.addEventListener('DOMContentLoaded', function() {
            // Check for saved theme preference or default to system preference
            const savedTheme = localStorage.getItem('theme');
            if (savedTheme) {
                document.documentElement.setAttribute('data-theme', savedTheme);
            } else {
                // Check system preference
                const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
                document.documentElement.setAttribute('data-theme', prefersDark ? 'dark' : 'light');
            }
        });
        
        function toggleTheme() {
            const currentTheme = document.documentElement.getAttribute('data-theme');
            const newTheme = currentTheme === 'dark' ? 'light' : 'dark';
            document.documentElement.setAttribute('data-theme', newTheme);
            localStorage.setItem('theme', newTheme);
        }
        
        document.addEventListener('htmx:afterSettle', function(evt) {
            const markdownElements = evt.detail.elt.querySelectorAll('.markdown');
            markdownElements.forEach(parseMarkdown);
            scrollToBottom();
        });

        function appendStream(content) {
            const messagesDiv = document.querySelector('#messages');
            const lastMessage = messagesDiv.querySelector('.chat-bubble:last-child');
            
            if (lastMessage) {
                const currentContent = lastMessage.textContent;
                lastMessage.textContent = currentContent + content;
                
                // Parse markdown for the updated content
                if (lastMessage.classList.contains('markdown')) {
                    lastMessage.innerHTML = marked.parse(lastMessage.textContent);
                }
                scrollToBottom();
            }
        }
        
        // Add event listener for SSE
        document.body.addEventListener('stream-response', function(e) {
            if (e.detail === '[DONE]') return;
            appendStream(e.detail);
        });
    """),
    Style("""
        body {
            background-color: #2A3630;
            color: #E8E4D9;
        }
        h1 {
            font-size: 2.5rem;
            text-align: center;
            margin: 1rem 0;
            font-weight: bold;
        }
        .chat-container {
            height: calc(100vh - 100px);
            display: flex;
            flex-direction: column;
            background-color: #2A3630;
        }
        .messages {
            flex-grow: 1;
            overflow-y: auto;
            padding: 1rem;
        }
        .input-area {
            padding: 1rem;
            background: #1F2924;
            border-top: 1px solid #3A463F;
        }
        .chat-bubble-primary {
            background-color: #E8B4B8 !important;
            color: #1F2924 !important;
        }
        .chat-bubble-secondary {
            background-color: #E8E4D9 !important;
            color: #1F2924 !important;
        }
        .chat-header {
            color: #E8E4D9;
        }
        .input {
            background-color: #3A463F !important;
            color: #E8E4D9 !important;
            border-color: #4A564F !important;
        }
        .input::placeholder {
            color: #8A968F !important;
        }
        .btn-primary {
            background-color: #E8B4B8 !important;
            border-color: #E8B4B8 !important;
            color: #1F2924 !important;
        }
        .btn-primary:hover {
            background-color: #D9A5A9 !important;
            border-color: #D9A5A9 !important;
        }
        
        /* Loading indicator styles */
        .typing {
            display: flex;
            gap: 5px;
            padding: 10px 15px;
        }
        .typing-dot {
            width: 8px;
            height: 8px;
            background-color: var(--text-color);
            border-radius: 50%;
            animation: typing 1.0s infinite;
            opacity: 0.7;
        }
        .typing-dot:nth-child(2) { animation-delay: 0.1s; }
        .typing-dot:nth-child(3) { animation-delay: 0.2s; }
        
        @keyframes typing {
            0%, 100% { transform: translateY(0); }
            50% { transform: translateY(-4px); }
        }

        /* Hide loading indicator by default */
        .loading-indicator {
            display: none;
        }
        /* Show when htmx is requesting */
        .htmx-request #typing-indicator {
            display: block;
        }
        /* Hide form during request */
        .htmx-request .input-form {
            display: none;
        }

        /* Markdown styles */
        .chat-bubble.markdown ul {
            list-style-type: disc;
            margin-left: 1.5em;
            margin-top: 0.5em;
            margin-bottom: 0.5em;
        }
        .chat-bubble.markdown p {
            margin-bottom: 0.5em;
        }
        .chat-bubble.markdown code {
            background-color: rgba(0, 0, 0, 0.1);
            padding: 0.2em 0.4em;
            border-radius: 3px;
        }

        /* Light mode colors */
        :root[data-theme="light"] {
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
        :root[data-theme="dark"] {
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
            background-color: var(--bg-color);
        }

        .input-area {
            background: var(--input-area-bg);
            border-top: 1px solid var(--input-area-border);
        }

        .chat-bubble-primary {
            background-color: var(--chat-primary) !important;
            color: var(--chat-primary-text) !important;
        }

        .chat-bubble-secondary {
            background-color: var(--chat-secondary) !important;
            color: var(--chat-secondary-text) !important;
        }

        .chat-header {
            color: var(--text-color);
        }

        .input {
            background-color: var(--input-bg) !important;
            color: var(--text-color) !important;
            border-color: var(--input-border) !important;
        }

        .input::placeholder {
            color: var(--text-color) !important;
            opacity: 0.5;
        }

        /* Theme toggle button styles */
        .theme-toggle {
            position: fixed;
            top: 1rem;
            right: 1rem;
            padding: 0.5rem 1rem;
            border-radius: 0.5rem;
            background: var(--input-bg);
            border: 1px solid var(--input-border);
            color: var(--text-color);
            cursor: pointer;
            transition: all 0.2s;
            z-index: 100;
        }

        .theme-toggle:hover {
            opacity: 0.8;
        }

        /* Update typing indicator colors */
        .typing-dot {
            background-color: var(--text-color);
        }
    """),
    Script(src="https://unpkg.com/htmx.org/dist/ext/sse.js"),
)

app = FastHTMLWithLiveReload(hdrs=hdrs, debug=True)

def LoadingIndicator():
    """Create a typing indicator"""
    return Div(
        Div(
            Div(cls="typing-dot"),
            Div(cls="typing-dot"),
            Div(cls="typing-dot"),
            cls="typing"
        ),
        cls="chat chat-start",
    )

def ChatMessage(role: str, content: str):
    """Create a chat message bubble"""
    chat_class = "chat-end" if role == "user" else "chat-start"
    bubble_class = "chat-bubble-primary" if role == "user" else "chat-bubble-secondary"
    markdown_class = " markdown" if role == "assistant" else ""
    
    return Div(
        Div(role.title(), cls="chat-header"),
        Div(content, 
            cls=f"chat-bubble {bubble_class}{markdown_class}"
        ),
        cls=f"chat {chat_class}"
    )

@app.get("/")
def home():
    messages = Div(
        Button("Toggle Theme", 
            cls="theme-toggle",
            onclick="toggleTheme()"
        ),
        Div(
            ChatMessage("assistant", "Hi! I'm Cal, your ultimate rules assistant. Ask me anything about ultimate!"),
            Div(LoadingIndicator(), id="typing-indicator", cls="loading-indicator"),
            id="messages",
            cls="messages"
        ),
        Div(
            Form(
                Input(
                    type="text",
                    name="message",
                    placeholder="Ask a question about ultimate...",
                    cls="input input-bordered w-full",
                    id="message-input",
                    required=True,
                    minlength=2
                ),
                Button("Send", cls="btn btn-primary ml-2"),
                cls="flex gap-2",
                hx_post="/chat",
                hx_target="#messages",
                hx_swap="beforeend",
                hx_indicator="#typing-indicator"
            ),
            cls="input-area"
        ),
        cls="chat-container"
    )
    
    return Title("UltiRules Chat"), Main(H1("UltiRules Chat"), messages)

@app.post("/chat")
def chat(message: str):
    return (
        ChatMessage("user", message),
        Div(LoadingIndicator(), id="current-loading"),
        Div(
            hx_ext="sse",
            sse_connect=f"/chat_response?message={message}",
            sse_swap="beforeend",
            hx_target="#messages",
            id="sse-listener"
        ),
        Input(
            type="text",
            name="message",
            placeholder="Ask a question about ultimate...",
            cls="input input-bordered w-full",
            id="message-input",
            required=True,
            minlength=2,
            value="",
            hx_swap_oob="true"
        )
    )

@app.get("/chat_response")
async def chat_response(message: str):
    from fastapi.responses import StreamingResponse
    
    async def generate():
        # First chunk removes loading indicator and adds empty message
        # Combine the elements into a single Div
        initial_content = Div(
            Script("document.getElementById('current-loading').remove();"),
            ChatMessage("assistant", "")
        )
        yield f"data: {initial_content}\n\n"
        
        # Stream the answer
        answer_stream = session.answer_question(message, retriever_kwargs=retriever_kwargs)
        for chunk in answer_stream:
            # Escape any script tags to prevent XSS
            chunk = chunk.replace("<script>", "&lt;script&gt;").replace("</script>", "&lt;/script&gt;")
            yield f"data: {chunk}\n\n"
        print(f"Answer: {chunk}")
        
        yield "data: [DONE]\n\n"
        
        # Wrap the final script in a Div
        cleanup = Div(Script("document.getElementById('sse-listener').remove();"))
        yield f"data: {cleanup}\n\n"
    
    return StreamingResponse(
        generate(),
        media_type="text/event-stream"
    )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=5000)