from dotenv import load_dotenv
load_dotenv()

import os
import json
import argparse
from openai import OpenAI
from langchain_text_splitters import RecursiveCharacterTextSplitter

client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])
MODEL_NAME = "gpt-4o-mini"

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
If the chunk is a continuation of a rule definition, please summarize the rule as defined in the earlier section in a few words.
Answer only with the succinct context and nothing else.
"""

def create_embedding(text):
    response = client.embeddings.create(input=text, model="text-embedding-3-small")
    return response.data[0].embedding

def extract_sections(markdown_text):
    """Extract sections from the markdown text using regex."""
    named_sections = []
    sections = markdown_text.split("## ")[3:]
    
    for section in sections:
        section_name = section.split("\n")[0]
        item = {
            "section_name": section_name,
            "text": section
        }
        named_sections.append(item)
    
    return named_sections

def situate_context_openai(section: str, chunk: str) -> str:
    response = client.chat.completions.create(
        model=MODEL_NAME,
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

def process_rules_document(chunk_size):
    # Read the rules document
    with open("texts/Official-Rules-of-Ultimate-2024-2025.md", "r", encoding="utf-8") as f:
        rules_text = f.read()
    
    # Extract sections
    sections = extract_sections(rules_text)
    
    # Setup text splitter
    SEPARATORS = ["\n\n\n", "\n\n", "\n", "."]
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size, 
        chunk_overlap=0, 
        separators=SEPARATORS
    )
    
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
                "tokens": {
                    "prompt": usage.prompt_tokens, 
                    "completion": usage.completion_tokens
                },
                "embedding": embedding
            }
            items.append(item)
    
    return items

def main():
    parser = argparse.ArgumentParser(description='Create contextual embeddings for rules document')
    parser.add_argument('--chunk_size', type=int, default=1500, help='Size of text chunks (default: 1500)')
    args = parser.parse_args()
    
    items = process_rules_document(args.chunk_size)
    
    # Save the results
    output_path = f"texts/chunked_embedded/rules_contextual_embeddings_chunk-{args.chunk_size}.json"
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w") as f:
        json.dump(items, f, indent=2)

if __name__ == "__main__":
    main() 