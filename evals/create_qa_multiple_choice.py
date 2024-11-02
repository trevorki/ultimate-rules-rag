from src.ultimate_rules_rag.clients.get_abstract_client import get_abstract_client
import os
import json
from pydantic import BaseModel, Field

client = get_abstract_client(client_type="openai", default_model="gpt-4o-2024-08-06")

def llm_parse_question(question: str) -> dict:
    prompt = f"""You are a quiz making expert. 
    Please read the following question and format it in the specified structured format.
    The question may have more than 1 correct answer.
    Do not change the question or the choices in any way.
    Here is the question:
    {question}
    """
    class Choice(BaseModel):
        letter: str = Field(description="The letter of the multiple choice item. Use A, B, C, D, etc.")
        text: str = Field(description="The text of the multiple choice item")

    class Question(BaseModel):
        question: str = Field(description="The question to be answered (ignore the question number)")
        choices: list[Choice] = Field(description="The list of possible answers for the question")
        answers: list[str] = Field(description="The letter of the correct answer(s) to the question. Use A, B, C, D, etc.")
    config = {"temperature": 0.1}
    response =  client.invoke(prompt, config=config, response_format=Question)
    print(response.answers)
    return response.model_dump()

folder = "evals/quizzes"
quiz_files = os.listdir(folder)

parsed_questions = []

for quiz_file in quiz_files:
    print(f"\n{'#'*10} Processing {quiz_file} {'#'*10}")
    with open(f"{folder}/{quiz_file}", "r", encoding="utf-8") as file:
        content = file.read()

    questions = content.split("\n\n")
    for i, question in enumerate(questions, start = 1):
        print(f"Question {i} of {len(questions)}", end=None)
        parsed_question = llm_parse_question(question)
        parsed_question["source"] = quiz_file
        parsed_question["question_number"] = i
        parsed_questions.append(parsed_question)
        # print(json.dumps(parsed_question, indent=4))  

        with open("evals/datasets/multiple_choice_qa.json", "w") as file:
            json.dump(parsed_questions, file, indent=4)
