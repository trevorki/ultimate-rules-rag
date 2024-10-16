import os
from graph import WorkFlow
from dotenv import load_dotenv
load_dotenv()

while True:
    app = WorkFlow().app
    # question = input("\nHUMAN: ").strip()
    question = "what is a strip?"
    if question.lower() in ['quit', 'q']:
        break
    else: 
        state = {"question": question}      
        print(f"\n\nState: {state}")     
        state = app.invoke(state)
        print(f"\n\nLLM: {state['answer']}")
        

