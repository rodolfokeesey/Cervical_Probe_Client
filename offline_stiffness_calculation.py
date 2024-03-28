import numpy as np
from scipy.ndimage import median_filter
import scipy.signal as sps
import sympy as sym
import matplotlib.pyplot as plt
import ruptures as rpt


# This is a testing script for calculating stiffness from the force data and the set indentation

file_path = "C:\\Users\\rdkee\\Documents\\Github\\Cervical_Probe_Client\\data\\gel_12.csv"

loaded_data = np.loadtxt(file_path, delimiter=",")
y_force = loaded_data[:,1] 
y_pos = loaded_data[:,0]

# make the time vector
x = list(range(len(y_force)))

# Truncate the deadzone and initialize holding arrays:
ff = np.zeros((3))
ff_ind = np.zeros((3))
trial_start = 350 # in indices
trunc_force = y_force[trial_start:-1]

# Search for onset given the number of boops
model = "l1"  # "l1", "l2", "rbf"
#algo = rpt.Dynp(model=model, min_size=3, jump=5).fit(trunc_force)
#my_bkps = algo.predict(n_bkps=6)

algo = rpt.KernelCPD(kernel='linear', min_size=2, jump=1).fit(trunc_force)
my_bkps = algo.predict(n_bkps=6)
lag = 10
adj_bkps = np.array(my_bkps) - np.array([lag,0,lag,0,lag,0,0])
# show results

rpt.show.display(trunc_force, adj_bkps, figsize=(10, 6))

# Hold the results
fi = [trunc_force[x] for x in adj_bkps[[0,2,4]]]
fi_ind = adj_bkps[[0,2,4]]
ff[0], ff[1], ff[2] = np.max(trunc_force[adj_bkps[0]:adj_bkps[1]]), np.max(trunc_force[adj_bkps[2]:adj_bkps[3]]), np.max(trunc_force[adj_bkps[4]:adj_bkps[5]])
ff_ind[0], ff_ind[1], ff_ind[2] = np.argmax(trunc_force[adj_bkps[0]:adj_bkps[1]]), np.argmax(trunc_force[adj_bkps[2]:adj_bkps[3]]), np.argmax(trunc_force[adj_bkps[4]:adj_bkps[5]])
plt.show()


# Calculate the stiffness

f_frict = 0.4 # friction force in newtons
h = 0.004 # indentation in meters
v = 0.5 # What is this?
P = ff[2] - fi[2] - f_frict # force in newtons
R = .0024052 # radius of the probe in meters

E = (0.75 * P * (1 - v**2)) / (R**0.5 * h**(3/2))
print("the calculated Elastic Modulus is %s" % E)