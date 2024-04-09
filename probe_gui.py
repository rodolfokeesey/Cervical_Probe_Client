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
        self.fs = 80 # Sampling frequency
        self.h = 0.002 # indentation in meters
        self.v = 0.5 # What is this?
        self.R = 0.0024052 # radius of the probe in meters

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

        # Initialize plot detection windows
        num_reps = 3 # Number of repetitions in a single trial
        t0_start = [225, 408, 588]
        t0_end = [250, 428, 608]
        tf_start = [251, 430, 612]
        tf_end = [311, 490, 672]
        self.detection_windows:list[list] = [[] for x in range(num_reps * 2)]
        self.det_current_bound:list[list] = [[t0_start[x], t0_end[x], tf_start[x], tf_end[x]] for x in range(num_reps)]
        
        # Creates detection windows for each plot
        detection_windows:list[pg.InfiniteLine] = []
        # range is hardcoded 4 because we have 2 windows, each defined with a start value and end value
        # these values are keyed to the following [m_start, m_end, h_start, h_end]
        for rep in range(num_reps):
            for i in range(4):
                # if i is 0 or 1, we are doing the M-Response, if 2 or 3, we are doing the H-response
                if i == 0 or i == 1:
                    line = pg.InfiniteLine(pos = self.det_current_bound[rep][i], pen = '#FD003A', movable=True, angle=90, name=[rep,i])
                elif i == 2 or i == 3:
                    line = pg.InfiniteLine(pos = self.det_current_bound[rep][i], pen = '#5BA4C4', movable=True, angle=90, name=[rep,i])
                else:
                    line = pg.InfiniteLine(pos = self.det_current_bound[rep][i], movable=True, angle=90, name=[rep,i])
                # if "i" is 0 or 2, then we are creating the starting bound line
                if i == 0 or i == 2:
                    line.addMarker('|>')
                elif i == 1 or i == 3:
                    line.addMarker('<|')
                else:
                    line.addMarker('|')
                line.sigPositionChangeFinished.connect(self.line_pos)
                self.recall_pos.addItem(line)
                #self.recall_force.addItem(line)
                self.detection_windows[rep].insert(i,line)


        self.init_ui()

        # Initialize the timer to record all the data in the buffer
        self.record_timer = QTimer()
        self.record_timer.setSingleShot(True)
        self.record_timer.setInterval(7000)  # Interval in milliseconds
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

        # Manually set the initial and final force values, then add the sublayout
        force_sublay = QHBoxLayout()
        self.f0_val = [0, 0, 0]
        self.ff_val = [0, 0, 0]
        self.f1_0 = QLabel(f"Rep 1 Initial Force: {self.f0_val[0]}")
        self.f1_f = QLabel(f"Rep 1 Final Force: {self.ff_val[0]}")
        self.f2_0 = QLabel(f"Rep 2 Initial Force: {self.f0_val[1]}")
        self.f2_f = QLabel(f"Rep 2 Final Force: {self.ff_val[1]}")
        self.f3_0 = QLabel(f"Rep 3 Initial Force: {self.f0_val[2]}")
        self.f3_f = QLabel(f"Rep 3 Final Force: {self.ff_val[2]}")
        force_sublay.addWidget(self.f1_0)
        force_sublay.addWidget(self.f1_f)
        force_sublay.addWidget(self.f2_0)
        force_sublay.addWidget(self.f2_f)
        force_sublay.addWidget(self.f3_0)
        force_sublay.addWidget(self.f3_f)
        col2.addLayout(force_sublay)

        # Manually set the initial calculated stiffness values,
        stiffness_sublay = QHBoxLayout()
        self.stiffness = [0, 0, 0]
        self.stiffness_ave = [0]
        self.stiffnes_dev = [0]

        self.r1s = QLabel(f"Rep 1 Stiffness: {self.stiffness[0]}")
        self.r2s = QLabel(f"Rep 2 Stiffness: {self.stiffness[1]}")
        self.r3s = QLabel(f"Rep 3 Stiffness: {self.stiffness[2]}")
        self.s_ave = QLabel(f"Average Stiffness: {self.stiffness_ave[0]}")
        self.s_dev = QLabel(f"Stiffness Deviation: {self.stiffnes_dev[0]}")
        stiffness_sublay.addWidget(self.r1s)
        stiffness_sublay.addWidget(self.r2s)
        stiffness_sublay.addWidget(self.r3s)
        stiffness_sublay.addWidget(self.s_ave)
        stiffness_sublay.addWidget(self.s_dev)
        col2.addLayout(stiffness_sublay)

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

    def line_pos(self, obj):
        """ This function is called when the detection lines are moved. It updates the self.det_current_bound attribute
        to the value of the detection line. It also sorts the detection bounds so that the lower bound line can never be
        above the upper bound line, and vis versa.
        
        """
        keyIdx = obj.name()[0]
        lineIdx = obj.name()[1]
        # obj.name[0] is the device, obj.name[1] is the sub-plot
        self.det_current_bound[keyIdx][lineIdx] = obj.value()
        # Sort the order of the bounds pairwise
        m_sort = sorted(self.det_current_bound[keyIdx][0:2])
        h_sort = sorted(self.det_current_bound[keyIdx][2:4])
        # Reassign our detection bounds to our sorted bounds
        self.det_current_bound[keyIdx][0:2] = m_sort
        self.det_current_bound[keyIdx][2:4] = h_sort
        # Reassign our plotting lines accordingly to the new sorted bounds
        m_lower = self.det_current_bound[keyIdx][0]
        m_upper = self.det_current_bound[keyIdx][1]
        h_lower = self.det_current_bound[keyIdx][2]
        h_upper = self.det_current_bound[keyIdx][3]
        self.detection_windows[keyIdx][0].setValue(m_lower)  # The line object itself
        self.detection_windows[keyIdx][1].setValue(m_upper) # The line object itself
        self.detection_windows[keyIdx][2].setValue(h_lower)  # The line object itself
        self.detection_windows[keyIdx][3].setValue(h_upper) # The line object itself

    def calculate_force(self,input_force):
        """ Calculates/updates the force values from the detection windows"""
        # Unpack the detection windows
        r1_f0_start = self.det_current_bound[0][0]
        r1_f0_end = self.det_current_bound[0][1]
        r1_ff_start = self.det_current_bound[0][2]
        r1_ff_end = self.det_current_bound[0][3]
        r2_f0_start = self.det_current_bound[1][0]
        r2_f0_end = self.det_current_bound[1][1]
        r2_ff_start = self.det_current_bound[1][2]
        r2_ff_end = self.det_current_bound[1][3]
        r3_f0_start = self.det_current_bound[2][0]
        r3_f0_end = self.det_current_bound[2][1]
        r3_ff_start = self.det_current_bound[2][2]
        r3_ff_end = self.det_current_bound[2][3]
        # Get the force values from the detection windows
        force = input_force[:]
        ff = np.zeros((3))
        fi = np.zeros((3))
        ff[0], ff[1], ff[2] = np.max(force[r1_ff_start:r1_ff_end]), np.max(force[r2_ff_start:r2_ff_end]), np.max(force[r3_ff_start:r3_ff_end])
        fi[0], fi[1], fi[2] = np.max(force[r1_f0_start:r1_f0_end]), np.max(force[r2_f0_start:r2_f0_end]), np.max(force[r3_f0_start:r3_f0_end])
        # Update the force labels
        self.f0_val = fi
        self.ff_val = ff
        self.f1_0.setText(f"Rep 1 Initial Force: {round(self.f0_val[0],3)}")
        self.f1_f.setText(f"Rep 1 Final Force: {round(self.ff_val[0],3)}")
        self.f2_0.setText(f"Rep 2 Initial Force: {round(self.f0_val[1],3)}")
        self.f2_f.setText(f"Rep 2 Final Force: {round(self.ff_val[1],3)}")
        self.f3_0.setText(f"Rep 3 Initial Force: {round(self.f0_val[2],3)}")
        self.f3_f.setText(f"Rep 3 Final Force: {round(self.ff_val[2],3)}")

    def calculate_stiffness(self):
        """ Takes the initial and force values and calculates the stiffness"""
        P1 = self.ff_val[0] - self.f0_val[0] # force in newtons
        P2 = self.ff_val[1] - self.f0_val[1] # force in newtons
        P3 = self.ff_val[2] - self.f0_val[2] # force in newtons

        self.stiffness[0] = (0.75 * P1 * (1 - self.v**2)) / (self.R**0.5 * self.h**(3/2))
        self.stiffness[1] = (0.75 * P2 * (1 - self.v**2)) / (self.R**0.5 * self.h**(3/2))
        self.stiffness[2] = (0.75 * P3 * (1 - self.v**2)) / (self.R**0.5 * self.h**(3/2))
        self.stiffness_ave = np.mean(self.stiffness)
        self.stiffness_dev = np.std(self.stiffness)
        # Update the stiffness labels
        self.r1s.setText(f"Rep 1 Stiffness: {round(self.stiffness[0],3)}")
        self.r2s.setText(f"Rep 2 Stiffness: {round(self.stiffness[1],3)}")
        self.r3s.setText(f"Rep 3 Stiffness: {round(self.stiffness[2],3)}")
        self.s_ave.setText(f"Average Stiffness: {round(self.stiffness_ave,3)}")
        self.s_dev.setText(f"Stiffness Deviation: {round(self.stiffness_dev,3)}")

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
                self.calculate_force(y_force)
                self.calculate_stiffness()
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
                self.calculate_force(y_force)
                self.calculate_stiffness()
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
            time.sleep(1)
            self.probe.send_command("retract")
            print("Trial Two...")
            time.sleep(1)
            self.probe.send_command("extend")
            time.sleep(1)
            self.probe.send_command("retract")
            print("Trial Three...")
            time.sleep(1)
            self.probe.send_command("extend")
            time.sleep(1)
            self.probe.send_command("retract")
        except:
            print("Failed to send command")


if __name__ == '__main__':
    app = QApplication(sys.argv)
    main = MainWindow()
    main.show()

    app.aboutToQuit.connect(main.cleanup)
    sys.exit(app.exec_())
