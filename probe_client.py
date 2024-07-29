import serial
import struct
import time
import random
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
                self.ser = serial.Serial('COM4', 115200, timeout = 1)
                self.connected = True
            except:
                print("Failed to connect")
        else:
            print("Already connected")

    def disconnect(self):
        try:
            self.ser.close()
            self.connected = False
            print("Disconnected")
        except:
            print("Failed to disconnect")

    def send_command(self,command):
        # encodes the string to bytes
        self.ser.write(command.encode('utf-8') + b'\n')
    
    def send_command_int(self, float1, int1, int2):
        """
        Sends a command to the cervical probe with two integer arguments. The first integer gives
        the direction to move the probe in, and the second integer gives the number of steps to move.
        """
        
        bytes_to_send = struct.pack('<fii', float1, int1, int2)
        self.ser.write(bytes_to_send)

    def receive_data(self):
        """
        Reads one line from the serial port
        Decode bytes to string and strip newline characters, then split based on commas
        """
        
        data = self.ser.readline().decode('utf-8').rstrip().split(",")
        try: 
            data = [float(i) for i in data]
        except:
            print("Failed to convert data to float")
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
            try:
                prev_position = data[0]
            except:
                prev_position = 0
            data = self.receive_data()
            data[0] = self.low_pass_filter(data[0], prev_position, 0.1)
            queue.put(data)
        
    def start_stream(self):
        #assert self.connected
        self.streaming = True

    def stop_stream(self):
        self.streaming = False
        try:
            self.worker_thread.join()
            print("Streaming thread joined!")
        except:
            print("Unable to close streaming thread")

    def handle_stream_spoof(self, queue: Queue[list[float]]):
        self.start_stream()
        self.worker_thread = threading.Thread(
            target = self.stream_worker_spoof, args = (queue,))
        self.worker_thread.start()
        # Make the thread a daemon
        self.worker_thread.deamon = True

    def stream_worker_spoof(self, queue: Queue[list[float]]):
        while self.streaming == True:
            data = [random.randint(10, 20), random.randint(1, 5)]
            time.sleep(.0125)
            queue.put(data)
    
    def low_pass_filter(self,current_value, previous_filtered_value, alpha):
        """
        Simple exponential moving average low pass filter.
        alpha: smoothing factor within [0, 1], where closer to 1 is less smoothing.
        """
        return alpha * current_value + (1 - alpha) * previous_filtered_value
        