import pandas as pd
from owlready2 import get_ontology
from elasticsearch import Elasticsearch
from setting import config_read

# Read config file
config = config_read()

# Load owl file
data_path = config['owl']['path']
onto = get_ontology(data_path).load()

# Connect to Elasticsearch Server
es = Elasticsearch(config['elasticsearch']['ip'])
index_name = config['elasticsearch']['name']

# Create index on dataframe
index_list = []
index_list.extend([("T_c", r.label) for r in onto.classes()])
index_list.extend([("T_op", r.label) for r in onto.object_properties()])
index_list.extend([("T_dp", r.label) for r in onto.data_properties()])
index_list.extend([("T_i", r.label) for r in onto.individuals()])

df = pd.DataFrame(index_list, columns=['Type', 'Annotation Values'])

# Remain only resources with annotation values
cond = df["Annotation Values"].apply(len) != 0
df = df[cond].reset_index(drop=True)

# Delete index on elasticsearch server
if es.indices.exists(index=index_name):
    es.indices.delete(index=index_name,ignore=[400, 404])
    print('Index has been deleted successfully')

# Create index on elasticsearch server
for i in range(len(df)) :
    doc = {'Annotation Values':df["Annotation Values"][i],}
    es.index(index=index_name, body=doc)