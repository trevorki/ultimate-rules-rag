from ultimate_rules_rag.clients.get_abstract_client import get_abstract_client
from ultimate_rules_rag.rag_chat_session import RagChatSession
import os
import json
from pydantic import BaseModel
from dotenv import load_dotenv


load_dotenv()

grading_client = get_abstract_client(client_type="openai", default_model="gpt-4o-mini")

def process_question(session, question: dict, retriever_kwargs: dict):
    
    print("generating answer  ", end = "\r")
    question_text, generated_answer = answer_question(session, question, retriever_kwargs)
    processed_question = {
        "question": question_text,
        "expected_answer": question["answers"],
        "generated_answer": generated_answer
    }

    print("grading answer  ", end = "\r")
    graded_question = grade_question(processed_question)

    return processed_question | graded_question

def answer_question(session, question: dict, retriever_kwargs: dict):
    session.history.prune_history()

    question_text = f"""{question["question"]}
    {"\n" + "\n".join([f"{choice["letter"]}. {choice["text"]}" for choice in question["choices"]])}
    """.replace("    ", "").replace("\n\n", "\n")

    answer = session.answer_question(question_text, retriever_kwargs=retriever_kwargs)
    return question_text, answer


def grade_question(processed_question: dict):
    prompt = f"""You are a quiz-marking assistant. Please assign a grade to the following multiple choice question.
    The respondant may have included some extraneous information, so please ignore that.
    We want to know which choices (A, B, C, etc) they selected.
    Some questions have multiple correct answers, so we will record:
    - number of expected correct answers
    - number of generated correct answers
    - number of generated incorrect answers
    Here are some examples:
    <example 1>
    expected answer: C
    generated answer: C
    number of expected correct answers=1
    number of generated correct answers=1
    number of generated incorrect answers=0
    </example 1>

    <example 2>
    expected answer: A, B, C
    generated answer: A, B, C, D
    number of expected correct answers=3
    number of generated correct answers=3
    number of generated incorrect answers=1
    </example 2>

    <example 3>
    expected answer: A, B
    generated answer: A
    number of expected correct answers=2
    number of generated correct answers=1
    number of generated incorrect answers=0
    </example 3>

    Question:
    {processed_question["question"]}
    
    Expected Answer: 
    {processed_question["expected_answer"]}
    
    Generated Answer: 
    {processed_question["generated_answer"]}
    """.replace("    ", "")

    class GradedQuestion(BaseModel):
        number_of_expected_correct_answers: int
        number_of_generated_correct_answers: int
        number_of_generated_incorrect_answers: int

    graded_question = grading_client.invoke(prompt, config={"temperature": 0.1}, response_format=GradedQuestion)

    return graded_question.model_dump()

# Example usage
if __name__ == "__main__":

    llms = {
        # "gpt-4o-mini": "openai",
        "gpt-4o-20024-08-06": "openai",
        "claude-3-5-sonnet-20240620": "anthropic",
    }
    kwargs = {
            "limit": 6,
            "expand_context": 0,
            "search_type": "hybrid",
            "fts_operator": "OR"
        }
    chunk_size = 2000
    
    path = "evals/datasets/multiple_choice_qa.json"
    with open(path, "r") as f:
        questions = json.load(f)

    for model, provider in llms.items():
        print(f"\n\n{'#'*20} {model} {'#'*20}")
        client = get_abstract_client(client_type=provider, model=model)
        session = RagChatSession(llm_client=client, memory_size=0, context_size=1)

        out_folder = "evals/results/qa"
        out_filename = f"mc_chunk-{chunk_size}_model-{model}_lim-{kwargs['limit']}_exp-{kwargs['expand_context']}_search-{kwargs['search_type']}{kwargs['fts_operator']}.json"
        
        processed_questions = []
        for i, question in enumerate(questions):
            print(f"processing question {i+1} of {len(questions)}")
            processed_question = process_question(session, question, kwargs)
            processed_questions.append(processed_question)
            with open(f"{out_folder}/{out_filename}", "w") as f:
                json.dump(processed_questions, f, indent=2)
        


    #     session = RagChatSession(
    #         llm_client=client,
    #         stream_output=False,
    #         memory_size=6,
    #         context_size=1
    #     )
    
    # print("Enter a question (or 'q' to quit): ")
    # query = None
    # while query != "q":
    #     query = input("\n\nQUESTION: ")
    #     if query != "q":
    #         answer = session.answer_question(query, retriever_kwargs=retriever_kwargs)
    #         if not session.stream_output: 
    #             print("\nANSWER:") 
    #             print(answer)

    # print(f"\n\nhistory:")
    # session.history.pretty_print()

  
