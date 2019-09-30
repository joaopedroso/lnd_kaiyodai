import unittest
import pandas as pd
import random
import numpy as np

def read_data(filename="../data/zipcode.csv.gz"):
    df = pd.read_csv(filename,index_col="zip")
    df.index = df.index.map(str)
    # df.index.astype('str', copy=False)
    # df['latitude'] = pd.to_numeric(df['latitude'])
    # df['longitude'] = pd.to_numeric(df['longitude'])
    return df

def sample_locations(df, n_locations, rnd_stat):
    sample = df.sample(n=n_locations, random_state=rnd_stat)
    province = sample['name1'].to_dict()
    town = sample['name2'].to_dict()
    address = sample['name3'].to_dict()
    latitude = sample['latitude'].to_dict()
    longitude = sample['longitude'].to_dict()
     
    return (province, town, address, latitude, longitude)


def mk_instance(df, n_plants, n_dcs, n_custs, n_prods, seed):
    random.seed(seed)
    rnd_stat = np.random.RandomState(seed=seed)

    # products
    prods = [f"P{p:02}" for p in range(1,n_prods+1)]
    weight = {prod:random.randint(1,10) for prod in prods}
     
    # customer's locations
    (province, town, address, latitude, longitude) = sample_locations(df, n_custs, rnd_stat)
    locations = [z for z in address.keys()]
    cust = {z:(latitude[z],longitude[z]) for z in locations}
    name = {z:("C-" + province[z] + town[z] + address[z]) for z in locations}   # names for all zip codes used
     
    # "Cust-Prod.csv"
    # demand[cust,prod] = value
    demand = {(c,p):random.randint(10,100) for c in cust for p in prods}
     
    # distribution center's location and bounds
    (province, town, address, latitude, longitude) = sample_locations(df, n_dcs, rnd_stat)
    locations = list(address.keys())
    dc = {z:(latitude[z],longitude[z]) for z in locations}
    dc_lb = {z:0 for z in locations}
    dc_ub = {z:(1000+25*random.randint(1,9)*len(cust)) for z in locations}
    name.update({z:("D-" + province[z] + town[z] + address[z]) for z in locations})

    # plant's locations
    (province, town, address, latitude, longitude) = sample_locations(df, n_plants, rnd_stat)
    locations = list(address.keys())
    plnt = {z:(latitude[z],longitude[z]) for z in locations}
    name.update({z:("P-" + province[z] + town[z] + address[z]) for z in locations})
    # plant upper bounds (per product)
    tdemand = {p:sum(demand[c,p] for c in cust) for p in prods}
    plnt_ub = {(z,p):(tdemand[p]/n_plants + 1000) for z in locations for p in prods}

    return weight, cust, plnt, dc, dc_lb, dc_ub, demand, plnt_ub, name


def mk_instances():
    df = read_data()
    n_plants = 3
    n_prods = 5
    seeds = range(1,11)
    for n_custs in [3, 10, 100, 1000]:
        n_dcs = n_custs
        # print(f"testing location sample, number of customers: {n_custs}")
        for seed in seeds:
            # print(f"instance {n_custs}:{seed}")
            (weight, cust, plnt, dc, dc_lb, dc_ub, demand, plnt_ub, name) = \
                mk_instance(df, n_plants, n_dcs, n_custs, n_prods, seed)
            yield (weight, cust, plnt, dc, dc_lb, dc_ub, demand, plnt_ub, name)


class TestInstances(unittest.TestCase):
    def test_one(self):
        df = read_data()
        for n in [10, 100, 1000]:
            print(f"testing location sample, n:{n}")
            for seed in range(1,11):
                print(f"instance {n}:{seed}")
                (province, town, address, latitude, longitude) = sample_locations(df, n, seed)
                nout = 0
                for i in province:
                    print(i, latitude[i], longitude[i], town[i])
                    nout += 1
                    if nout >= 3:
                        print("...")
                        break

    def test_two(self):
        for (weight, cust, plnt, dc, dc_lb, dc_ub, demand, plnt_ub, name) in mk_instances():
            for dic in [cust, plnt, dc]:
                nout = 0
                for i in dic:
                    print(i, dic[i], name[i])
                    nout += 1
                    if nout >= 3:
                        print("...\n")
                        break
            
                    

if __name__ == '__main__':
    unittest.main()
