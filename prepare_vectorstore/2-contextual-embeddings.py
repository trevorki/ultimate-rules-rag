from dotenv import load_dotenv
load_dotenv()

import os
import anthropic
from openai import OpenAI
import json
from langchain_text_splitters import RecursiveCharacterTextSplitter


client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])

def create_embedding(text):
    response = client.embeddings.create(input=text, model="text-embedding-3-small")
    return response.data[0].embedding

DOCUMENT_CONTEXT_PROMPT = """
You are a helpful assistant that is helping to situate a chunk of text within a larger document. 
The larger document is a section from the official rules of the sport of ultimate frisbee.
The rule book has the following sections:
1. Introduction
2. Spirit of the Game
3. Definitions
4. Playing Field
5. Equipment
6. Length of Game
7. Timeouts
8. Player Substitutions
9. Starting and Restarting Play
10. In- and Out-of-bounds
11. End Zone Possession
12. Scoring
13. Turnovers
14. The Thrower
15. The Marker
16. The Receiver
17. Violations and Fouls
18. Positioning
19. Observers
20. Etiquette
Appendix A: Field Diagram
Appendix B: Misconduct System
Appendix C: Hand Signals
Appendix D: Youth Rules Adaptations
Appendix E: Beach Ultimate Rules Adaptations
Appendix F: Ultimate 4's Rules Adaptations

Here is the section of the document we are focusing on:
<section>
{section}
</section>
"""

CHUNK_CONTEXT_PROMPT = """
Here is the chunk we want to situate within the section:
<chunk>
{chunk}
</chunk>

Please give a short succinct context to situate this chunk within the overall document for the purposes of improving search retrieval of the chunk.
Answer only with the succinct context and nothing else.
"""


def situate_context_openai(section: str, chunk: str) -> str:
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        max_tokens=250,
        temperature=0.1,
        messages=[
            {
                "role": "user", 
                "content": [
                    {
                        "type": "text",
                        "text": DOCUMENT_CONTEXT_PROMPT.format(section=section)
                    },
                    {
                        "type": "text",
                        "text": CHUNK_CONTEXT_PROMPT.format(chunk=chunk)
                    }
                ]
            }
        ],
    )
    return response

# load the sections
path = "texts/rule_section_summaries.json"
with open(path, "r") as f:
    sections = json.load(f)

CHUNK_SIZE = 1500
SEPARATORS = ["\n\n\n", "\n\n", "\n", "."]
splitter = RecursiveCharacterTextSplitter(chunk_size=CHUNK_SIZE, chunk_overlap=0, separators=SEPARATORS)
items = []
for section in sections:
    
    text = section["text"]
    chunks = splitter.split_text(text)
    print(f"\nsection: {section['section_name']} ({len(chunks)} chunks)")
    for i, chunk in enumerate(chunks):
        print(f"chunk {i+1} of {len(chunks)}     ", end="\r")
        context_response = situate_context_openai(section["section_name"], chunk)
        context = context_response.choices[0].message.content
        usage = context_response.usage
        embedding = create_embedding(f"{chunk}\n\n{context}")
        item = {
            "context": context,
            "chunk": chunk,
            "tokens": {"prompt": usage.prompt_tokens, "completion": usage.completion_tokens},
            "embedding": embedding
        }
        items.append(item)


        
with open("texts/contextual_embeddings.json", "w") as f:
    json.dump(items, f, indent = 2)







