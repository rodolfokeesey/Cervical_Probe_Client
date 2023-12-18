import serial
import time
import threading
from queue import Queue



class CervicalProbe:
    """
    Interfaces with the Cervical probe. Handles data streaming and sending commands
    """

    def __init__(self):
        self.connected = False
        self.connect()
        
    def connect(self):
        if not self.connected:
            try:
                self.ser = serial.Serial('COM3', 115200, timeout = 1)
                self.connected = True
            except:
                print("failed to connect")
        else:
            print("Already connected")

    def disconnect(self):
        try:
            self.ser.close()
            self.connected = False
            print("disconnected")
        except:
            print("failed to disconnect")

    def send_command(self,command):
        # encodes the string to bytes
        self.ser.write(command.encode('utf-8') + b'\n')

    def receive_data(self):
        # Reads one line from the serial port
        # Decode bytes to string and strip newline characters, then split based on commas
        data = self.ser.readline().decode('utf-8').rstrip().split(",") 
        data = [float(i) for i in data]
        return data
    
    def handle_stream(self, queue: Queue[list[float]]):
        assert self.connected
        self.start_stream()
        self.worker_thread = threading.Thread(
            target = self.stream_worker, args = (queue,))
        self.worker_thread.start()
        # Make the thread a daemon
        self.worker_thread.deamon = True
    
    def stream_worker(self, queue: Queue[list[float]]):
        while self.streaming == True:
            data = self.receive_data()
            queue.put(data)

        
    def start_stream(self):
        assert self.connected
        self.streaming = True

    def stop_stream(self):
        self.streaming = False
        try:
            self.worker_thread.join()
            print("Streaming thread joined")
        except:
            print("Unable to close streaming thread")
        


probe = CervicalProbe()
q = Queue()
probe.handle_stream(q)
time.sleep(2)
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
print(items)
probe.stop_stream()