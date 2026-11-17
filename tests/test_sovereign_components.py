import importlib.util
import pathlib
import tempfile
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1] / "sovereign"
def load(name):
    spec = importlib.util.spec_from_file_location(name, ROOT / (name + ".py"))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

class SovereignComponents(unittest.TestCase):
    def test_graph_roundtrip(self):
        graph = load("knowledge").KnowledgeGraph()
        graph.add_node("repo", "repository")
        graph.add_node("test", "test")
        graph.link("repo", "contains", "test")
        with tempfile.TemporaryDirectory() as d:
            p = pathlib.Path(d) / "graph.json"
            graph.save(p)
            self.assertEqual(load("knowledge").KnowledgeGraph.load(p).neighborhood("test"), ["repo", "test"])
    def test_graph_invalid_edge(self):
        graph = load("knowledge").KnowledgeGraph()
        with self.assertRaises(ValueError):
            graph.link("missing", "contains", "other")
    def test_mesh_quota_and_fallback(self):
        mesh = load("mesh").FreeApiMesh([
            {"name": "remote", "enabled": True, "capabilities": ["code"], "daily_token_limit": 5, "priority": 10},
            {"name": "ollama", "enabled": True, "capabilities": ["code"], "daily_token_limit": 100, "priority": 1}
        ], clock=lambda: 1000)
        self.assertEqual(mesh.select("code", 5), "remote")
        self.assertTrue(mesh.reserve("remote", 5))
        self.assertEqual(mesh.select("code", 1), "ollama")
        self.assertFalse(mesh.reserve("remote", 1))
    def test_mesh_missing_quota_denied(self):
        mesh = load("mesh").FreeApiMesh([{"name": "unknown", "enabled": True, "capabilities": ["code"]}])
        self.assertIsNone(mesh.select("code"))

if __name__ == "__main__":
    unittest.main()
