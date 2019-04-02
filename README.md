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

### p_2_5

![loadsym](doc/p_2_5.svg)

### loadsym

![loadsym](doc/loadsym.svg)
