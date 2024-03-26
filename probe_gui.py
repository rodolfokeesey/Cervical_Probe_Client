import numpy as np
import probe_client as pc
import time
from queue import Queue
import probe_buffer as pb
import sys
from PyQt5.QtWidgets import QApplication, QMainWindow, QPushButton, QVBoxLayout, QHBoxLayout, QWidget, QTreeView, QFileSystemModel, QRadioButton, QLineEdit, QLabel
from PyQt5.QtCore import QTimer, QDir
from pyqtgraph import PlotWidget
import pyqtgraph as pg
import os
import random
import threading
import copy


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        # Initialize the pathing
        self.current_directory = os.getcwd()
        print("Current directory:", self.current_directory)
        self.data_path = os.path.join(self.current_directory, "data")
        print("Current data directory:", self.data_path)

        # Initialize the graphs

        # This is the graph for the real time position plot
        self.graphWidget1 = pg.PlotWidget()
        # This is the graph for the real time force plot
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
        self.loaded_data = []

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
        # Real time feed
        self.force_line = self.graphWidget1.plot([], [], pen = 'red')
        self.pos_line  = self.graphWidget2.plot([], [], pen = 'green')

        # Callback feed
        self.recall_force_line = self.recall_pos.plot([], [], pen = 'red')
        self.recall_pos_line  = self.recall_force.plot([], [], pen = 'green')

        self.init_ui()

        # Initialize the timer to record all the data in the buffer
        self.record_timer = QTimer()
        self.record_timer.setSingleShot(True)
        self.record_timer.setInterval(5000)  # Interval in milliseconds
        self.record_timer.timeout.connect(self.record_buffer)


        # Initialize the timer to update the live plot
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
        self.model.setRootPath(self.data_path)

        self.tree = QTreeView()
        self.tree.setModel(self.model)
        self.tree.setRootIndex(self.model.index(self.data_path))
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

        # Last Sublayout (Holds the filename inputs, and the save command)
        sublay3 = QHBoxLayout()

        # Adding Filename Field Input
        self.lineEdit = QLineEdit()
        self.lineEdit.setPlaceholderText("Enter a filename here")
        sublay3.addWidget(self.lineEdit)

        # Extend Button
        save_btn = QPushButton('Save Data', self)
        save_btn.clicked.connect(self.save_data)  # Connect to a function
        sublay2.addWidget(save_btn)



        # Column 3, making the final layout
        layout.addLayout(sublay2)
        layout.addLayout(sublay3)

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
            try:
                print("Displaying Current Session Data.")
                self.update_callback_plot()
            except:
                print("No data to display.")
        elif self.radio2.isChecked():
            try:
                print("Displaying Loaded Session Data.")
                self.update_callback_plot()
            except:
                print("No data to display.")

    def onSelectionChanged(self, selected, deselected):
        # Get the model index of the first selected item
        index = self.tree.selectionModel().currentIndex()
        # Check if the index is valid
        if index.isValid():
            # Get the file path from the model index
            self.filePath = self.model.filePath(index)
            print("Selected file:", self.filePath)
            self.load_data()
            if self.radio2.isChecked():
                try:
                    print("Displaying Loaded Session Data.")
                    self.update_callback_plot()
                except:
                    print("No data to display.")
    
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
        
        #self.graphWidget2.setOpts(height=new_height)
        self.force_line.setData(x, y_force)  # Update the data
        self.pos_line.setData(x, y_pos)

    def update_callback_plot(self):
        """ Graphs data from the probe data buffer"""
        if self.radio1.isChecked():
            try:
                y_force = self.data_session[:,1] 
                y_pos = self.data_session[:,0]
                x = list(range(len(y_force)))
                #self.graphWidget2.setOpts(height=new_height)
                self.recall_force_line.setData(x, y_force)
                self.recall_pos_line.setData(x, y_pos)
            except:
                print("Could not display current data.")
        elif self.radio2.isChecked():
            try:
                y_force = self.loaded_data[:,1] 
                y_pos = self.loaded_data[:,0]
                x = list(range(len(y_force)))
                #self.graphWidget2.setOpts(height=new_height)
                self.recall_force_line.setData(x, y_force)
                self.recall_pos_line.setData(x, y_pos)
            except:
                print("Could not display loaded data.")
    
    def save_data(self):
        """Writes all the data to the specified filename"""
        filename = self.lineEdit.text()
        print("Saving data to", filename)
        if filename == "":
            print("No filename entered.")
            return
        # Write the data to the specified file
        final_path = os.path.join(self.data_path, filename)

        np.savetxt(final_path + ".csv", self.data_session, delimiter=",")
        #np.save(final_path, self.data_session)

    def record_buffer(self):
        """ Records the data in the buffer to a file"""
        print("Recording data...")
        self.data_session = copy.deepcopy(self.data_buffer.bufdata)
        self.update_callback_plot()
        print("Data recorded.")

    def load_data(self):
        """ Loads the data from the specified file"""
        try:
            print("Loading data...")
            self.loaded_data = np.loadtxt(self.filePath, delimiter=",")
            print("Data loaded.")
        except:
            print("Failed to load data. Check if file is in the correct format.")
    
    def queue_to_buffer(self):
        """ Pulls data from the queue and adds it to the buffer"""
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
        self.record_timer.start() 
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
