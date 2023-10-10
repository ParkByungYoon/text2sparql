from elasticsearch import Elasticsearch
import pandas as pd
import numpy as np
from path import *

class ConceptualGraphGenerator:
    
    def __init__(self, config):
        # Elasticsearch
        server_ip = config['elasticsearch']['ip']
        self.index_name = config['elasticsearch']['name']
        self.es = Elasticsearch(server_ip)
    

    def get_type(self, resource):
        search_query = {"query":{"term":{"URI.keyword": resource}}}
        result = self.es.search(index=self.index_name, body=search_query)
        return result['hits']['hits'][0]['_source']['Type']
        

    def generate_conceptual_graph(self, resource_combinations):
        conceptual_graph = []

        for rc in resource_combinations:
            conceptual_arc = []
            state_list = []
            rc = list(rc)

            for r in rc:
                r_type = self.get_type(r)
                if r_type in ['T_dp', 'T_op']:
                    state_list.append('edge') 
                else:
                    state_list.append('vertex') 

            # 마지막이 edge일 때
            if state_list[-1] == 'edge':
                state_list.append('vertex')
                rc.append('owl:Thing')

            # vertex - vertex 일때
            index_list = []
            for i in range(len(state_list)-1):
                if state_list[i] == 'vertex' and state_list[i+1] == 'vertex':
                    index_list.append(i+1)
            
            for i in index_list:
                state_list.insert(i, 'edge')
                rc.insert(i, 'Any P')
            
            for offset in range(0,len(rc)-2, 2):
                conceptual_arc.append(tuple(rc[offset:offset+3]))
            
            conceptual_graph.append(conceptual_arc)
        
        return conceptual_graph



class QueryGraphGenerator:

    def __init__(self, config):
        # Elasticsearch
        server_ip = config['elasticsearch']['ip']
        self.index_name = config['elasticsearch']['name']
        self.es = Elasticsearch(server_ip)

        # Unit Path
        unit_path = pd.read_csv(config['unitpath']['path'])
        self.G = generate_graph(unit_path)


    def get_tbox(self, resource):
        search_query = {"query":{"term":{"URI.keyword": resource}}}
        result = self.es.search(index=self.index_name, body=search_query)
        return result['hits']['hits'][0]['_source']['Tbox']


    def search_at_tbox_level(self, conceptual_graph):
        ca2sp = {}

        for cg in conceptual_graph:
        
            for ca in cg:
                if ca in ca2sp: 
                    continue

                ca2sp[ca] = []
                d,p,r = ca

                # Restict search space to Tbox level
                if not self.G.has_node(d):
                    d = self.get_tbox(d)
                else: d = [d]

                if not self.G.has_node(r):
                    r = self.get_tbox(r)
                else: r = [r]

                p = [p]

                # Find shortest path
                for u,e,v in itertools.product(d,p,r):
                    if e == 'Any P': e=None

                    score, result = find_shortest_path(self.G, u, v, e, n_triple=4, weight=True) 
                    if len(result) == 0: continue
                    ca2sp[ca].append((score,result))
        
        return ca2sp


    def generate_query_graph(self, conceptual_graph):

        ca2sp = self.search_at_tbox_level(conceptual_graph)
        query_graph = []

        for cg in conceptual_graph:
            query_graph_candidates = []
            for ca in cg:
                query_graph_candidates.append(ca2sp[ca])    
            for qg in itertools.product(*query_graph_candidates):
                sp_list = []
                query_graph_score = 0
                for arc_score, sp in qg:
                    query_graph_score += arc_score
                    sp_list.append(sp)
                query_graph.append((query_graph_score, sp_list))

        query_graph = self.merge_subclass(query_graph)

        return query_graph
    
    
    def merge_subclass(self, query_graph):
        new_query_graph = []
        for score, qg in query_graph:
            if qg[-1][-1][1] != 'rdfs:subClassOf' and qg[0][0][1] != 'rdfs:subClassOf':
                new_query_graph.append((score/len(qg),qg))
                continue
            
            if qg[-1][-1][1] == 'rdfs:subClassOf':
                new_qg = []
                new_score = score
                terminated = False

                for sp in qg[::-1]:
                    n_delete = 0
                    if terminated:
                        new_qg.insert(0,sp)
                        continue
                    for arc in sp[::-1]:
                        if arc[1] == 'rdfs:subClassOf':
                            n_delete+=1
                            new_score-=0
                        else: 
                            terminated = True
                            break
                    if len(sp)-n_delete == 0: continue
                    new_qg.insert(0, sp[:len(sp)-n_delete])
                qg = new_qg

            if qg[0][0][1] == 'rdfs:subClassOf':
                new_qg = []
                terminated = False

                for sp in qg:
                    n_delete = 0
                    if terminated:
                        new_qg.append(sp)
                        continue
                    for arc in sp:
                        if arc[1] == 'rdfs:subClassOf':
                            n_delete+=1
                            new_score-=0
                        else: 
                            terminated = True
                            break
                    if len(sp)-n_delete == 0: continue
                    new_qg.append(sp[n_delete:])
                
            if len(new_qg) == 0: continue
            if (new_score/len(new_qg), new_qg) in new_query_graph : continue
            new_query_graph.append((new_score/len(new_qg), new_qg))
    
        return new_query_graph