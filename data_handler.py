import numpy as np
import probe_client as pc
import time
from queue import Queue
import probe_buffer as pb


# Create an instance of the probe
probe = pc.CervicalProbe()

# Create the data queue to pass to the probe client
q = Queue()

# Initialize probe parameters
num_channels = 2
fs = 80

# Create the data buffer to hold the data
data_buffer = pb.ProbeBuffer(num_channels, fs)



probe.handle_stream_spoof(q)
time.sleep(.1)
# Read everything currently in the queue
items = []
while not q.empty():
    try:
        item = q.get_nowait()  # Or q.get(timeout=0.1)
        items.append(item)
    except q.Empty:
        # This exception is thrown if the queue was empty. Break the loop.
        break

# 'items' now contains all the elements that were in the queue
num_items = len(items)
print(num_items)
data_buffer.add_data(items)
print(data_buffer.bufdata)
probe.stop_stream()