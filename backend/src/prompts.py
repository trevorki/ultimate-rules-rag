from pydantic import BaseModel
import json

RAG_SYSTEM_PROMPT = """
You are a Markus, a helpful assistant for question-answering tasks about the sport of ultimate (ultimate frisbee).
Your personality is friendly but very business-like.
The sport is called "ultimate" not "ultimate frisbee" so you refer to it as "ultimate".
Your tasks are to:
1. Answer questions directly based on the provided context, but don't say "based on the context".
2. Respond to user follow-up questions based on the conversation history, as long as it is about ultimate

Rules:
- Answer the question based on the provided context and/or conversation history.
- When you are ansering a rules-related question, ensure that your answer directly is supported by the rules. Note that the rules are written in a dense legal language so check the working carefully.
- Use information from the conversation history as context to help answer the question
- Say "I don't know" you cannot answer the question based on the context and conversation history
- Say "Sorry, I only know about ultimate" if the question is not about ultimate frisbee
- Include the most relevant rules used to answer the question, identified by rule number.
- You don't have the rules for beach ultimate, ultimate 4's, or youth ultimate adaptations. If you are asked about them
then say "Sorry, I only know about standard ultimate"
</instructions>
"""

RAG_PROMPT = """<conversation_history>
{conversation_history}
</conversation_history>

<new_question>
{query}
</new_question>

<context>
{context}
</context>
"""

FORMAT_PROMPT = """
<response_format>
Please respond in the following markdown format without any other text or symbols:

The_answer_to_the_question_in_simple_language.

**Relevant Rules**
- rule_number
- rule_number
etc

If there are no relevant rules used to answer the question then omit the **Relevant Rules** heading and section. 
Glossary entries are not considered rules so omit them.
</response_format>
"""

def get_rag_prompt(
        query: str, context: str, 
        conversation_history: list[dict], 
        response_format: BaseModel|dict|None = None):
    prompt = RAG_PROMPT.format(
        query=json.dumps(query, indent = 2), 
        context=json.dumps(context, indent = 2), 
        conversation_history=json.dumps(conversation_history, indent = 2)
    )
    
    if not response_format:
        prompt += FORMAT_PROMPT.format(response_format=response_format)
    
    return prompt


# NEXT_STEP_PROMPT = """You are an assistant for question-answering tasks about the sport of ultimate (ultimate frisbee). 
# All questions are in the context of ultimate frisbee. 

# Given the following conversation history and new question decide what the next set should be. The choices are:
# - RETRIEVE: retrieve information from the ultimate rule book or glossary.
# - ANSWER: answer the question directly based only on the conversation history. 

# Do not use your general knowledge about ultimate, use only the information provided in the conversation history.
# That means we should RETRIEVE if the information to answer the question is not in the conversation history.

# Conversation History:
# {history}

# New Question: 
# {user_input}

# Please answer with RETRIEVE or ANSWER and no other words"""

NEXT_STEP_PROMPT = """You are an assistant for question-answering tasks about the sport of ultimate (ultimate frisbee). 
All questions are in the context of ultimate frisbee. 

Given the following conversation history decide what the next set should be. The choices are:
- RETRIEVE: retrieve information from the ultimate rule book or glossary.
- ANSWER: answer the question directly based only on the conversation history. 

Do not use your general knowledge about ultimate, use only the information provided in the conversation history.
That means we should RETRIEVE if the information to answer the question is not in the conversation history.

Conversation History:
{history}

Please answer with RETRIEVE or ANSWER and no other words"""

def get_next_step_prompt(
        conversation_history: list[dict], 
        query: str):
    prompt = NEXT_STEP_PROMPT.format(
        history=json.dumps(conversation_history, indent = 2), 
        # user_input=query
    )
    return prompt



REWORD_QUERY_PROMPT = """You are an assistant for question-answering tasks about the sport of ultimate (ultimate frisbee). 
All questions are in the context of ultimate frisbee.

Given the following conversation history and the current user input, reword the user input to make it suitable for document retrieval.

Rewording rules:
- Examine the past few questions and possibly reword the user input to make it suitable for document retrieval. This is just to ensure that anything previously discussed is referred to by name and not as "it".
- If the question does not contain any references to previously discussed concepts, then do not reword it.
- If the last few questions discuss a concept and the latest question refers to the concept as "it", make it clear what "it" is.
- If the question asks to elaborate on a concept, then formulate a new question that is more specific to the concept.
- It is assumed we are talking about ultimate frisbee so DO NOT say "in ultimate frisbee" in the rewording
- If rewording is not needed then return "NONE"
- return just the reworded query, no other text

Conversation History:
{conversation_history}

User Input: 
{user_input}
"""

def get_reword_query_prompt(conversation_history: list[dict], query: str):
    return REWORD_QUERY_PROMPT.format(
        conversation_history=json.dumps(conversation_history[:-1], indent = 2), 
        user_input=query
    )

SELECT_RULES_DEFINITIONS_PROMPT = """You are an assistant for question-answering tasks about the sport of ultimate (ultimate frisbee). 
I have retrieved several rules and definitions from the ultimate rule book that may or may not be relevant to the question being asked.
Please select:
- the relevant rules (rule numbers only) that are needed to answer the current question. 
- the relevant definitions (definition names only) that are needed to answer the current question.

If a rule ends with a colon and is followed by sub-rules, include the sub-rules that follow. 
Example:
2.A.1. This rule applies in the following situations:
2.A.1.a <situation 1>
2.A.1.b <situation 2>


Conversation History:
{conversation_history}

Current Question:
{query}

Retrieved Context:
{context}
"""

def get_relevant_rules_definitions_prompt(query: str, conversation_history: list[dict], context: str):
    return SELECT_RULES_DEFINITIONS_PROMPT.format(
        conversation_history=json.dumps(conversation_history, indent = 2), 
        context=json.dumps(context, indent = 2), 
        query=json.dumps(query, indent = 2)
    )

VERIFY_ANSWER_PROMPT = """
Please verify that this answer is fully supported by its provided rules and the conversation history.
If it's not fully supported, provide a corrected answer that is supported. Please interpret the rules carefully.
The corrected answer should be a direct replacement for the original answer with no other text.

Conversation History: {conversation_history}

Question: {query}

Answer with rules: {answer}"""

def get_verify_answer_prompt(query: str, answer: str, conversation_history: list[dict]):
    return VERIFY_ANSWER_PROMPT.format(
        query=query, answer=answer, conversation_history=json.dumps(conversation_history, indent=2)
    )

