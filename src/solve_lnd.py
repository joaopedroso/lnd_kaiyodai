"""
solve_lnd: Main example for testing logistics network design optimizer

This program illustrates how to use the optimization model implemented
in module `lnd.py`, with potential places for distribution centers
being pre-clustered by the method implemented in `clustering.py`.

Notice that for large instances, completing the tests may still take
a considerable time.
"""




import unittest
from geopy.distance import great_circle as distance
from lnd import lnd_ms, lnd_ss, mk_costs
from clustering import preclustering
from mk_instances import mk_instances


class TestClusteringAndSolving(unittest.TestCase):
    def test_one(self):
        """
        Test clustering a set of potential dc's, then optimizing the location of a small number of them
        """
        TIME_LIM = 300 # allow gurobi to use 5 minutes
        import time
        from mk_instances import mk_instances
        from clustering import preclustering

        models = {
            "multiple source":lnd_ms,
            "single source":lnd_ss
            }

        for k in models:
            for (weight, cust, plnt, dc, dc_lb, dc_ub, demand, plnt_ub, name) in mk_instances():
                print(f"* using {k} model *")
                print(f"*** new instance, {len(plnt)} plants + {len(dc)} dc's + {len(cust)} customers ***")

                # prepare costs for optimization part
                (tp_cost, del_cost, dc_fc, dc_vc) = mk_costs(plnt, dc, cust)

                # clustering part
                prods = weight.keys()
                n_clusters = (10 + len(dc))//5
                cluster_dc = preclustering(cust, dc, prods, demand, n_clusters)
                dc = cluster_dc

                # optimization part
                start = time.process_time()
                dc_num = (90 + len(dc))//50
             
                print(f"***** dc's clustered into {len(dc)} groups, for choosing {dc_num} dc's")
                model = models[k](weight, cust, dc, dc_lb, dc_ub, plnt, plnt_ub,
                                  demand, tp_cost, del_cost, dc_fc, dc_vc, dc_num)
                model.setParam('TimeLimit', TIME_LIM)
                model.optimize()
                # model.write("lnd.lp")
             
                EPS = 1.e-6
                for x in model.getVars():
                    if x.X > EPS:
                        print(x.varName, x.X)
             
                end = time.process_time()
                print(f"solving MIP used {end-start} seconds")
                print()


            
if __name__ == '__main__':
    unittest.main()
