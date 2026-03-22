#Library imports
import pandas as pd
import random
import csv
import math
import importlib
from pathlib import Path
from rdflib import Literal, Graph, RDF
from namespace import *
import datetime

"""
    Helper functions to be used in the main.py file
    - hierarchy_reader: reads a hierarchy file to be used for attribute generalization
    - generate_full_name: generates a list of random full names
    - read_txt_file: reads a text file and returns a list of comma-separated elements
    - generate_rdf: generates an RDF graph with FOAF vocabulary specification which fits the expected input of the implemented graph anonymization algorithm
"""

# reads a hierarchy file file dataset and renames columns
# the expected format of the hierarchy file is the same as when exporting a hierarchy file from ARX anonymization tool
# example: data\hierarchies\age.csv
def hierarchy_reader(filename: str):
    df = pd.read_csv(filename, sep=";", header=None) #note the separator when exporting file from ARX
    column_names = ["level_%s" %i for i in range(len(df.columns))] #provide customized column names
    df.columns = column_names
    df = df.astype(str)
    return df 

#gets a list of first names, a list of last names and a number of people and generates a list of random full names
def generate_full_name(first_names,last_names, n):
    names = []
    for i in range(n):
        names.append("".join(random.choice(first_names)+"_"+random.choice(last_names)))
    return names

#reads a text file and returns a list of comma-separated elements
def read_txt_file(filename):
    with open(filename, newline='') as f:
        reader = csv.reader(f)
        data = list(reader)
        #flatten list of lists
        data = [item for sublist in data for item in sublist]
    return data

def _validate_rmat_params(a: float, b: float, c: float, d: float):
    total = a + b + c + d
    if min(a, b, c, d) < 0:
        raise ValueError("R-MAT parameters must be non-negative.")
    if not math.isclose(total, 1.0, rel_tol=1e-9, abs_tol=1e-9):
        raise ValueError(f"R-MAT parameters must sum to 1.0 (current sum={total}).")

def _extract_undirected_edges(graph_obj):
    edges = set()
    if hasattr(graph_obj, "iterEdges"):
        iterator = graph_obj.iterEdges()
    elif hasattr(graph_obj, "edges"):
        iterator = graph_obj.edges()
    else:
        raise RuntimeError("Unable to iterate edges from NetworKit graph object.")

    for u, v in iterator:
        if u == v:
            continue
        edge = (u, v) if u < v else (v, u)
        edges.add(edge)
    return edges

def generate_rmat_knows_edges(
    n_people: int,
    m_knows: int,
    a: float,
    b: float,
    c: float,
    d: float,
    seed: int):
    _validate_rmat_params(a, b, c, d)

    if m_knows <= 0:
        return set()

    max_edges = (n_people * (n_people - 1)) // 2
    target_edges = min(m_knows, max_edges)

    try:
        nk = importlib.import_module("networkit")
    except ModuleNotFoundError as exc:
        raise ImportError(
            "NetworKit is required when --use_rmat is enabled. Please get that package."
        ) from exc

    if hasattr(nk, "setSeed"):
        nk.setSeed(seed, False)

    scale = math.ceil(math.log2(n_people)) if n_people > 1 else 1
    total_nodes = 2 ** scale
    reduce_nodes = total_nodes - n_people

    edge_factor = max(1, math.ceil(target_edges / n_people))
    rmat_generator = nk.generators.RmatGenerator(scale, edge_factor, a, b, c, d, False, reduce_nodes)
    rmat_graph = rmat_generator.generate()
    knows_edges = _extract_undirected_edges(rmat_graph)

    if len(knows_edges) < target_edges:
        possible_edges = [(u, v) for u in range(n_people) for v in range(u + 1, n_people)]
        missing = [edge for edge in possible_edges if edge not in knows_edges]
        random.shuffle(missing)
        knows_edges.update(missing[:target_edges - len(knows_edges)])

    if len(knows_edges) > target_edges:
        knows_edges = set(random.sample(list(knows_edges), target_edges))

    return knows_edges

