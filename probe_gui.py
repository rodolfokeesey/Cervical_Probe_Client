import numpy as np
import probe_client as pc
import time
from queue import Queue
import probe_buffer as pb
import sys
from PyQt5.QtWidgets import QApplication, QMainWindow, QPushButton, QVBoxLayout, QHBoxLayout, QWidget, QTreeView, QFileSystemModel, QRadioButton
from PyQt5.QtCore import QTimer, QDir
from pyqtgraph import PlotWidget
import pyqtgraph as pg
import random
import threading


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        # Initialize the graphs

        # This is the graph for the real time position plot
        self.graphWidget1 = pg.PlotWidget()
        # This is the graph for the  real time force plot
        self.graphWidget2 = pg.PlotWidget()
        # This is the callback graph for a previous reading position
        self.recall_pos = pg.PlotWidget()
        # This is the callback graph for a previous reading force
        self.recall_force = pg.PlotWidget()

        # Create an instance of the probe
        self.probe = pc.CervicalProbe()
        # Create the data queue to pass to the probe client
        self.data_q = Queue()
        # Initialize data session list to be saved
        self.data_session = []

        # Initialize the recording flag
        self.Recording = False
        # Initialize the busy flag
        self.Busy = False

        # Initialize the probe state estimation
        # Idea! Use a kalman filter to estimate the state of the probe.
        # When I say state, I mean the position and force of the probe.
        # When the probe is not moving AND there is no command in the queue,
        # then self.Busy = False.


        # Initialize probe parameters
        self.num_channels = 2
        self.fs = 80
        # Create the data buffer to hold the data
        self.data_buffer = pb.ProbeBuffer(self.num_channels, self.fs)
        # Initialize the stream
        self.probe.handle_stream(self.data_q)

        # This is where we plot the data
        self.force_line = self.graphWidget1.plot([], [], pen = 'red')
        self.pos_line  = self.graphWidget2.plot([], [], pen = 'green')

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
        self.model = QFileSystemModel()
        self.model.setRootPath(QDir.rootPath())

        self.tree = QTreeView()
        self.tree.setModel(self.model)
        self.tree.setRootIndex(self.model.index(QDir.rootPath()))
        self.tree.setColumnWidth(0, 250)
        self.tree.setSortingEnabled(True)
        self.tree.selectionModel().selectionChanged.connect(self.onSelectionChanged)

        
        # File Explorer Layout (column 1)
        col1 = QVBoxLayout()


        # Create Radio Buttons for recall mode:
        self.radio1 = QRadioButton("Current Reading Mode")
        self.radio2 = QRadioButton("Saved Reading Mode")
        self.radio1.setChecked(True)

        # Connect the signals to the slots
        self.radio1.toggled.connect(self.onRecallSelect)
        #self.radio2.toggled.connect(self.onRecallSelect)

        # Add the tree view for the file explorer
        col1.addWidget(self.radio1)
        col1.addWidget(self.radio2)
        col1.addWidget(self.tree)
        
        # Callback Plot Layout (column 2)
        col2 = QVBoxLayout()
        col2.addWidget(self.recall_pos)
        col2.addWidget(self.recall_force)

        # Real Time Plot Layout (column 3)
        layout = QVBoxLayout()
        layout.addWidget(self.graphWidget1)
        layout.addWidget(self.graphWidget2)

        # Lower Sublayout (Holds buttons)
        sublay2 = QHBoxLayout()

        # Adding Buttons
        # Retract Button
        ret_btn = QPushButton('Retract', self)
        ret_btn.clicked.connect(self.retract_probe)  # Connect to a function
        sublay2.addWidget(ret_btn)
        # Extend Button
        ext_btn = QPushButton('Extend', self)
        ext_btn.clicked.connect(self.extend_probe)  # Connect to a function
        sublay2.addWidget(ext_btn)
        # Test Stiffness Button
        tst_btn = QPushButton('Test Stiffness', self)
        tst_btn.clicked.connect(self.test_stiffness)  # Connect to a function
        sublay2.addWidget(tst_btn)

        # Column 3, making the final layout
        layout.addLayout(sublay2)

        # Final layout
        main_layout.addLayout(col1)
        main_layout.addLayout(col2)
        main_layout.addLayout(layout)

        container = QWidget()
        container.setLayout(main_layout)
        self.setCentralWidget(container)

    def onRecallSelect(self):
        """ Check which radio button is checked and perform actions """
        if self.radio1.isChecked():
            print("Option 1 is selected.")
        elif self.radio2.isChecked():
            print("Option 2 is selected.")

    def onSelectionChanged(self, selected, deselected):
        # Get the model index of the first selected item
        index = self.tree.selectionModel().currentIndex()
        # Check if the index is valid
        if index.isValid():
            # Get the file path from the model index
            self.filePath = self.model.filePath(index)
            print("Selected file:", self.filePath)
    
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

    def test_stiffness(self):
        """Creates a thread to call the stiffness test function"""
        self.worker_thread = threading.Thread(
            target = self.test_stiffness_thread)
        self.worker_thread.start()
        # Make the thread a daemon
        self.worker_thread.deamon = True

    def test_stiffness_thread(self):
        try:
            print("Testing Stiffness...")
            print("Trial One...")
            self.probe.send_command("retract")
            time.sleep(0.5)
            self.probe.send_command("extend")
            time.sleep(0.5)
            self.probe.send_command("retract")
            print("Trial Two...")
            time.sleep(1)
            self.probe.send_command("extend")
            time.sleep(0.5)
            self.probe.send_command("retract")
            print("Trial Three...")
            time.sleep(1)
            self.probe.send_command("extend")
            time.sleep(0.5)
            self.probe.send_command("retract")
        except:
            print("Failed to send command")


if __name__ == '__main__':
    app = QApplication(sys.argv)
    main = MainWindow()
    main.show()

    app.aboutToQuit.connect(main.cleanup)
    sys.exit(app.exec_())
