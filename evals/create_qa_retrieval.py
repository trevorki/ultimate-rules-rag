import os
import json
import openai
from pydantic import BaseModel, Field
from dotenv import load_dotenv

load_dotenv()

openai_client = openai.OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

def create_qa_pairs(text, model="gpt-4o-mini", n_questions=10):

    class QA_Pair(BaseModel):
        question: str = Field(description="a question about the rules of ultimate")
        answer: str = Field(description="the answer to the question in plain language")
        rules: list[str] = Field(description="the rule (number and text) that the question and answer relate to or are referenced by quoted rule text")

    class QA_Dataset(BaseModel):
        qa_pairs: list[QA_Pair] = Field(description="a list of question-answer pairs")

    prompt = f"""
    Create {n_questions} questions and answer pair for the a QA dataset based on the rules of ultimate: {text}
    The questions will be used to test a RAG system based on this content so make sure they are somthing that could be asked about this subject. Each question should have a enough information to determine the answer based on the rules
    
    Here are the rules of ultimate:\n{text}
    """
    #           "reason_for_failure": "<[optional] if the qa pair was not generated explain why>"
    response = openai_client.beta.chat.completions.parse(
        model=model,
        messages=[
            {"role": "system", "content": "You are a helpful assistant that creates question-answer pairs."},
            {"role": "user", "content": prompt}
        ],
        temperature=0.5,
        max_tokens=2000,
        response_format=QA_Dataset
    )
    
    qa_dataset = response.choices[0].message.content
    print(f"\n\nqa_dataset ({type(qa_dataset)}):\n{qa_dataset}")

    #convert to dict
    qa_dataset_dict = json.loads(qa_dataset)
    print(f"\n\nqa_dataset_dict ({type(qa_dataset_dict)}):\n{qa_dataset_dict}")
    return qa_dataset_dict["qa_pairs"]

def create_embedding(text):
    response = openai_client.embeddings.create(input=text, model="text-embedding-3-small")
    return response.data[0].embedding

if __name__ == "__main__":

    path = r"C:\Users\Trevor_Kinsey\Documents\personal-projects\ultimate-rules-rag\texts\Official-Rules-of-Ultimate-2024-2025.md"
    model = "gpt-4o-2024-08-06"
    n_questions = 10

    with open(path, "r", encoding="utf-8") as file:
        text = file.read()
    sections = text.split("## ")

    qa_dataset = []

    # Create the QA pairs section by section
    for section in sections[3:]:
        section_name = section.split("\n")[0]
        print(f"\n{'***'*10} {section_name} {'***'*10}")
        print(f"\n{section[0:500]}...")
        qa_pairs = create_qa_pairs(section, model=model, n_questions=n_questions)
        # Update each QA pair with the section info
        qa_pairs = [dict(section=section_name, **qa_pair) for qa_pair in qa_pairs]
        print(f"\n\nqa_pairs:\n{json.dumps(qa_pairs, indent=4)}")
        qa_dataset.extend(qa_pairs)

        filename = f"evals/datasets/rules_dataset_{model}_{n_questions}q.json"
        with open(filename, "w", encoding="utf-8") as file:
            json.dump(qa_dataset, file, indent=4)
            
    #  Now create embeddings for the questions
    filename = f"evals/datasets/rules_dataset_{model}_{n_questions}q.json"
    with open(filename, "r", encoding="utf-8") as file:
        dataset = json.load(file)

    for i, item in enumerate(dataset):
        print(f"embedding item {i+1} of {len(dataset)}", end = "\r")
        item["question_embedding"] = create_embedding(item["question"])


    filename = f"evals/datasets/rules_dataset_{model}_{n_questions}q.json"
    with open(filename, "w", encoding="utf-8") as file:
        json.dump(dataset, file, indent=4)