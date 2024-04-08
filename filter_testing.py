import numpy as np
from scipy.ndimage import median_filter
import scipy.signal as sps
import matplotlib.pyplot as plt
import ruptures as rpt


# This is a testing script for filtering the positional and force data 


file_path = "C:\\Users\\rdkee\\Documents\\Github\\Cervical_Probe_Client\\data\\forearm_newtons_test.csv"

loaded_data = np.loadtxt(file_path, delimiter=",")
y_force = loaded_data[:,1] 
y_pos = loaded_data[:,0]

# make the time vector
x = list(range(len(y_force)))

# # filter the positional data

filtered_pos = median_filter(y_pos, size=5)

plt.figure(figsize=(10, 5))
#plt.plot(y_pos, label='Original')
plt.plot(filtered_pos, label='Filtered')
plt.legend()
plt.title('Time Series Data: Original vs. Median Filtered')
plt.xlabel('Index')
plt.ylabel('Value')

# # Find the start points of the signal

# # change point detection
# model = "rbf"  # "l1", "l2", "rbf"
# algo = rpt.Binseg(model=model, min_size=3, jump=5).fit(filtered_pos)
# my_bkps = algo.predict(n_bkps=6)
# # show results
# rpt.show.display(filtered_pos, my_bkps, figsize=(10, 6))



# # Process the force data for onset detection

# plt.figure(figsize=(10,5))
# plt.plot(y_force)

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

