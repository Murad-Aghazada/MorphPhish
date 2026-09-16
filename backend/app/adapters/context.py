from abc import ABC, abstractmethod
class ContextAdapter(ABC):
    @abstractmethod
    def generate(self, employee): ...
class MockContextAdapter(ContextAdapter):
    def generate(self, employee):
        base=[
          ("ticket",f"{employee.department} access review",f"Quarterly synthetic access review for {employee.role}.",{"source":"mock-ticketing"}),
          ("calendar","Security awareness briefing","Synthetic calendar event scheduled this week.",{"source":"mock-calendar"}),
          ("communication","Team project update","Synthetic metadata: internal team update thread is active.",{"source":"mock-comms","content_excluded":True}),
          ("task","Pending document review",f"Synthetic task relevant to {employee.department} workflow.",{"source":"mock-task"}),
        ]
        return base
