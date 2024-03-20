import numpy as np
import probe_client as pc
import time
from queue import Queue
import probe_buffer as pb
import sys
from PyQt5.QtWidgets import QApplication, QMainWindow, QPushButton, QVBoxLayout, QHBoxLayout, QWidget, QTreeView, QFileSystemModel, QListView
from PyQt5.QtCore import QTimer, QDir
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
        self.setCentralWidget(self.graphWidget1)

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
        self.probe.handle_stream(self.data_q)

        # This is where we plot the data
        self.force_line = self.graphWidget1.plot([], [], pen = 'red')
        self.pos_line  = self.graphWidget1.plot([], [], pen = 'green')

        self.init_ui()

        self.timer = QTimer()
        self.timer.setInterval(33)  # Interval in milliseconds
        self.timer.timeout.connect(self.update_plot_data)
        self.timer.start()

    def init_ui(self):
        """ Initializes the user interface. Defines the button and graph layout"""

        # Main Layout ()
        main_layout = QHBoxLayout()

        # Sets up file system model
        model = QFileSystemModel()
        model.setRootPath(QDir.rootPath())

        tree = QTreeView()
        tree.setModel(model)
        tree.setRootIndex(model.index(QDir.rootPath()))
        tree.setColumnWidth(0, 250)
        tree.setSortingEnabled(True)

        
        # File Explorer Layout (column 1)
        col1 = QVBoxLayout()

        # Add the tree view
        col1.addWidget(tree)


        # Call back Plot Layout (column 2)

        # Real Time Plot Layout (column 3)
        layout = QVBoxLayout()
        layout.addWidget(self.graphWidget1)

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

        # Column 3, making the final layout
        layout.addLayout(sublay2)

        # Final layout
        main_layout.addLayout(col1)
        main_layout.addLayout(layout)

        container = QWidget()
        container.setLayout(main_layout)
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
        y_force = self.data_buffer.bufdata[:,1] 
        y_pos = self.data_buffer.bufdata[:,0]
        x = list(range(len(y_force))) 
        
        new_height = y_force[-1]
        #self.graphWidget2.setOpts(height=new_height)
        self.force_line.setData(x, y_force)  # Update the data
        self.pos_line.setData(x, y_pos)

    
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
        # attempt to add to the buffer
        try:
            self.data_buffer.add_data(items)
        except:
            pass

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
