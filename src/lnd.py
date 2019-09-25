"""
lnd: Gurobi models for logistic network design

There are two models:

  - lnd_ms, for multiple-source supply
  - lnd_ss, for single-source supply

The aim is to select a predefined number of places for implementing
a distribution center.  Data are: 

  - customer locations
  - potential distribution center locations
  - plant locations
  - demand, bounds and costs

See `TestSolving` below for examples of usage.
"""


import unittest
from geopy.distance import great_circle as distance
from gurobipy import *

# tqdm = lambda x: x
from tqdm import tqdm

def lnd_ms(weight, cust, dc, dc_lb, dc_ub, plnt, plnt_ub, demand, tp_cost, del_cost, dc_fc, dc_vc, dc_num):
    """
    Logistics network design, multiple source

    Gurobi model for multiple-source LND

    :rtype: object of class `Model`, as defined in `gurobipy`
    :weight: weight[p] -> unit weight for product `p`
    :cust: dict associating a customer id to its location as (latitute, longitude)
    :dc: dict associating a distribution center id to its (latitute, longitude)
    :dc_lb: dc_lb[k] -> lower bound for distribution center k [not used]
    :dc_ub: dc_ub[k] -> upper bound for distribution center k
    :plnt: dict associating a plant id to its (latitute, longitude)
    :plnt_ub: plnt_ub[k] -> upper bound for plant k
    :demand: demand[k,p] -> units of `p` demanded by customer `k`
    :tp_cost: unit transportation cost (from the plant)
    :del_cost: unit delivery cost (from a dc)
    :dc_fc: fixed cost for opening a dc
    :dc_vc: unit (variable) cost for operating a dc
    :dc_num: (maximum) number of distribution centers to open
    """
    prod = set(weight.keys())
    plnt_to_dc = [(i,j,p) for i in plnt for j in dc for p in prod if plnt_ub.get((i,p),0) > 0]
    dc_to_cust = [(j,k,p) for j in dc for k in cust for p in prod if demand[k,p] > 0]

    model = Model()
    x,y = {}, {}
    for (i,j,p) in plnt_to_dc + dc_to_cust:
        x[i,j,p] = model.addVar(vtype='C', name=f'x[{i},{j},{p}]')
     
    slack = {}
    for (k,p) in demand:
        if demand[k,p] > 0.:
            slack[k,p] = model.addVar(vtype="C", name=f"slack[{k},{p}]")
            
    for j in dc:
        y[j] = model.addVar(vtype='B', name=f'y[{j}]')
            
    model.update()
     
     
    Cust_Demand_Cons, DC_Flow_Cons, DC_Strong_Cons, DC_UB_Cons, DC_LB_Cons, Plnt_UB_Cons = {}, {}, {}, {}, {}, {}
     
    for k in tqdm(cust):
        for p in prod:
            if demand[k,p]>0.:
                Cust_Demand_Cons[k,p] = model.addConstr(
                    quicksum(x[j,k,p] for j in dc if (j,k,p) in dc_to_cust)  + slack[k,p]
                    ==
                    demand[k,p],
                    name=f'Cust_Demand_Cons[{k},{p}]'
                )
    for j in tqdm(dc):
        for p in prod:
            DC_Flow_Cons[j,p] = model.addConstr(
                quicksum(x[i,j,p] for i in plnt if (i,j,p) in plnt_to_dc)
                ==
                quicksum(x[j,k,p] for k in cust if (j,k,p) in dc_to_cust),
                name=f'DC_Flow_Cons[{j},{p}]'
            )        
    for (j,k,p) in dc_to_cust:
        DC_Strong_Cons[j,k,p] = model.addConstr(
            x[j,k,p]
            <=
            demand[k,p] * y[j],
            name=f'DC_Strong_Cons[{j},{k},{p}]'
        )
            
    for j in tqdm(dc):
        DC_UB_Cons[j] = model.addConstr(
            dc_ub[j] * y[j]
            >=
            quicksum(x[i,j,p] for i in plnt for p in prod if (i,j,p) in plnt_to_dc),
            name=f'DC_UB_Cons[{j}]'
        )
     
    # for j in tqdm(dc):
    #     DC_LB_Cons[j] = model.addConstr(
    #         dc_lb[j] * y[j]
    #         <=
    #         quicksum(x[i,j,p] for i in plnt for p o prod if (i,j,p) in plnt_to_dc),
    #         name=f'DC_LB_Cons[{j}]'
    #     )
        
    for i in tqdm(plnt):
        for p in prod:
            Plnt_UB_Cons[i,p] = model.addConstr(
                plnt_ub[i,p]
                >=
                quicksum(x[i,j,p] for j in dc if (i,j,p) in plnt_to_dc),
                name=f'Plnt_UB_Cons[{i},{p}]'
            )
            
    DC_Num_Cons = model.addConstr(
        quicksum(y[j] for j in dc)
        <=
        dc_num,
        name='DC_Num_Cons'
    )
        
    model.update()
     
    model.setObjective(
        quicksum(weight[p] * tp_cost[i,j] * x[i,j,p] for (i,j,p) in plnt_to_dc)  +
        quicksum(weight[p] * del_cost[j,k] * x[j,k,p] for (j,k,p) in dc_to_cust) +
        quicksum(dc_fc[j] * y[j] for j in dc) + 
        quicksum(dc_vc[j] * x[i,j,p] for (i,j,p) in plnt_to_dc) +
        quicksum(999999*slack[k,p] for k in cust for p in prod if demand[k,p]>0.)
    )
    model.update()
    return model


