# synthetic-rdf-graph

Synthetic RDF graph generator for FOAF-style datasets, designed to produce person-centric graphs with configurable attributes, relationships, and optional R-MAT social structure.

## Data generator (CLI)

Run the generator from the project root:

```bash
python3 graph_generator/main.py [OPTIONS]
```

### Required arguments

- `--n_people <int>`: Number of `foaf:Person` nodes to generate.
- `--preamble <string>`: Base URI prefix used for generated resources.
- `--graph_name <string>`: Prefix for output file names.

### Optional arguments

- `--attributes <name1 name2 ...>`: FOAF attribute names to populate.
- `--hierarchies <path1 path2 ...>`: Hierarchy CSV files (same count/order as `--attributes`).
- `--unidirectional_connections <name values ...>`: Literal-based relations, where values are provided as a list string (for example `"[A, B, C]"`).
- `--bidirectional_connections <name max ...>`: Person-to-person relations with a random max per person (for example `knows 5`).
- `--seed <int>`: Random seed (default: `11`) for reproducibility.

R-MAT options for `foaf:knows` generation:

- `--use_rmat`: Enables R-MAT generation for `knows`.
- `--m_knows <int>`: Exact number of undirected `knows` edges (required with `--use_rmat`).
- `--rmat_a|--rmat_b|--rmat_c|--rmat_d <float>`: R-MAT quadrant probabilities (defaults: `0.57, 0.19, 0.19, 0.05`; should sum to `1.0`).

Project assignment options:

- `--n_projects <int>`: Number of `foaf:Project` resources.
- `--min_projects <int>` / `--max_projects <int>`: Project links per person.

### Examples

Minimal run:

```bash
python3 graph_generator/main.py \
	--n_people 256 \
	--preamble "http://example.org/foaf" \
	--graph_name "graph_generator_test"
```

Generate people with hierarchy-based attributes and random `knows` links:

```bash
python3 graph_generator/main.py \
	--n_people 256 \
	--preamble "http://example.org/foaf" \
	--graph_name "graph_generator_test" \
	--attributes age gender based_near \
	--hierarchies data/inputs/hierarchies/age.csv data/inputs/hierarchies/gender.csv data/inputs/hierarchies/austrian_cities.csv \
	--bidirectional_connections knows 5
```

Generate with R-MAT `knows` plus projects:

```bash
python3 graph_generator/main.py \
	--n_people 256 \
	--preamble "http://example.org/foaf" \
	--graph_name "graph_generator_test" \
	--use_rmat \
	--m_knows 768 \
	--seed 11 \
	--n_projects 15 \
	--min_projects 3 \
	--max_projects 7
```

Combined example (attributes + R-MAT + projects):

```bash
python3 graph_generator/main.py \
	--n_people 256 \
	--preamble "http://example.org/foaf" \
	--graph_name "graph_generator_test" \
	--attributes age gender based_near \
	--hierarchies data/inputs/hierarchies/age.csv data/inputs/hierarchies/gender.csv data/inputs/hierarchies/austrian_cities.csv \
	--use_rmat \
	--m_knows 768 \
	--seed 11 \
	--n_projects 15 \
	--min_projects 3 \
	--max_projects 7
```

When `--use_rmat` is enabled, `foaf:knows` edges are controlled by `--m_knows`, so `--bidirectional_connections knows ...` is not needed.

## Output

Generated Turtle files are written to `data/generated_graphs/` using:

`<graph_name>_<n_people>_<timestamp>.ttl`