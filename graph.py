from heapq import heappop, heappush
import itertools
import networkx as nx


def base_graph_generation(unit_path):
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


def conceptual_graph_generation(onto, resource_combinations):
    conceptual_graph = []

    for rc in resource_combinations:
        conceptual_arc = []
        state_list = []
        rc = list(rc)

        for r in rc:
            if (r) in onto.object_properties():
                state_list.append('edge') 
            elif r in onto.data_properties():
                state_list.append('edge') 
            else:
                state_list.append('vertex') 

        # 처음이 edge일 때
        if state_list[0] == 'edge':
            break
        
        # 마지막이 edge일 때
        if state_list[-1] == 'edge':
            state_list.append('vertex')
            rc.append(None)

        # vertex - vertex 일때
        index_list = []
        for i in range(len(state_list)-1):
            if state_list[i] == 'vertex' and state_list[i+1] == 'vertex':
                index_list.append(i+1)
        
        for i in index_list:
            state_list.insert(i, 'edge')
            rc.insert(i, None)
        
        for offset in range(0,len(rc)-2, 2):
            conceptual_arc.append(tuple(rc[offset:offset+3]))

        conceptual_graph.append(conceptual_arc)
    
    return conceptual_graph


def query_graph_generation(G, conceptual_graph):

    query_graph = {}

    for cg in conceptual_graph:
        
        for ca in cg:
            if ca in query_graph: 
                continue
            else:
                query_graph[ca] = []

            d,p,r = ca

            if d and not G.has_node(str(d)):
                d = d.is_a
            else: d = [d]

            if r and not G.has_node(str(r)):
                r = r.is_a
            else: r = [r]

            p = [p]

            for u,e,v in itertools.product(d,p,r):
                if u: u = str(u)
                if e: e = str(e)
                if v: v = str(v)

                result = find_shortest_path(G, u, v, e, n_triple=3)
                if len(result) == 0: continue
                query_graph[ca].append(result)
    
    return query_graph


def find_shortest_path(G, source, target=None, p_name=None, n_triple=None):
    push = heappush
    pop = heappop
    
    c = itertools.count()
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
        return result
    
    result = sorted(result)[0][1]
    
    return [tuple(result[offset:offset+3]) for offset in range(0, len(result)-2, 2)]