def lnd_ss(weight, cust, dc, dc_lb, dc_ub, plnt, plnt_ub, demand, tp_cost, del_cost, dc_fc, dc_vc, dc_num):
    """
    Logistics network design, single source

    Gurobi model for single-source LND

    :rtype: object of class `Model`, as defined in `gurobipy`
    :weight: weight[p] -> unit weight for product `p`
    :cust: dict associating a customer id to its location as (latitute, longitude)
    :dc: dict associating a distribution center id to its (latitute, longitude)
    :dc_lb: dc_lb[k] -> lower bound for distribution center k [not used]
    :dc_ub: dc_ub[k] -> upper bound for distribution center k
    :plnt: dict associating a plant id to its (latitute, longitude)
    :plnt_ub: plnt_ub[k] -> upper bound for plant k
    :demand: demand[k,p] -> units of `p` demanded by customer `k`
    :tp_cost: unit transportation cost (from the plant)
    :del_cost: unit delivery cost (from a dc)
    :dc_fc: fixed cost for opening a dc
    :dc_vc: unit (variable) cost for operating a dc
    :dc_num: (maximum) number of distribution centers to open
    """
    prod = set(weight.keys())
    plnt_to_dc = [(i,j,p) for i in plnt for j in dc for p in prod if plnt_ub.get((i,p),0) > 0]
    dc_to_cust = [(j,k,p) for j in dc for k in cust for p in prod if demand[k,p] > 0]

    model = Model()
    x,y = {}, {}
    z = {}
    for (i,j,p) in plnt_to_dc:
        x[i,j,p] = model.addVar(vtype='C', name=f'x[{i},{j},{p}]')
    for j in dc:
        for k in cust:
            z[j,k] = model.addVar(vtype="B",name=f"z[{j},{k}]")
                
    slack = {}
    for k in cust:
        slack[k]= model.addVar(vtype="C",name=f"slack[{k}]")
            
    for j in dc:
        y[j] = model.addVar(vtype='B', name=f'y[{j}]')
            
    model.update()
     
     
    Cust_Demand_Cons, DC_Flow_Cons, DC_Strong_Cons, DC_UB_Cons, DC_LB_Cons, Plnt_UB_Cons = {}, {}, {}, {}, {}, {}
     
    for k in cust:
        Cust_Demand_Cons[k] = model.addConstr(
                    quicksum(z[j,k] for j in dc) +slack[k]
                    == 1,
                    name=f'Cust_Demand_Cons[{k}]'
        )
    for j in dc:
        for p in prod:
            DC_Flow_Cons[j,p] = model.addConstr(
                quicksum(x[i,j,p] for i in plnt if (i,j,p) in plnt_to_dc)
                ==
                quicksum(  demand[k,p]*z[j,k] for k in cust),
                name=f'DC_Flow_Cons[{j},{p}]'
            )
    
    for j in dc:
        for k in cust:
            DC_Strong_Cons[j,k] = model.addConstr(
                    z[j,k]
                    <=
                    y[j],
                    name=f'DC_Strong_Cons[{j},{k}]'
                )
            
    for j in tqdm(dc):
        DC_UB_Cons[j] = model.addConstr(
            dc_ub[j] * y[j]
            >=
            quicksum(x[i,j,p] for i in plnt if (i,j,p) in plnt_to_dc),
            name=f'DC_UB_Cons[{j}]'
        )
     
    # for j in tqdm(dc):
    #    DC_LB_Cons[j] = model.addConstr(
    #        dc_lb[j] * y[j]
    #        <=
    #        quicksum(x[i,j,p] for i in plnt if (i,j,p) in plnt_to_dc),
    #        name=f'DC_LB_Cons[{j}]'
    #   )
        
    for i in tqdm(plnt):
        for p in prod:
            Plnt_UB_Cons[i,p] = model.addConstr(
                plnt_ub[i,p]
                >=
                quicksum(x[i,j,p] for j in dc if (i,j,p) in plnt_to_dc),
                name=f'Plnt_UB_Cons[{i},{p}]'
            )
            
    DC_Num_Cons = model.addConstr(
        quicksum(y[j] for j in dc)
        <=
        dc_num,
        name='DC_Num_Cons'
    )
        
    model.update()
     
    total_demand = {k:sum(demand[k,p] for p in prod) for k in cust}
    model.setObjective(
        quicksum(weight[p] * tp_cost[i,j] * x[i,j,p] for (i,j,p) in plnt_to_dc)  +
        quicksum(weight[p] * del_cost[j,k] * total_demand[k]* z[j,k] for j in dc for k in cust) +
        quicksum(dc_fc[j] * y[j] for j in dc) + 
        quicksum(dc_vc[j] * x[i,j,p] for (i,j,p) in plnt_to_dc) +
        quicksum(99999999*slack[k] for k in cust)
    )
    model.update()
    return model



