import numpy as np
import matplotlib.pyplot as plt
from scipy import stats


# Enter in the observed values from the calibration data
newtons = np.array([0, 0.1, 0.2, 0.5, 1, 2])
mv_readings = np.array([-67700, -78800,-90600,-125950,-185900,-304400])

# Run a linear regression to find the slope and intercept
res = stats.linregress(mv_readings, newtons)

print(f"R-squared: {res.rvalue**2:.6f}")
print(f"Slope: {res.slope:.6f}")
print(f"Intercept: {res.intercept:.6f}")

plt.plot(mv_readings, newtons, 'o', label='original data')
plt.plot(mv_readings, res.intercept + res.slope*mv_readings, 'r', label='fitted line')
plt.legend()
plt.show()

