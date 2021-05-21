from graphviz import Digraph


class _Bit:
    def __init__(self, value):
        self.value = value

    def is_similar(self, other):
        return type(self) is type(other) and self.value == other.value


class _Node:
    lo = _Bit(False)
    hi = _Bit(True)

    def __init__(self, variable, parents=None, function_in=None):
        self.variable = variable
        self.__parents = [] if parents is None else parents
        self.__function_in = [] if function_in is None else function_in
        self.hi = _Node.lo
        self.lo = _Node.lo

    def is_similar(self, other):
        return type(self) is type(other) and self.variable == other.variable and self.hi.is_similar(
            other.hi) and self.lo.is_similar(other.lo)

    @property
    def parents(self):
        return self.__parents

    @property
    def function_in(self):
        return self.__function_in

    def add_parent(self, parent):
        if parent not in self.__parents:
            self.__parents.append(parent)

    def remove_parent(self, parent):
        if parent in self.__parents:
            self.__parents.remove(parent)

    def add_function_in(self, function_in):
        if function_in not in self.__function_in:
            self.__function_in.append(function_in)
            function_in.node = self

    def remove_function_in(self, function_in):
        if function_in in self.__function_in:
            self.__function_in.remove(function_in)


class Function:

    def __init__(self, name, node, bdd_obj):
        self.name = name
        self.node = node
        self.node.add_function_in(self)
        self.bdd = bdd_obj
        self.__visited = []

    def solve(self, *args, **kwargs):
        curr_node = self.node
        d = dict(zip(self.bdd.in_bits, args))
        d = dict(**d, **kwargs)
        if len(d) != len(self.bdd.in_bits):
            raise Exception('Number of inputs should equal to number of input bits. '
                            f'Expected: {len(self.bdd.in_bits)}, Got: {len(d)}')

        while True:
            if type(curr_node) is _Bit:
                return curr_node.value
            curr_node = curr_node.hi if d[curr_node.variable] else curr_node.lo

    @property
    def node_count(self):
        self.__visited = []
        return self.__node_count(self.node)

    def __node_count(self, node):
        if type(node) is _Bit:
            return 0
        ret = (node not in self.__visited) + self.__node_count(node.hi) + self.__node_count(node.lo)
        self.__visited.append(node)
        return ret


class BDD:

    def __init__(self, *in_bits):
        self.in_bits = in_bits
        self.nodes = []
        self.out_bits = []
        self.out_functions = dict()
        self.n = len(in_bits)

    def add_function(self, out, *min_terms):
        assert all([i < 2 ** self.n for i in min_terms])

        self.out_bits.append(out)

        min_terms = [self.bin_list(i) for i in min_terms]

        top_node = _Node(self.in_bits[0])
        self.nodes.append(top_node)

        out_function = Function(out, top_node, self)
        self.out_functions[out] = out_function

        for min_term in min_terms:
            self.add_to_function(out_function, min_term)

        return out_function

    def add_to_function(self, out_function, min_term_bin_list):
        curr_node = out_function.node
        for i in range(1, self.n):
            prev_bit = min_term_bin_list[i - 1]
            curr_bit = min_term_bin_list[i]
            bit_name = self.in_bits[i]
            if prev_bit:
                if type(curr_node.hi) is _Bit:
                    node = _Node(bit_name, [curr_node])
                    self.nodes.append(node)
                    curr_node.hi = node
                    curr_node = node
                else:
                    curr_node = curr_node.hi
                if i == self.n - 1:
                    if curr_bit:
                        curr_node.hi = _Node.hi
                    else:
                        curr_node.lo = _Node.hi
            else:
                if type(curr_node.lo) is _Bit:
                    node = _Node(bit_name, [curr_node])
                    self.nodes.append(node)
                    curr_node.lo = node
                    curr_node = node
                else:
                    curr_node = curr_node.lo
                if i == self.n - 1:
                    if curr_bit:
                        curr_node.hi = _Node.hi
                    else:
                        curr_node.lo = _Node.hi

    def remove_node(self, node):
        # assert node not in ([nd.hi for nd in self.nodes] + [nd.lo for nd in self.nodes])
        if node in self.nodes:
            self.nodes.remove(node)
            if type(node.hi) is _Node:
                node.hi.remove_parent(node)
                if not node.hi.parents and not node.hi.function_in:
                    self.remove_node(node.hi)
            if type(node.lo) is _Node:
                node.lo.remove_parent(node)
                if not node.lo.parents and not node.lo.function_in:
                    self.remove_node(node.lo)

    def reduce_graph(self):
        initial_node_count = len(self.nodes)
        modified = True

        while modified:
            modified = False
            for i in range(len(self.nodes)):
                for j in range(i + 1, len(self.nodes)):
                    node_i = self.nodes[i]
                    node_j = self.nodes[j]
                    if node_i.is_similar(node_j):
                        modified = True

                        for parent in node_i.parents:
                            node_j.add_parent(parent)
                            if parent.hi is node_i:
                                parent.hi = node_j
                            if parent.lo is node_i:
                                parent.lo = node_j

                        for function_in in node_i.function_in:
                            node_j.add_function_in(function_in)
                        self.remove_node(node_i)
                        break
                if modified:
                    break

            else:
                for node in self.nodes:
                    if node.hi is node.lo:
                        modified = True

                        for parent in node.parents:
                            if parent.hi is node:
                                parent.hi = node.hi
                            else:
                                parent.lo = node.hi
                            if type(node.hi) is _Node:
                                node.hi.add_parent(parent)

                        if type(node.hi) is _Node:
                            for function_in in node.function_in:
                                node.hi.add_function_in(function_in)
                        elif node.function_in:
                            for function_in in node.function_in:
                                function_in.node = node.hi

                        self.remove_node(node)
                        break

        return initial_node_count, len(self.nodes)

    def bin_list(self, term):
        ret = [i == '1' for i in str(bin(term))[2:]]
        ret = [False for i in range(self.n - len(ret))] + ret
        return tuple(ret[-self.n:])

    def graph(self, name='Graph', save=False):
        graph = Digraph(format='png')
        graph.node(str(id(_Node.hi)), str(_Node.hi.value), shape='box')
        graph.node(str(id(_Node.lo)), str(_Node.lo.value), shape='box')
        for node in self.nodes:
            graph.node(str(id(node)), node.variable, shape='circle')
            graph.edge(str(id(node)), str(id(node.hi)), 'True', color='green')
            graph.edge(str(id(node)), str(id(node.lo)), 'False', color='red')
            for function_in in node.function_in:
                graph.node(str(id(function_in)), function_in.name, shape='doublecircle')
                graph.edge(str(id(function_in)), str(id(node)), 'In', color='blue')

        if save:
            graph.render(name, cleanup=True)
        return graph