def mk_costs(plnt, dc, cust):
    """
    Instantiate costs to a given set of plants, dc's and customers

    To be adpted to more realistic settings

    :rtype: tuple with transportation costs
    :plnt: dict associating a plant id to its (latitute, longitude)
    :dc: dict associating a distribution center id to its (latitute, longitude)
    """
    unit_tp_cost = 1 #  transportation cost (from the plant)
    unit_del_cost = 10 #  delivery cost (from a dc)
    unit_dc_fc = 1000 # fixed cost for opening a dc
    unit_dc_vc = 1 #  variable cost for operating a dc
    tp_cost = {}
    for i in plnt:
        for j in dc:
            tp_cost[i,j] = unit_tp_cost * distance(plnt[i], dc[j]).kilometers
    del_cost = {}
    dc_fc = {}
    dc_vc = {}
    for j in dc:
        dc_fc[j] = unit_dc_fc
        dc_vc[j] = unit_dc_vc
        for k in cust:
            del_cost[j,k] = unit_del_cost * distance(dc[j], cust[k]).kilometers
    return tp_cost, del_cost, dc_fc, dc_vc




class TestSolving(unittest.TestCase):
    def test_one(self):
        """
        Test optimizing the location of a small number of dc's from set of candidates
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
                start = time.process_time()
                (tp_cost, del_cost, dc_fc, dc_vc) = mk_costs(plnt, dc, cust)
                dc_num = (20 + len(dc))//10
             
                model = models[k](weight, cust, dc, dc_lb, dc_ub, plnt, plnt_ub, 
                                  demand, tp_cost, del_cost, dc_fc, dc_vc, dc_num)
                # model.write("lnd_ss.lp")
                model.setParam('TimeLimit', TIME_LIM)
                model.optimize()
             
                EPS = 1.e-6
                for x in model.getVars():
                    if x.X > EPS:
                        print(x.varName, x.X)
             
                end = time.process_time()
                print(f"solving MIP used {end-start} seconds")
                print()

            
if __name__ == '__main__':
    unittest.main()
