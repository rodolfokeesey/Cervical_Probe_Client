import numpy as np
import probe_client as pc
import time
from queue import Queue
import probe_buffer as pb
import sys
from PyQt5.QtWidgets import QApplication, QMainWindow, QPushButton, QVBoxLayout, QHBoxLayout, QWidget
from PyQt5.QtCore import QTimer
from pyqtgraph import PlotWidget
import pyqtgraph as pg
import random


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        # Initialize the graphs
        self.graphWidget1 = pg.PlotWidget()
        self.barx = 1
        self.bar_height = 5
        self.graphWidget2 = pg.BarGraphItem(x = self.x, height = self.bar_height, x0 = 1, x1 = 2)
        self.setCentralWidget(self.graphWidget2)

        # Create an instance of the probe
        self.probe = pc.CervicalProbe()
        # Create the data queue to pass to the probe client
        self.data_q = Queue()
        # Initialize probe parameters
        self.num_channels = 2
        self.fs = 80
        # Create the data buffer to hold the data
        self.data_buffer = pb.ProbeBuffer(self.num_channels, self.fs)
        # Initialize the stream
        self.probe.handle_stream_spoof(self.data_q)

        # This is where we plot the data
        self.data_line = self.graphWidget.plot([], [])

        self.init_ui()

        self.timer = QTimer()
        self.timer.setInterval(33)  # Interval in milliseconds
        self.timer.timeout.connect(self.update_plot_data)
        self.timer.start()

    def init_ui(self):
        """ Initializes the user interface. Defines the button and graph layout"""


        # Main Layout
        layout = QVBoxLayout()
        layout.addWidget(self.graphWidget)

        # Lower Sublayout (Holds buttons)
        sublay2 = QHBoxLayout()

        # Adding Buttons
        # Retract Button
        ret_btn = QPushButton('Retract', self)
        ret_btn.clicked.connect(self.retract_probe)  # Connect to a function
        sublay2.addWidget(ret_btn)
        #Extend Button
        ext_btn = QPushButton('Extend', self)
        ext_btn.clicked.connect(self.extend_probe)  # Connect to a function
        sublay2.addWidget(ext_btn)

        # Making the final layout
        layout.addLayout(sublay2)

        container = QWidget()
        container.setLayout(layout)
        self.setCentralWidget(container)
    
    def closeEvent(self, event):
        """ This function is called when the window is closing"""
        self.cleanup()
        event.accept()

    def cleanup(self):
        """ Stops the probe stream and disconnects from the serial connection on closure"""
        print("Joining threads...")
        self.probe.stop_stream()
        print("Terminating serial connection...")
        self.probe.disconnect()

    def update_plot_data(self):
        """ Graphs data from the probe data buffer"""
        self.queue_to_buffer()
        y = self.data_buffer.bufdata[:,1]  # Replace with real data
        x = list(range(len(y)))  # Replace with real data
        
        new_height = y[-1]
        self.graphWidget2.setOpts(height=new_height)
        self.data_line.setData(x, y)  # Update the data
    
    def queue_to_buffer(self):
        """ Pulls data from the """
        items = []
        while not self.data_q.empty():
            try:
                item = self.data_q.get_nowait()  # Or q.get(timeout=0.1)
                items.append(item)
            except self.data_q.Empty:
                # This exception is thrown if the queue was empty. Break the loop.
                break
        self.data_buffer.add_data(items)

    def interp_state():
        print("Current State:")

    def on_click(self):
        print("Button clicked")

    def retract_probe(self):
        try:
            self.probe.send_command("retract")
            print("Retracting Probe...")
        except:
            print("Failed to send command")

    def extend_probe(self):
        try:
            self.probe.send_command("extend")
            print("Extending Probe...")
        except:
            print("Failed to send command")


if __name__ == '__main__':
    app = QApplication(sys.argv)
    main = MainWindow()
    main.show()

    app.aboutToQuit.connect(main.cleanup)
    sys.exit(app.exec_())
