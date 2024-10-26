from dotenv import load_dotenv
load_dotenv()
import json
import os

rules_path = "texts/Official-Rules-of-Ultimate-2024-2025.md"

with open(rules_path, "r", encoding="utf-8") as file:
    rules_text = file.read()

#split into chunks by headers, ignoring the TOC, Preface, etc
summaries = []
chunks = rules_text.split("## ")[3:]

for chunk in chunks:
    section_name = chunk.split("\n")[0]
    item = {
        "section_name": section_name,
        "text": chunk
    }
    summaries.append(item)


summary_path = "texts/rule_section_summaries.json"
with open(summary_path, "w") as file:
    json.dump(summaries, file, indent=2)  