#generates an RDF graph with FOAF vocabulary specification which fits the expected input of the implemented graph anonymization algorithm
def generate_rdf(
    attributes_dict: dict,
    unidirectional_connections_dict: dict,
    bidirectional_connections_dict: dict,
    preamble: str,
    n_people: int,
    graph_name: str,
    first_names: list,
    last_names: list,
    use_rmat: bool = False,
    m_knows: int = None,
    rmat_a: float = 0.57,
    rmat_b: float = 0.19,
    rmat_c: float = 0.19,
    rmat_d: float = 0.05,
    seed: int = 11,
    n_projects: int = None,
    min_projects: int = None,
    max_projects: int = None,
    output_dir: str = None):
    
    #PREPROCESSING
    #random seed initialization for reproducibility in subsequent runs
    random.seed(seed)
    #empty graph element where whole RDF graph will be stored
    g = Graph()
    #generate random names for the people (nodes)
    full_names = generate_full_name(n=n_people,
                                    first_names=first_names,
                                    last_names=last_names)

    #each person should have a URI associated with a subject, object and predicate
    #full names are used for this purpose
    #URIs are stored in a list
    URIs = [URIRef("%s/%s_%s" %(preamble, full_names[i], i)) for i in range(n_people)]

    project_uris = []
    should_generate_projects = (
        n_projects is not None or
        min_projects is not None or
        max_projects is not None or
        "currentProject" in unidirectional_connections_dict
    )

    if should_generate_projects:
        if n_projects is not None and n_projects > 0:
            project_ids = [str(i) for i in range(n_projects)]
        elif "currentProject" in unidirectional_connections_dict:
            project_ids = [str(value) for value in unidirectional_connections_dict["currentProject"]]
        else:
            raise ValueError("Provide --n_projects or include currentProject in --unidirectional_connections.")

        project_uris = [URIRef(f"{preamble}/project_{project_id}") for project_id in project_ids]
        for project_uri in project_uris:
            g.add((project_uri, RDF.type, FOAF.Project))

    knows_edges = set()
    if use_rmat:
        if m_knows is None:
            raise ValueError("m_knows must be provided when use_rmat is enabled.")
        knows_edges = generate_rmat_knows_edges(
            n_people=n_people,
            m_knows=m_knows,
            a=rmat_a,
            b=rmat_b,
            c=rmat_c,
            d=rmat_d,
            seed=seed,
        )
    
    
    #GRAPH GENERATION
    #loop over the number of nodes to be created
    for i in range(n_people):
        #create a FOAF.Person Object and FOAF.name attribute for each node
        URI = URIs[i]
        g.add((URI, RDF.type, FOAF.Person))
        g.add((URI,FOAF.name, Literal(full_names[i])))
        
        #generate the attributes using the hierarchies
        #level 0 indicates the raw value of a hierarchy attribute (every allowed value is iin that column)
        for att in attributes_dict:
            g.add((URI, getattr(FOAF, att), Literal(random.choice(attributes_dict[att]["level_0"]))))

        if project_uris:
            lower = min_projects if min_projects is not None else 1
            upper = max_projects if max_projects is not None else len(project_uris)
            lower = max(1, lower)
            upper = min(len(project_uris), upper)
            if lower > upper:
                lower = upper

            selected_count = random.randint(lower, upper) if upper > 0 else 0
            selected_projects = random.sample(project_uris, selected_count) if selected_count > 0 else []
            for project_uri in selected_projects:
                g.add((URI, FOAF.currentProject, project_uri))
        
        #generate unidirectional connections
        #a person can work as maximum in ALL possible values of the respective unidirectional connection
        for uni in unidirectional_connections_dict:
            if uni == "currentProject":
                continue
            uni_connections = random.sample(unidirectional_connections_dict[uni], random.randint(1, len(unidirectional_connections_dict[uni])))
            for u in uni_connections:
                g.add((URI, getattr(FOAF, uni), Literal("%s" %u)))

        #generate bidirectional connections
        for bi in bidirectional_connections_dict:
            if use_rmat and bi == "knows":
                continue
            bidi_connections = random.sample(URIs[:i] + URIs[i+1:], random.randint(1, int(bidirectional_connections_dict[bi])))
            for b in bidi_connections:
                g.add((URI, getattr(FOAF,bi), b))

    if use_rmat:
        for person_a, person_b in knows_edges:
            uri_a = URIs[person_a]
            uri_b = URIs[person_b]
            g.add((uri_a, FOAF.knows, uri_b))
            g.add((uri_b, FOAF.knows, uri_a))

    #bind namespace to a prefix
    g.bind("foaf", FOAF)
    
    #Friends have been assigned randomly, however this has been done only in one direction
    #It is a condition that if x knows y, y should also know x (bidirectional logic)
    #Ensure that this condition is met
    for bi in bidirectional_connections_dict:
        #for every person x amd every friend of person x
        for person_x in g.subjects(RDF.type, FOAF.Person):
            for bidi in g.objects(person_x, getattr(FOAF, bi)):
                #for every other person y
                for person_y in g.subjects(RDF.type, FOAF.Person):
                    if person_x == person_y:
                        pass
                    #if friend of person x is person y, then add the person to the list of friends of person y (if not already there)
                    if bidi == person_y:
                        if person_x in [f for f in g.objects(person_y, getattr(FOAF, bi))]:
                            pass
                        else:
                            g.add((person_y, getattr(FOAF, bi), person_x))
                    else:
                        pass
    
    #save the graph to data/generated_graphs/
    #storage logic is the following: <graph_name>_<number_of_people_in_the_graph>_<generation_timestamp>.txt
    timestamp = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
    if output_dir is None:
        destination_path = Path(f"data/generated_graphs/{graph_name}_{n_people}_{timestamp}.ttl")
    else:
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        destination_path = output_path / f"{graph_name}_{n_people}_{timestamp}.ttl"

    destination_file = str(destination_path)
    g.serialize(format="ttl", destination = destination_file)
    

    print("Job finished successfully. Exiting...")
    print(f"Graph destination path: {destination_file}")
    print(f"Number of people: {n_people}")
    print(f"Attributes: {attributes_dict.keys()}")
    print(f"Unidirectional connections: {unidirectional_connections_dict}")
    print(f"Bidirectional connections: {bidirectional_connections_dict}")
    print(f"Preamble: {preamble}")
    print("Shutting down...")

    #return the generated graph
    return g