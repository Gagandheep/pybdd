from pybdd import BDD


if __name__ == '__main__':
    bdd = BDD('a', 'b', 'c')

    # Full Adder
    s = bdd.add_function('s', 1, 2, 4, 7)
    co = bdd.add_function('co', 3, 5, 6, 7)

    # a = 1, b = 0, c = 0
    print(s.solve(1, 0, 0), co.solve(1, 0, 0))
    # a = 1, b = 1, c = 0
    print(s.solve(*bdd.bin_list(6)), co.solve(*bdd.bin_list(6)))
    # a = 1, b = 1, c = 1
    print(s.solve(a=1, b=1, c=1), co.solve(a=1, b=1, c=1))

    bdd.graph('Before Reduction', save=True)
    bdd.reduce_graph()
    bdd.graph('After Reduction', save=True)
