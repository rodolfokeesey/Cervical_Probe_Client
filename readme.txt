This is the codebase for the CervOs probe GUI.

The entrypoint to the GUI is the probe_gui.py script, however, it this code will not run without a valid connection to the probe.

The probe_client script manages the conncetion to the cervical probe. It handles connections, data streaming, and communication.

The probe_buffer script contains the data buffer class necessary for data vidualization and recording.

The probe_gui_helpers class contains a helper class for data entry.

The remaining scripts are used for testing and debugging purposes.

