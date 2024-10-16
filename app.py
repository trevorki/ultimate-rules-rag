from fasthtml.fastapp import *
from fasthtml.common import *
from ultimate_rag import RagChat, ultimate_rules_chat
import markdown2
from markupsafe import Markup
import json

app = FastHTMLWithLiveReload(live=True)
chat = RagChat(server=False, user_message_memory_size=3, n_results=4)

@app.route("/")
def get():
    return Titled("", 
        Div(
            Div(
                H1("Ultimate Rules Q&A", cls="text-4xl font-bold mb-4 text-green-600"),
                P("Ask questions about ultimate rules!", cls="mb-6 text-lg"),
                cls="flex-none"
            ),
            Div(
                Div(id="chat-history", cls="space-y-4 p-4 flex flex-col"),
                cls="flex-1 overflow-y-auto border border-gray-300 rounded-lg bg-white mb-4"
            ),
            Form(
                Input(type="text", name="question", placeholder="Enter your question here", 
                      cls="w-full p-2 border border-gray-300 rounded-md"),
                Button("Submit", type="submit", 
                       cls="mt-2 px-4 py-2 bg-green-500 text-white rounded-md float-right"),
                id="question-form",
                cls="flex-none"
            ),
            cls="max-w-3xl mx-auto p-6 flex flex-col h-screen"
        ),
        Script("""
            var chatHistory = document.getElementById('chat-history');
            
            function scrollToBottom() {
                chatHistory.scrollTop = chatHistory.scrollHeight;
            }

            document.getElementById('question-form').addEventListener('submit', function(event) {
                event.preventDefault();
                var question = this.question.value;
                
                // Add user message
                var userMessage = document.createElement('div');
                userMessage.className = 'flex justify-end mb-4 slide-up';
                userMessage.innerHTML = '<div class="bg-blue-100 p-4 rounded-lg inline-block max-w-[80%] text-lg">' + question + '</div>';
                chatHistory.appendChild(userMessage);
                scrollToBottom();
                
                // Send question to server and get AI response
                fetch('/answer', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({question: question}),
                })
                .then(response => response.json())
                .then(data => {
                    var aiMessage = document.createElement('div');
                    aiMessage.className = 'flex justify-start mb-4 slide-up';
                    aiMessage.innerHTML = '<div class="bg-green-100 p-4 rounded-lg inline-block max-w-[80%] text-lg">' + marked.parse(data.answer) + '</div>';
                    chatHistory.appendChild(aiMessage);
                    scrollToBottom();
                });
                
                this.question.value = '';
            });

            // Initial scroll to bottom
            scrollToBottom();
        """),
        Style("""
            @keyframes slideUp {
                from { transform: translateY(20px); opacity: 0; }
                to { transform: translateY(0); opacity: 1; }
            }
            .slide-up {
                animation: slideUp 0.3s ease-out;
            }
            #chat-history {
                display: flex;
                flex-direction: column;
                justify-content: flex-end;
            }
        """),
        Script(src="https://cdn.jsdelivr.net/npm/marked/marked.min.js"),
        Link(rel="stylesheet", href="https://cdn.jsdelivr.net/npm/tailwindcss@2.2.19/dist/tailwind.min.css")
    )
    

@app.route("/answer", methods=["POST"])
async def post(request):
    try:
        body = await request.body()
        data = json.loads(body)
        if data and 'question' in data:
            question = data['question']
            question = chat.query_rewriter(question)
            print(f"\nQuery Rewriter: {question}")
            
            context = chat.retriever(question)
            print(f"Question: {question}")

            chat.history.update("user", question)
            chat.history.update("assistant", "I am retrieving some information to help answer the question")
            chat.history.update("tool", f"Here is some context: {context}", name = "get_context")

            answer = chat.answer_question(question)
            chat.history.update("assistant", answer)

            print(f"\nAnswer: {answer}")
            return JSONResponse({"answer": answer})
        else:
            return JSONResponse({"error": "Invalid request"}, status_code=400)
    except json.JSONDecodeError:
        return JSONResponse({"error": "Invalid JSON"}, status_code=400)
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)

@app.route("/reset")
def reset():
    chat.history = RagChat.ConversationHistory(user_message_memory_size=3)
    return "Chat history reset."

if __name__ == "__main__":
    app.run(debug=True)