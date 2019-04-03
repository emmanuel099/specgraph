# specgraph
Tool for visualizing Spectector traces.

For more information about Spectector please visit https://spectector.github.io/

## Usage

Run Spectector and redirect the output into a file:

```
spectector loadsym.muasm -a reach1 -c 'c([], [pc=0,x=0])' | tee loadsym.txt
```

Then start `specgraph.py` with `loadsym.txt`:

```
python specgraph.py -i loadsym.txt -o loadsym
```

Or run Spectector and redirect the output to `specgraph.py` directly:

```
spectector p_2_5.muasm -a reach1 -c 'c([], [pc=0])' | python specgraph.py -o p_2_5
```

## Result

* Rectangles correspond to the (labeled) instructions of the program. The octagon corresponds to the "final instruction".
* Gray edges show the control flow of the program.
* Red edges depict the trace found by Spectector. Each edge is labeled with the logical timestamp (`@{number}`) as well as the observations of the executed instruction.
* Dashed edges visualize the uncommitted speculative transactions along the trace.

### p_2_5

![loadsym](doc/p_2_5.svg)

### loadsym

![loadsym](doc/loadsym.svg)
