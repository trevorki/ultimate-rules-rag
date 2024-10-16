from nodes import Nodes
from langgraph.graph import StateGraph, END
from state import State

class WorkFlow():
	def __init__(self, **node_kwargs):
		nodes = Nodes(**node_kwargs)
		print("NODES",nodes)
		workflow = StateGraph(State)
		workflow.add_node("question_rewriter", nodes.question_rewriter)
		workflow.add_node("retriever", nodes.retriever)
		workflow.add_node("context_filterer", nodes.context_filterer)
		workflow.add_node("answer_question", nodes.answer_question)
		
		workflow.set_entry_point("question_rewriter")
		workflow.add_edge('question_rewriter', 'retriever')
		workflow.add_edge('retriever', 'context_filterer')
		workflow.add_edge('context_filterer', 'answer_question')
		workflow.add_edge('answer_question', END)
		

		# workflow.add_conditional_edges(
		# 	"validate_llm_scan", # start node
		# 	nodes.scan_valid, # decision function
		# 	{True: "categorize_summarize_receipt",  False: "save_output"} # dest nodes
		# )
		
		self.app = workflow.compile()