import rdflib
import itertools

class SPAQLConverter:

    def __init__(self, config):
        self.g = rdflib.Graph()
        self.g.parse(config['owl']['path'])

        SKMO = rdflib.Namespace("http://www.sktelecom.com/skmo/")
        self.g.bind("skmo", SKMO)
        SCHEMA = rdflib.Namespace("https://schema.org/")
        self.g.bind("temp", SCHEMA)
        SCHEMA = rdflib.Namespace("http://schema.org/")
        self.g.bind("schema", SCHEMA)

    
    def select_query_graph(self, query_graph):
        final_query_graph = sorted(query_graph, key=lambda x: (-x[0], len(x[1])))[0][1]

        return final_query_graph
    

    def extract_relation_triples(self, final_query_graph):
        relation_triples = []

        for s,p,o in final_query_graph:
            if p == 'rdfs:subClassOf': continue
            if (s,p,o) in relation_triples: continue
            
            relation_triples.append((s,p,o))
        return relation_triples

    
    def generate_query(self, query_graph):
        final_query_graph = self.select_query_graph(query_graph) 
        relation_triples = self.extract_relation_triples(final_query_graph)

        knows_query = "SELECT DISTINCT ?target \nWHERE\n"
        prev_s = ''
        var_dict = {relation_triples[-1][-1]:'?target'}
        c = itertools.count()

        knows_query += '{'


        for s,p,o in relation_triples:
            # if p == 'rdfs:subClassOf':
            #     continue
            
            # domain이 instance 일때
            if s[-1] == ')':
                s_var = s[:-1].split('(')[-1]
            # domain이 class 일때
            else:
                if s in var_dict:
                    s_var = var_dict[s]
                else:
                    s_var = f'?x{next(c)}'
                    var_dict[s] = s_var

            # range가 instance 일때
            if o[-1] == ')':
                o_var = o[:-1].split('(')[-1]
            # range가 class 일때
            else:
                if o in var_dict:
                    o_var = var_dict[o]
                else:
                    o_var = f'?x{next(c)}'
                    var_dict[o] = o_var

            if prev_s == s_var:
                s_var = ';'
            else:
                if not prev_s == '':
                    knows_query += '.'
                prev_s = s_var
                knows_query += '\n    '
            
            knows_query += (' ').join([s_var, p, o_var])
            
        knows_query += '\n}'

        return knows_query
    

    def excute_query(self, knows_query):
        return self.g.query(knows_query)