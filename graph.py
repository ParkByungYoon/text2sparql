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
        

    def generate_all_conceptual_graph(self, resource_combinations):
        conceptual_graph = []
        for rc in resource_combinations:
            # rightmost element is an edge
            if self.get_type(rc[-1]) in ['T_dp', 'T_op']:
                rc = list(rc)
                rc.append('owl:Thing')

            conceptual_arc_list = []


            for i in range(len(rc)-1):
                conceptual_arc = []
                s_type = self.get_type(rc[i])

                if s_type in ['T_dp', 'T_op']:
                    continue
                
                p_list = []
                for j in range(i+1, len(rc)):
                    o_type = self.get_type(rc[j])
                    if o_type in ['T_dp', 'T_op']:
                        p_list.append(rc[j])
                    elif s_type == 'T_i' and o_type == 'T_i':
                        continue
                    else:
                        if len(p_list) == 0:
                            conceptual_arc.append((rc[i],'Any P',rc[j]))
                        else:
                            for p in p_list:
                                conceptual_arc.append((rc[i], p, rc[j]))
                conceptual_arc_list.append(conceptual_arc)
            
            for cg in list(itertools.product(*conceptual_arc_list)):
                conceptual_graph.append(list(cg))
        
        return conceptual_graph
    

    def generate_conceptual_graph(self, resource_combination):
        conceptual_graph = []
        for rc in resource_combination:
            # rightmost element is an edge
            if self.get_type(rc[-1]) in ['T_dp', 'T_op']:
                rc = list(rc)
                rc.append('owl:Thing')
                
            conceptual_arc = []
            for i in range(len(rc)-1):
                s_type = self.get_type(rc[i])

                if s_type in ['T_dp', 'T_op']:
                    continue
                
                p = 'Any P'
                for j in range(i+1, len(rc)):
                    o_type = self.get_type(rc[j])
                    if o_type in ['T_dp', 'T_op']:
                        p = rc[j]
                    elif s_type == 'T_i' and o_type == 'T_i':
                        break
                    else:
                        conceptual_arc.append((rc[i],p,rc[j]))
                        break
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


    def search_at_tbox_level(self, conceptual_graph, weight=True):
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

                    forward_result = find_shortest_path(self.G, u, v, e, weight=weight)
                    backward_result = find_shortest_path(self.G, v, u, e, weight=weight)

                    if forward_result[0] <= backward_result[0]:
                        score, result = forward_result
                        abox = ca[0], ca[-1]
                    else:
                        score, result = backward_result
                        abox = ca[-1], ca[0]

                    if len(result) == 0: continue

                    # 앞이 instance일 경우
                    if result[0][0] != abox[0]:
                        result[0] = (result[0][0] + '('+abox[0]+')', result[0][1], result[0][2])
                    
                    # 뒤가 instance일 경우
                    if result[-1][-1] != abox[1]:
                        result[-1] = (result[-1][0], result[-1][1], result[-1][2] + '('+abox[1]+')')
                    
                    ca2sp[ca].append((score,result))
        
        return ca2sp


    def generate_query_graph(self, conceptual_graph, weight=True):

        ca2sp = self.search_at_tbox_level(conceptual_graph, weight)
        query_graph = []

        for cg in conceptual_graph:
            query_graph_candidates = []
            for ca in cg:
                query_graph_candidates.append(ca2sp[ca])    
            for qg in itertools.product(*query_graph_candidates):
                sp_list = []
                query_graph_score = 0
                for arc_score, sp in qg:
                    query_graph_score += (1-arc_score)
                    sp_list.append(sp)
                sp_list = sum(sp_list, list())
                query_graph.append((query_graph_score, sp_list))

        return query_graph
    
    
    def merge_subclass(self, query_graph):
        new_query_graph = []
        for score, qg in query_graph:
            if qg[-1][-1][1] != 'rdfs:subClassOf' and qg[0][0][1] != 'rdfs:subClassOf':
                new_query_graph.append((score/len(qg),qg))
                continue
            
            new_score = score
            
            if qg[-1][-1][1] == 'rdfs:subClassOf':
                new_qg = []
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