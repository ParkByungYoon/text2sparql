from heapq import heappop, heappush
import itertools
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


def find_shortest_path(G, source, target, p_name=None, n_triple=None, weight=False):
    push = heappush
    pop = heappop
    
    c = itertools.count()
    fringe = []
    path = [source]
    result = (float('inf'), [])

    if n_triple is None:
        n_triple = len(G.nodes)

    if source == target:
        raise ValueError(f"source({source}) and target({target}) are the same")
    
    push(fringe, (0, next(c), source, path))

    while fringe:
        (d, loop, v, path) = pop(fringe)

        if len(path)//2 >= n_triple:
            continue
    
        if target == path[-1]:
            if p_name is None or p_name in path:
                result = (d,path)
                break
            continue
        

        for u, edges in G._adj[v].items():
            if u in path:
                continue
            for _, e in edges.items():
                if weight: cost = e['weight'] 
                else: cost = 1
                vu_dist = d + cost

                new_path = list()
                new_path += path
                new_path += [e['property'], u]

                push(fringe, (vu_dist, next(c), u, new_path))

    if len(result[1]) == 0:
        return result

    score, shortest_path = result
    shortest_path = [tuple(shortest_path[offset:offset+3]) for offset in range(0, len(shortest_path)-2, 2)]
    return score, shortest_path