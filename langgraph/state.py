from typing import TypedDict, Sequence, Optional, List

class State(TypedDict):
    question: str
    question_rewrite: Optional[bool]
    retrieval_activator: Optional[bool]
    context: Optional[List[str]]
   
    messages: Optional[List[str]]
    answer: Optional[str]

