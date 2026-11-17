"""Versioned, typed dependency graph; offline JSON persistence."""
import json
from pathlib import Path

KINDS = {"repository", "file", "test", "requirement", "dependency", "repair"}
RELATIONS = {"contains", "tests", "requires", "depends_on", "repaired_by"}

class KnowledgeGraph:
    def __init__(self):
        self.nodes = {}
        self.edges = []
    def add_node(self, node_id, kind, **metadata):
        if kind not in KINDS or not node_id:
            raise ValueError("Invalid node")
        self.nodes[node_id] = {"kind": kind, "metadata": metadata}
    def link(self, source, relation, target):
        if source not in self.nodes or target not in self.nodes or relation not in RELATIONS:
            raise ValueError("Invalid edge")
        edge = {"source": source, "relation": relation, "target": target}
        if edge not in self.edges:
            self.edges.append(edge)
    def neighborhood(self, node_id, depth=2):
        if node_id not in self.nodes or not isinstance(depth, int) or depth < 0 or depth > 5:
            raise ValueError("Invalid query")
        visited = {node_id}
        for _ in range(depth):
            visited |= {e["target"] for e in self.edges if e["source"] in visited}
            visited |= {e["source"] for e in self.edges if e["target"] in visited}
        return sorted(visited)
    def save(self, path):
        Path(path).write_text(json.dumps({"schema_version": 1, "nodes": self.nodes, "edges": self.edges}, indent=2))
    @classmethod
    def load(cls, path):
        data = json.loads(Path(path).read_text())
        if data.get("schema_version") != 1:
            raise ValueError("Unsupported schema")
        graph = cls()
        for key, node in data["nodes"].items():
            graph.add_node(key, node["kind"], **node.get("metadata", {}))
        for edge in data["edges"]:
            graph.link(edge["source"], edge["relation"], edge["target"])
        return graph
