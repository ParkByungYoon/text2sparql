from heapq import heappop, heappush
from itertools import count
import networkx as nx

def generate_graph(unit_path):
    G = nx.MultiDiGraph()

    for _, row in unit_path.iterrows():
        source = row['domain']  
        target = row['range']   
        edge = row['P']         
        weight = row['W']       

        G.add_node(source)        
        G.add_node(target)
            
        G.add_edge(source, target, property=edge, weight=weight, label=edge)
    
    return G

def find_shortest_path(G, source, target=None, p_name=None, n_triple=None):
    push = heappush
    pop = heappop
    
    c = count()
    fringe = []
    path = [source]
    result = []

    if n_triple is None:
        n_triple = len(G.nodes)

    if source == target:
        return result
    
    push(fringe, (0, next(c), source, path))

    while fringe:
        (d, loop, v, path) = pop(fringe)

        if len(path)//2 >= n_triple:
            continue
        
        if target == None:
            if p_name in path:
                result.append((d,path))
                continue
    
        elif target == path[-1]:
            if p_name is None or p_name in path:
                result.append((d,path))
            continue
        

        for u, edges in G._adj[v].items():
            if u in path:
                continue
            for _, e in edges.items():
                cost = e['weight']
                if cost is None:
                    continue
                vu_dist = d + cost

                new_path = list()
                new_path += path
                new_path += [e['property'], u]

                push(fringe, (vu_dist, next(c), u, new_path))
    
    if len(result) == 0:
        # raise nx.NetworkXNoPath(f"Node {target} not reachable from {source} with {p_name}")
        return result
    
    return sorted(result)[0][1]