from d3graph import d3graph

# 1. Initialize
d3 = d3graph()

# 2. Load the 'bigbang' example adjacency matrix
adjmat = d3.import_example('bigbang')

# 3. Build the graph layout while forcing custom properties directly
# This blocks the library from running its default, buggy color-mapper
node_count = adjmat.shape[0]
valid_colors = ["#86CA68"] * node_count

d3.graph(adjmat, color=valid_colors, size=15, opacity=0.8)

# 4. Write to file
d3.show(filepath='./d3graph_bigbang.html')