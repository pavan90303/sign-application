"""
Knowledge Graph Generator
==========================
Constructs NetworkX directed graphs from extracted concepts and relationships
for topological and structural knowledge alignment.
"""

def build_networkx_knowledge_graph(concepts_list: list, relationships_list: list):
    """
    Constructs a NetworkX DiGraph for structural knowledge analysis.
    """
    import networkx as nx
    G = nx.DiGraph()
    for c in concepts_list:
        c_name = c.get("name", c) if isinstance(c, dict) else str(c)
        c_id = c.get("id", c_name).lower().strip() if isinstance(c, dict) else c_name.lower().strip()
        G.add_node(c_id, label=c_name)
    for r in relationships_list:
        s = str(r.get("source", "")).lower().strip()
        t = str(r.get("target", "")).lower().strip()
        rel = str(r.get("relation", "relates"))
        if s and t:
            G.add_edge(s, t, relation=rel)
    return G
