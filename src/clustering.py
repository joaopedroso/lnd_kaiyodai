"""
clustering: Use scikit-learn models for clustering a set of distribution centers.

The aim is to select a predefined number of *candidates* for implementing
a distribution center.  Data are: 

  - number of candidates to select
  - customer locations
  - potential distribution center locations
  - plant locations

See `TestSolving` below for examples of usage.
"""
import random
import unittest
import numpy as np
import pandas as pd
# from geopy.distance import geodesic as distance
from geopy.distance import great_circle as distance
from sklearn.cluster import AgglomerativeClustering

def preclustering(cust, dc, prods, demand, n_clusters):
    """
    Clustering as a predecessor for optimization, to be used in logistics network design

    :rtype: list of selected dc's (a subset of `dc`)
    :cust: dict associating a customer id to its location as (latitute, longitude)
    :dc: dict associating a distribution center id to its (latitute, longitude)
    :prods: list (set) of products 
    :demand: demand[k,p] -> units of `p` demanded by customer `k`
    :n_clusters: number of clusters to use
    """
    # start = time.process_time()
    key_dc = list(dc.keys())
    n_dc = len(key_dc)
    d = np.zeros((n_dc,n_dc), np.int)
    for i in range(n_dc):
        for j in range(i,n_dc):
            d[i,j] = distance(dc[key_dc[i]], dc[key_dc[j]]).kilometers + .5  # round to closest integer
            # print(geodesic(origin, dest).meters)  # 23576.805481751613
            # print(geodesic(origin, dest).kilometers)  # 23.576805481751613
            # print(geodesic(origin, dest).miles)  # 14.64994773134371
            d[j,i] = d[i,j]
    # print("distance (dc's):")
    # print(d)
    # end = time.process_time()
    # print("{} seconds computing distances".format(end-start))

    # start = time.process_time()
    # heuristic: assign demand from customers to closest dc
    dc_dem = np.zeros((n_dc,), np.int)
    for z in cust:
        dists = np.array([distance(cust[z], dc[k]).kilometers + .5 for k in key_dc], np.int)
        imin = np.argmin(dists)
        dc_dem[imin] += sum(demand[z,p] for p in prods)
        # print(z, dists)
        # print("imin", imin, dc_dem[imin])
    # end = time.process_time()
    # print("{} seconds computing demands".format(end-start))
    
    # start = time.process_time()
    n_clusters = min(n_clusters,n_dc)
    model = AgglomerativeClustering(linkage='average',
                                    affinity='precomputed',
                                    connectivity=None, # knn_graph,
                                    n_clusters=n_clusters)
    model.fit(d)
    # end = time.process_time()
    # print("{} seconds clustering".format(end-start))

    # start = time.process_time()
    cluster_dc = []
    for i in range(n_clusters):
        indices = np.where(model.labels_ == i)[0]
        demands = [dc_dem[j] for j in indices]
        print(i, indices, demands)
        dmax = np.argmax(demands)
        # print(i, indices, demands, indices[dmax])
        cluster_dc.append(indices[dmax])
    # end = time.process_time()
    # print("{} seconds choosing dc in cluster".format(end-start))

    return [key_dc[i] for i in cluster_dc]


class TestClustering(unittest.TestCase):
    def test_one(self):
        """
        Test optimizing the location of a small number of dc's from set of candidates
        """
        from mk_instances import mk_instances
        import time
        for (weight, cust, plnt, dc, dc_lb, dc_ub, demand, plnt_ub, name) in mk_instances():
            start = time.process_time()
            prods = weight.keys()
            n_clusters = (10 + len(dc))//5
            cluster_dc = preclustering(cust, dc, prods, demand, n_clusters)
            end = time.process_time()
            print("clustered dc's, used {} seconds".format(end-start))
            print("selected", len(cluster_dc), "dc's out of", len(dc.keys()), "possible positions")


if __name__ == '__main__':
    unittest.main()
