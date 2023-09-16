import numpy as np
import itertools

def query_patitioning(query_terms):
    query_patitions = [[" ".join(query_terms)]]

    for slice_num in range(1,len(query_terms)):
        for slice_list in itertools.combinations(range(len(query_terms)-1), slice_num):
            qp = []
            qp.append(" ".join(query_terms[:slice_list[0]+1]))
            
            for s_i, slice_idx in enumerate(slice_list):
                if s_i == len(slice_list) - 1 : break
                qp.append(" ".join(query_terms[slice_idx+1:slice_list[s_i+1]+1]))

            qp.append(" ".join(query_terms[slice_list[-1]+1:]))
            query_patitions.append(qp)
    
    return query_patitions


def partition_scoring(es, index_name, query_patitions):
    score_list = []

    for qp in query_patitions:
        score = 0
        for q in qp:
            search_query = {"query":{"term":{"Annotation Values.keyword": q}}}
            data = es.search(index=index_name, body=search_query)
            if data['hits']['max_score'] :
                score += data['hits']['max_score']
        score_list.append(score)
    
    p_star = query_patitions[np.argmax(score_list)]

    return p_star, score_list