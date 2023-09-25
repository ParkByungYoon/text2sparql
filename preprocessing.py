import pandas as pd
import owlready2
import rdflib
from elasticsearch import Elasticsearch
from setting import config_read
from utils import literal

# Read config file
config = config_read()

# Load owl file
data_path = config['owl']['path']
onto = owlready2.get_ontology(data_path).load()

# Connect to Elasticsearch Server
es = Elasticsearch(config['elasticsearch']['ip'])
index_name = config['elasticsearch']['name']

##########################################################################################
###################################  Index Generation  ###################################
##########################################################################################


need_index = True

if need_index:
    # Create index on dataframe
    index_list = []
    index_list.extend([("T_c", r.label) for r in onto.classes()])
    index_list.extend([("T_op", r.label) for r in onto.object_properties()])
    index_list.extend([("T_dp", r.label) for r in onto.data_properties()])
    index_list.extend([("T_i", r.label) for r in onto.individuals()])

    index_df = pd.DataFrame(index_list, columns=['Type', 'Annotation Values'])

    # Remain only resources with annotation values
    cond = index_df["Annotation Values"].apply(len) != 0
    index_df = index_df[cond].reset_index(drop=True)

    # Delete index on elasticsearch server
    if es.indices.exists(index=index_name):
        es.indices.delete(index=index_name,ignore=[400, 404])
        print('Index has been deleted successfully')

    # Create index on elasticsearch server
    for i in range(len(index_df)) :
        doc = {'Annotation Values':index_df["Annotation Values"][i],}
        es.index(index=index_name, body=doc)


##########################################################################################
#################################  Unit Path Extraction  #################################
##########################################################################################


need_unit_path = True

if need_unit_path:
    g = rdflib.Graph()
    g.parse(data_path)

    knows_query = """
    SELECT DISTINCT ?x ?y ?z
    WHERE {
        ?x ?y ?z.
    }"""

    triple_list = []
    qres = g.query(knows_query)
    for row in qres:
        triple_list.append([str(row[0]), str(row[1]), str(row[2])])


    triple_text_list = []
    for s,p,o in triple_list:
        s_res = onto.search_one(iri=s)
        if s_res == None : 
            s_triple = s
        else:
            s_triple = s_res

        p_res = onto.search_one(iri=p)
        if p_res == None :
            p_triple = p
        else:
            p_triple = p_res

        o_res = onto.search_one(iri=o)
        if o_res == None : 
            o_triple = o
        else:
            o_triple = o_res
        
        triple_text_list.append([s_triple, p_triple, o_triple])

    triple_df = pd.DataFrame(triple_text_list, columns=['S','P','O'])
    triple_df = triple_df.drop_duplicates(['S','P','O']).reset_index(drop=True)


    p_list = list(onto.object_properties())
    p_list.extend(list(onto.data_properties()))
    only_op_dp_df = triple_df[triple_df.P.isin(p_list)].reset_index(drop=True)


    only_op_dp_df['domain'] = only_op_dp_df['S'].apply(lambda x:x.is_a)
    only_op_dp_df['range'] = only_op_dp_df['O'].apply(literal)

    only_op_dp_df = only_op_dp_df.explode(['domain'])
    only_op_dp_df = only_op_dp_df.explode(['range'])

    class_map_df = only_op_dp_df[only_op_dp_df['domain'] != owlready2.Thing].reset_index(drop=True).astype(str)

    cond = class_map_df['range'] == 'Literal_'
    class_map_df.loc[cond, 'range'] += class_map_df.loc[cond, 'P']


    # the number of instance-level triples containing the property of the unit path
    dpr_df = class_map_df.groupby(['domain', 'P', 'range'], as_index=False).S.count()

    # the total number of triples from domain class to range class
    dr_df = class_map_df.groupby(['domain', 'range'], as_index=False).S.count()

    merged_df = pd.merge(class_map_df, dpr_df, on=['domain', 'P', 'range'], how='inner', suffixes=('','_dpr'))
    merged_df = pd.merge(merged_df, dr_df, on=['domain', 'range'], how='inner', suffixes=('','_dr'))
    merged_df['W'] = 1 - (merged_df['S_dpr'] / merged_df['S_dr'])

    final_triple_df = merged_df[['domain', 'P', 'range', 'W']]
    merged_df = merged_df[['S', 'P', 'O', 'domain', 'range']]
    final_triple_df = final_triple_df.drop_duplicates().reset_index(drop=True)

    merged_df.to_csv('../unit_path_for_mapping.csv', index=False)
    final_triple_df.to_csv('../unit_path.csv', index=False)