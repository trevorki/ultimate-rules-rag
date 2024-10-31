from pydantic import BaseModel
from typing import ClassVar, Dict

class Usage(BaseModel):
    model: str
    input_tokens: int = 0
    output_tokens: int = 0
    n_calls: int = 0
    
    TOKEN_COSTS: ClassVar[Dict[str, Dict[str, float]]] = {
        "gpt-4o-2024-08-06": {"prompt": 2.5/1e6, "completion": 10/1e6},
        "gpt-4o-mini": {"prompt": 0.15/1e6, "completion": 0.60/1e6}
    }

    def add_usage(self, usage_info):
        self.input_tokens += usage_info.prompt_tokens
        self.output_tokens += usage_info.completion_tokens
        self.n_calls += 1

    def get_usage(self) -> dict:
        return {
            "input_tokens": self.input_tokens,
            "output_tokens": self.output_tokens,
            "n_calls": self.n_calls
        }

    def get_cost(self) -> dict:
        prompt_cost = self.input_tokens * self.TOKEN_COSTS[self.model]["prompt"]
        completion_cost = self.output_tokens * self.TOKEN_COSTS[self.model]["completion"]
        return {
            "input_cost": prompt_cost,
            "output_cost": completion_cost,
            "total_cost": prompt_cost + completion_cost
        }
    
    def pretty_print(self):
        costs = self.get_cost()
        print("USAGE:")
        print(f"\tmodel:    {self.model}")
        print(f"\tn_calls:  {self.n_calls}")
        print(f"\tinput_tokens:   {self.input_tokens}")
        print(f"\toutput_tokens:  {self.output_tokens}")
        print(f"\tinput_cost:   ${costs['input_cost']:.4f}")
        print(f"\toutput_cost:  ${costs['output_cost']:.4f}")
        print(f"\ttotal_cost:   ${costs['total_cost']:.4f}")