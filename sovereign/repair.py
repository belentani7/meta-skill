"""MAPE-K proposal-only loop: monitor, analyze, plan, evaluate; never auto-apply."""
from dataclasses import dataclass

@dataclass
class RepairProposal:
    failed_node: str
    context_nodes: list
    action: dict
    allowed: bool
    reasons: list

def plan_repair(graph, guard, failure_node, action, inventory):
    context = graph.neighborhood(failure_node)
    decision = guard(action, inventory)
    return RepairProposal(failure_node, context, action, decision["allowed"],
                          decision["failures"])
