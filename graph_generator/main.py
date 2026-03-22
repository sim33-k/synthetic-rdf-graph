#Library imports
import argparse
from pathlib import Path
from helpers import *
from namespace import *

PROJECT_ROOT = Path(__file__).resolve().parent.parent


def resolve_input_path(path_str: str) -> str:
    path = Path(path_str)
    if path.is_absolute():
        return str(path)

    cwd_candidate = Path.cwd() / path
    if cwd_candidate.exists():
        return str(cwd_candidate)

    return str(PROJECT_ROOT / path)


def resolve_hierarchy_path(path_str: str) -> str:
    resolved = Path(resolve_input_path(path_str))
    if resolved.exists():
        return str(resolved)

    file_name = Path(path_str).name
    candidates = []

    if Path(file_name).suffix:
        candidates.append(PROJECT_ROOT / "data/inputs/hierarchies" / file_name)
    else:
        candidates.append(PROJECT_ROOT / "data/inputs/hierarchies" / file_name)
        candidates.append(PROJECT_ROOT / "data/inputs/hierarchies" / f"{file_name}.csv")

    for candidate in candidates:
        if candidate.exists():
            return str(candidate)

    return str(resolved)

#argument parser
ap = argparse.ArgumentParser()
ap.add_argument("--attributes", nargs="+",
				help="Enter name of the attributes to be generated.", required=False)
ap.add_argument("--hierarchies", nargs="+",
				help="Enter the path to the hierarchies to be used to generate attributes. There should be exactly as many hierarchies as attributes.", required=False)
ap.add_argument("--unidirectional_connections", nargs="+",
				help="Enter the name of the unidirectional connections that should be generated and a list of possible values.", required=False)
ap.add_argument("--bidirectional_connections", nargs="+",
				help="Enter the name of the bidirectional connections that should be generated and the maximum amount of random connections to be generated between the nodes.", required=False)
ap.add_argument("--n_people", required=True, help="Enter number of people (nodes) that it is wished to have in the generated graph", type=int)
ap.add_argument("--preamble", required=True, help="Enter a customized preamble for the URIs", type=str)
ap.add_argument("--graph_name", required=True, help="Enter a customized named to be used as a preamble of your generated graph name", type=str)
ap.add_argument("--use_rmat", action="store_true", help="Use NetworKit R-MAT generation for foaf:knows edges.")
ap.add_argument("--m_knows", required=False, help="Exact number of undirected foaf:knows edges when --use_rmat is enabled.", type=int)
ap.add_argument("--rmat_a", required=False, help="R-MAT a parameter.", type=float, default=0.57)
ap.add_argument("--rmat_b", required=False, help="R-MAT b parameter.", type=float, default=0.19)
ap.add_argument("--rmat_c", required=False, help="R-MAT c parameter.", type=float, default=0.19)
ap.add_argument("--rmat_d", required=False, help="R-MAT d parameter.", type=float, default=0.05)
ap.add_argument("--seed", required=False, help="Random seed for reproducibility.", type=int, default=11)
ap.add_argument("--n_projects", required=False, help="Number of foaf:Project resources to create for currentProject.", type=int)
ap.add_argument("--min_projects", required=False, help="Minimum currentProject links per person.", type=int)
ap.add_argument("--max_projects", required=False, help="Maximum currentProject links per person.", type=int)
args = ap.parse_args()

# define a list of random first and last names to be used for random name generation
first_names = read_txt_file(str(PROJECT_ROOT / "data/inputs/names/first_names.txt"))
last_names = read_txt_file(str(PROJECT_ROOT / "data/inputs/names/last_names.txt"))

#load attributes from argparser
attributes_dict = {}
count = 0
if args.attributes and (not args.hierarchies or len(args.attributes) != len(args.hierarchies)):
    raise ValueError("When --attributes is provided, --hierarchies must be provided with the same number of entries.")

for attribute in (args.attributes or []):
    attributes_dict[attribute] = hierarchy_reader(resolve_hierarchy_path(args.hierarchies[count]))
    count = count + 1

#load unidirectional_connections
unidirectional_connections_dict = {}
for i in range(0, len(args.unidirectional_connections or []),2):
    unidirectional_connections_dict[args.unidirectional_connections[i]] = args.unidirectional_connections[i+1].strip('][').split(', ')

#load bidirectional_connections
bidirectional_connections_dict = {}
for i in range(0, len(args.bidirectional_connections or []),2):
    bidirectional_connections_dict[args.bidirectional_connections[i]] = args.bidirectional_connections[i+1]

#call the generate_rdf job
if __name__ == "__main__":
    generate_rdf(
        attributes_dict,
        unidirectional_connections_dict,
        bidirectional_connections_dict,
        args.preamble,
        int(args.n_people),
        args.graph_name, 
        first_names,
        last_names,
        use_rmat=args.use_rmat,
        m_knows=args.m_knows,
        rmat_a=args.rmat_a,
        rmat_b=args.rmat_b,
        rmat_c=args.rmat_c,
        rmat_d=args.rmat_d,
        seed=args.seed,
        n_projects=args.n_projects,
        min_projects=args.min_projects,
        max_projects=args.max_projects,
        output_dir=str(PROJECT_ROOT / "data/generated_graphs"))