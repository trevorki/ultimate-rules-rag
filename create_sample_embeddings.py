from openai import OpenAI
import json
from dotenv import load_dotenv
load_dotenv()

client = OpenAI()


def create_embedding(text):
    response = client.embeddings.create(input=text, model="text-embedding-3-small")
    return response.data[0].embedding

sentences = [
    #    Group 1: Weather Observations
    "The golden leaves rustled in the crisp autumn breeze.",
    "Snowflakes danced gracefully as they fell from the steel-gray sky.",
    "Droplets of summer rain pattered gently against the windowpane.",

    # Group 2: Technology Advancements
    "The new quantum computer solved complex equations in mere seconds.",
    "Scientists unveiled a revolutionary clean energy source derived from algae.",
    "The latest AI model demonstrated unprecedented natural language understanding.",

    # Group 3: Personal Achievements
    "After months of training, Sarah completed her first marathon with a beaming smile.",
    "John's persistent efforts paid off as he received a well-deserved promotion at work.",
    "Emma's dedication to her craft resulted in her artwork being featured in a prestigious gallery.",
]

sentence_embeddings = {}
for sentence in sentences:
    print(f"Creating embedding for: '{sentence}'")
    embedding = create_embedding(sentence)
    sentence_embeddings[sentence] = embedding

path = "sample_sentence_embeddings.json"
with open(path, "w") as f:
    json.dump(sentence_embeddings, f, indent=2)
    




