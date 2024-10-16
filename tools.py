import json

retrieval_activator = {
    "type": "function",
    "function": {
        "name": "retrieval_activator",
        "description": "Decides whether or not more information should be retrieved to answer the question",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "The question about Ultimate Frisbee rules"
                },
                "history": {
                    "type": "object",
                    "description": "The conversation history"
                }
            },
            "required": ["query", "history"]
        }
    }
}

query_rewrite_activator = {
    "type": "function",
    "function": {
        "name": "query_rewrite_activator",
        "description": "Determines if the query contains enough information to use the retriever or if it should be rewritten base on past messages",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "The question about Ultimate Frisbee rules"
                },
                "history": {
                    "type": "object",
                    "description": "The conversation history"
                }
            },
            "required": ["query", "history"]
        }
    }
}

query_rewriter = {
    "type": "function",
    "function": {
        "name": "query_rewrite_activator",
        "description": "Rewrites the query if it is not enough to answer the question",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "The question about Ultimate Frisbee rules"
                },
                "history": {
                    "type": "object",
                    "description": "The conversation history"
                }
            },
            "required": ["query", "history"]
        }
    }
}


retriever = {
    "type": "function",
    "function": {
        "name": "retriever",
        "description": "Retrieves information about Ultimate frisbee from a rules database",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "The question about Ultimate Frisbee rules"
                }
            },
            "required": ["query"]
        }
    }
}

answer_question = {
    "type": "function",
    "function": {
        "name": "answer_question",
        "description": "Answers questions about Ultimate Frisbee rules using the context in the conversation history",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "The question about Ultimate Frisbee rules"
                }
            },
            "required": ["query"]
        }
    }
}
tools = {
    "retrieval_activator": retrieval_activator,
    "query_rewrite_activator": query_rewrite_activator,
    "query_rewriter": query_rewriter,
    "retriever": retriever,
    "answer_question": answer_question
}

def get_tool_definitions(tools_to_use):
    return {tool: tools[tool] for tool in tools_to_use}


# tools_to_use = ["retrieval_activator", "query_rewrite_activator"]
# print(json.dumps(get_tool_definitions(tools_to_use), indent=2))


