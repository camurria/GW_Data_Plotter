import os  
import math
import sys
import json
import traceback
import re
import requests

import numpy as np
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas #for plotting
from matplotlib.backends.backend_qtagg import NavigationToolbar2QT as NavigationToolbar
from matplotlib.figure import Figure

from gwosc.datasets import find_datasets, event_detectors
from gwosc.datasets import event_gps
from gwpy.time import from_gps
from gwpy.timeseries import TimeSeries
from gwosc.api import fetch_event_json, fetch_json


from layout import Ui_MainWindow


import app_resources #PI: use a resources file (.qrc) to include images and fonts

from PyQt6 import QtGui
from PyQt6 import QtWidgets, QtCore, uic
from PyQt6.QtWidgets import QMessageBox, QFileDialog
from PyQt6.QtCore import QObject, pyqtSignal, QRunnable, pyqtSlot, QThreadPool, Qt
from PyQt6.QtCore import QSize
from PyQt6.QtGui import QTextCursor, QFontDatabase, QFont

#from matplotlib import pyplot as plt #WARNING in MacOs this import creates problems NOT USE!

basedir = os.path.dirname(__file__) 


#environment variable to set auto screen scale factor
os.environ["QT_AUTO_SCREEN_SCALE_FACTOR"] = "1"


# Handle high resolution displays:
if hasattr(Qt, 'AA_EnableHighDpiScaling'):
    QtWidgets.QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
if hasattr(Qt, 'AA_UseHighDpiPixmaps'):
    QtWidgets.QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)


#The following method is used to get the start and stop of each segment in an array
#see https://stackoverflow.com/questions/76146799/group-consecutive-true-in-1-d-numpy-array

def my_consecutive_bools(ar):
    indices, = np.concatenate([ar[:1], ar[:-1] != ar[1:], ar[-1:]]).nonzero()
    arange = np.arange(ar.size)
    return np.logical_and(arange >= indices[::2, None],
                          arange < indices[1::2, None])


#----------------------------------------------------
#the following 3 classes are needed for the multithread


class WorkerSignals(QObject):
    '''
    Defines the signals available from a running worker thread.

    Supported signals are:

    finished
        No data

    error
        tuple (exctype, value, traceback.format_exc() )

    result
        object data returned from processing, anything

    progress
        int indicating % progress

    '''
    finished = pyqtSignal()
    error = pyqtSignal(tuple)
    result = pyqtSignal(object)
    progress = pyqtSignal(int)



class Worker(QRunnable):
    '''
    Worker thread

    Inherits from QRunnable to handler worker thread setup, signals and wrap-up.

    :param callback: The function callback to run on this worker thread. Supplied args and
                     kwargs will be passed through to the runner.
    :type callback: function
    :param args: Arguments to pass to the callback function
    :param kwargs: Keywords to pass to the callback function

    '''

    def __init__(self, fn, *args, **kwargs):
        super(Worker, self).__init__()

        # Store constructor arguments (re-used for processing)
        self.fn = fn
        self.args = args
        self.kwargs = kwargs
        self.signals = WorkerSignals()

        # Add the callback to our kwargs
        self.kwargs['progress_callback'] = self.signals.progress

    @pyqtSlot()
    def run(self):
        '''
        Initialise the runner function with passed args, kwargs.
        '''

        # Retrieve args/kwargs here; and fire processing using them
        try:
            result = self.fn(*self.args, **self.kwargs)
        except:
            traceback.print_exc()
            exctype, value = sys.exc_info()[:2]
            self.signals.error.emit((exctype, value, traceback.format_exc()))
        else:
            self.signals.result.emit(result)  # Return the result of the processing
        finally:
            self.signals.finished.emit()  # Done



#----------------------------------------------------
class MainWindow(QtWidgets.QMainWindow, Ui_MainWindow):
    def __init__(self, *args, obj=None, **kwargs):
        super(MainWindow, self).__init__(*args, **kwargs)
        

        #----------------------------------------------------
        # PI: Temporarily comment out this part to test the resources file
        #
        # PI : trial to use the "Montserrat" font across different systems       
        #
        # QFontDatabase.addApplicationFont() loads the font from the file specified and makes it available to the application.
        #  
        # This line uses the full path of the font file  
        # font_id = QFontDatabase.addApplicationFont(os.path.join(basedir,"fonts/Montserrat/Montserrat_Regular.ttf"))
        #
        #
        # UPDATE: these lines work correctly with the structure of the resources file
        font_id_1 = QFontDatabase.addApplicationFont(":/fonts/Montserrat_Regular.ttf")
        font_id_2 = QFontDatabase.addApplicationFont(":/fonts/Montserrat_Bold.ttf")
        #
        # Check if fonts loaded properly
        if font_id_1==-1 or font_id_2== -1:
            print("Failed to load fonts")
        elif font_id_1==0 and font_id_2 == 0:
            print("Loaded fonts")
        #   
        # These lines are not needed because 'setFont()' lines are already present in the "tabs.py" file
        #          
        #     font_family = QFontDatabase.applicationFontFamilies(font_id)[0]
        #     custom_font = QFont(font_family)
        #     self.setFont(custom_font)
        #----------------------------------------------------

        #----------------------------------------------------
        # PI: comment out this part to test resources file
        # UPDATE: this works. The logo is included in the resources file and displays correctly in the app. The following line is not needed.
        #
        #this is a trick to add the logo
        # self.label_7.setPixmap(QtGui.QPixmap(os.path.join(basedir, "img", "logo_AHEAD2020_piccolo.png")))
        #----------------------------------------------------

        self.setupUi(self)

        # Dictionaries to track open windows
        self.open_help_windows = {} #help windows
        # self.plot_windows = {}  # plotting windows


        # PI: state variable to track user actions in Tab 3
        # It is used to distinguish whether the user clicked on "Plot histogram" or "2D scatter plot"
        self.user_action_tab3 = None  
    

        #addition of other options for glitches
        self.comboBox_3.addItem("Koi Fish")
        self.comboBox_3.addItem("Low Frequency Burst")
        self.comboBox_3.addItem("Power Line")
        self.comboBox_3.addItem("Repeating Blip")
        self.comboBox_3.addItem("Scattered Light")
        self.comboBox_3.addItem("Scratchy")
        self.comboBox_3.addItem("Tomte")
        
        #adding GEO to the list of detectors
        self.comboBox.addItem("GEO")

        
        self.GPS_end = 0 
        self.GPS_start = 0
        self.GPS_ref = 0
        #self.event = None
        self.catalogs = None
        self.download_event = False
        self.decimals = 10 #this is to set the decimal digits of the sliders - 10 is for 1 digit, 100 is for 2 digits
        self.data = None # PI: Initialize to None to avoid error when clicking "Save data" without downloading data first
        self.glitch = None # PI: Initialize to None to avoid error when clicking "Plot Qscan" without downloading data first


#        self.pushButton_3.clicked.connect(self.switch1) #this will change tab to the plotting tab
#        self.pushButton_8.clicked.connect(self.switch0) #this will change tab to the data tab
        #self.pushButton_3.setToolTip('prova')
        self.pushButton_7.clicked.connect(self.save_data)
        self.pushButton_6.clicked.connect(self.load_data)
        self.pushButton.clicked.connect(self.download_data) 
        self.pushButton_2.clicked.connect(self.plot_strain)
        self.pushButton_4.clicked.connect(self.plot_Qscan)

        # PI: Hide the progress bar by default
        self.download_progressBar.setVisible(False)

        # PI: Connect the help button of each different tab to the show_help method
        self.helpButton1.clicked.connect(self.show_help)
        self.helpButton2.clicked.connect(self.show_help)
        self.helpButton3.clicked.connect(self.show_help)

        self.pushButton_9.clicked.connect(self.print_event_params)
        self.pushButton_10.clicked.connect(self.plot_parameter_histogram)
        self.pushButton_11.clicked.connect(self.plot_parameter_scatter)


        # PI: We want to remove this button and implement its functionality in the "Plot histogram" and "2D scatter plot" buttons
        # self.pushButton_12.clicked.connect(self.get_catalogs)
        

        self.pushButton_13.clicked.connect(self.display_skymap)        
                
        self.horizontalSlider.valueChanged.connect(self.set_label_min_t) #this is to decide what happens when the value of the slider changes
        self.horizontalSlider_2.valueChanged.connect(self.set_label_max_t) #this is to decide what happens when the value of the slider changes
        self.threadpool = QThreadPool()

        #Dictionary to associate the event parameters name from the database to what is shown in the plots
        self.event_parameters = {
            "Mass 1" : {
                "db_name" : "mass_1_source",
                "unit" : "M$_\odot$",
                
            },
            "Mass 2" : {
                "db_name" : "mass_2_source",
                "unit" : "M$_\odot$",
            },            
            "Chirp Mass" : {
                "db_name" : "chirp_mass_source",
                "unit" : "M$_\odot$",
            },
            "Remnant Mass" : {
                "db_name" : "final_mass_source",
                "unit" : "M$_\odot$",
            },
            "Luminosity Distance" : {
                "db_name" : "luminosity_distance",
                "unit" : "Mpc",
            },
            "Signal-to-noise ratio" : {
                "db_name" : "network_matched_filter_snr",
                "unit" : "",
            },
            "Merger Time" : {
                "db_name" : "GPS",
                "unit" : "s",
            }
        } 
        
                
                
        #Add these parameters to the comboBox
        for key in self.event_parameters:
            self.comboBox_5.addItem(key)
            self.comboBox_6.addItem(key)
        
        #I create a dictionary to hold useful parameters to plot the events strain and Qscan
        self.events_dict = {
            "GW150914": {
                "text": "This event is the first direct detection of Gravitational Waves from a Binary Black Hole merger!\n",
                "fmin": 30,
                "fmax": 400,
                "tmin":-0.4,
                "tmax": 0.3,
                "Qmin":4,
                "Qmax":20,
                "Emax":50
            },
            "GW170814": {
                "text": "This event is the first Binary Black Hole merger detected by LIGO and Virgo together!\n (LIGO-Livingston is the detector for which the signal is more visible)",
                "fmin": 20,
                "fmax": 500,
                "tmin":-0.4,
                "tmax": 0.3,
                "Qmin":4,
                "Qmax":30,
                "Emax":25
            },
            "GW170817": {
                "text": "This event is the first direct detection of Gravitational Waves from a Binary Neutron Star merger!\n Note that there is a strong blip glitch at the time of the event in LIGO-Livingston data\n",                
                "fmin": 100,
                "fmax": 700,
                "tmin":-2,
                "tmax": 0.3,
                "Qmin":50,
                "Qmax":100,
                "Emax":22
            },            
            "GW190412": {
                "text": "This event is a Binary-Black-Hole Coalescence with Asymmetric Masses!\n (3-detectors event, more visible in LIGO-Livingston)\n",
                "fmin": 30,
                "fmax": 500,
                "tmin":-0.5,
                "tmax": 0.2,
                "Qmin":4,
                "Qmax":20,
                "Emax":25
            },
            "GW190521": {
                "text": "The remnant of this Binary-Black-Hole Coalescence is an Intermediate Mass Black Hole (mass higher than 100 solar masses)\n",
                "fmin": 30,
                "fmax": 250,
                "tmin":-0.1,
                "tmax": 0.2,
                "Qmin":4,
                "Qmax":20,
                "Emax":25
            },
            "GW190814": {
                "text": "This event is a possible merger of a Neutron Star with a Black Hole!\n",                
                "fmin": 30,
                "fmax": 300,
                "tmin":-3,
                "tmax": 0.3,
                "Qmin":4,
                "Qmax":50,
                "Emax":25
            },            
            "GW190521_074359": {
                "text": "This event is the Binary Black Hole merger with the highest signal-to-noise ratio in the O3a observing run\n",                
                "fmin": 20,
                "fmax": 500,
                "tmin":-0.4,
                "tmax": 0.3,
                "Qmin":4,
                "Qmax":20,
                "Emax":30
            },
            "GW200129_065458": {
                "text": "This event is the Binary Black Hole merger with the highest signal-to-noise ratio in the O3b observing run\n",                
                "fmin": 20,
                "fmax": 500,
                "tmin":-0.4,
                "tmax": 0.3,
                "Qmin":4,
                "Qmax":20,
                "Emax":30
            },

        }


        #Add the selected events in the comboBoxes
        for key in self.events_dict:
            self.comboBox_2.addItem(key)
            self.comboBox_4.addItem(key)

        
                
        #I create a dictionary to hold useful parameters to plot the glitches strain and Qscan
        self.glitches_dict = {
          "Blip" : {
            "GPS_central" : 1257525120.55322,
            "Delta_t" : 16,
            "fmin": 20,
            "fmax": 1000,
            "tmin":-0.3,
            "tmax": 0.3,
            "Qmin":4,
            "Qmax":10,
            "Emax":150            
          },
          "Koi Fish" : {
            "GPS_central" : 1131409011.24805,
            "Delta_t" : 20,
            "fmin": 10,
            "fmax": 1000,
            "tmin":-2,
            "tmax": 2,
            "Qmin":4,
            "Qmax":10,
            "Emax":150
          },          
          "Low Frequency Burst":{ 
              "GPS_central" : 1133692227.3125,
              "Delta_t" : 16,
              "fmin": 10,
              "fmax": 1000,
              "tmin":-2,
              "tmax": 2,
              "Qmin":4,
              "Qmax":10,
              "Emax":100
          },
          "Power Line":{
              "GPS_central" : 1130913180.98438,
              "Delta_t" : 16,
              "fmin": 10,
              "fmax": 1000,
              "tmin":-0.5,
              "tmax": 0.5,
              "Qmin":40,
              "Qmax":60,
              "Emax":70
          },
          "Repeating Blip":{
              "GPS_central" : 1133002869.03076,
              "Delta_t" : 16,
              "fmin": 10,
              "fmax": 1000,
              "tmin":-0.4,
              "tmax": 0.8,
              "Qmin":4,
              "Qmax":10,
              "Emax":60
          },
          "Scattered Light" : {
            "GPS_central" : 1136122822.625,
            "Delta_t" : 20,
            "fmin": 10,
            "fmax": 500,
            "tmin":-15,
            "tmax": 15,
            "Qmin":40,
            "Qmax":50,
            "Emax":500
          },
          "Scratchy" : {
            "GPS_central" : 1132412183.21875,
            "Delta_t" : 16,
            "fmin": 10,
            "fmax": 1000,
            "tmin":-2,
            "tmax": 2,
            "Qmin":40,
            "Qmax":50,
            "Emax":50
          },
          "Tomte" : {
            "GPS_central" : 1133222819.94922,
            "Delta_t" : 16,
            "fmin": 10,
            "fmax": 1000,
            "tmin":-0.3,
            "tmax": 0.3,
            "Qmin":4,
            "Qmax":10,
            "Emax":80
          }
        }


############################
# PI: Show help for the current tab in a new window

    def show_help(self):
        
        # Get the current tab
        current_tab = self.get_current_tab()

        # Check if a help window for the current tab is already open
        if current_tab in self.open_help_windows and self.open_help_windows[current_tab].isVisible():
            # Bring the existing help window to the front
            self.open_help_windows[current_tab].raise_()
            self.open_help_windows[current_tab].activateWindow()
            return    

        # Get the help contents for each tab
        help_text = self.help_content()

        # Create and show the help window
        self.helpwindow=HelpWindow(help_text, self)
        self.helpwindow.show()

        # Store the help window in the dictionary
        self.open_help_windows[current_tab] = self.helpwindow
        # print("status of help dictionary", self.open_help_windows)


############################
# PI:  Help window contents
# This method sets different help content for each tab
# The help contents could be also saved in a separate file and read from there

    def help_content(self):
        # Determine which tab is active and get the corresponding help text
        current_tab = self.get_current_tab()  # get the current tab
        
        # print("current tab is:", current_tab)

        if current_tab == "Tab 1":
            return """
        <div style="font-size: 16px;">

            <h1>GW Data Plotter</h1>
            <p>GW Data Plotter is an application to simplify access to Gravitational Wave (GW) data and facilitate basic visualization and analysis.</p>

            <h2>Get Data</h2>
            <p>The "Get Data" tab allows users to download publicly available GW data.</p>

            <ul>
                <li style="margin-bottom: 10px;">Users can download data in one of the following ways:
                    <ul style="list-style-type: disc; margin-left: 20px;">
                        <li style="margin-bottom: 5px;">by choosing a specific time interval (in GPS time)</li>
                        <li style="margin-bottom: 5px;">by selecting a known GW event</li>
                        <li style="margin-bottom: 5px;">by selecting a known glitch</li>
                    </ul>
                </li>
                <li style="margin-bottom: 10px;">To convert UTC time to GPS format visit the link: <span style="color: blue; text-decoration: underline;">https://gwosc.org/gps/</span></li>
                <li style="margin-bottom: 10px;">We suggest downloading at least 2 seconds of data in order to whiten them (whitening is a process to remove noise).</li>
                <li style="margin-bottom: 10px;">Under the "Select a known GW event" section, users can select to download a few showcase GW events or type the name of a specific event.</li>
                <li style="margin-bottom: 10px;">Check this page <span style="color: blue; text-decoration: underline;">https://gwosc.org/eventapi/</span> to get the GPS times and names of all known detections.</li>
                <li style="margin-bottom: 10px;">The "Download data" button downloads and saves the data in a local variable and no file will be saved on the user's PC yet.</li>
                <li style="margin-bottom: 10px;">There is support to save the data in different formats (.hdf5, .gwf, and .txt) or load previously downloaded files.
                    <ul style="list-style-type: disc; margin-left: 20px;">
                        <li style="margin-bottom: 5px;">(Known issue: the executable files currently do not support saving and loading of '.gwf' files)</li>
                    </ul>
                </li>
                <li style="margin-bottom: 10px;">Useful messages and tips are displayed in the log window.</li>
            </ul>
        </div>
        """
        elif current_tab == "Tab 2":
            return"""
        <div style="font-size: 16px;">    
            <h2>Plot Data</h2>
            <p>The "Plot Data" tab allows users to visualize the GW data.</p>

            <ul>
                <li style="margin-bottom: 10px;">The "Plot strain" button allows to plot the gravitational wave data (called strain) as a function of time.</li>
                <li style="margin-bottom: 10px;">A band pass filter will be applied unless the "No freq selection" is clicked (band passing is filtering within a specific frequency range).</li>
                <li style="margin-bottom: 10px;">To zoom in time users can select a time window starting from the t_center of the available segment.</li>
                <li style="margin-bottom: 10px;">The "Plot Qscan" button allows to plot the time-frequency evolution of the gravitational wave data.</li>
                <li style="margin-bottom: 10px;">In the "Q scan section" the frequency range, time interval and data whitening option will be inherited from the previous section. After changing the parameters, click the button "Plot Qscan" again to update the plot.</li>
            </ul>
        </div>
        """
        elif current_tab == "Tab 3":
            return"""
        <div style="font-size: 16px;">    
            <h2>Explore GW Event Parameters</h2>
            <p>The "Explore GW event parameters" tab allows users to get parameters of known GW events.</p>

            <ul style="font-size: 16px;">
                <li style="margin-bottom: 10px;">Users can select an event from a list of showcase events or type the name of an event and get its main parameters.</li>
                <li style="margin-bottom: 10px;">It is also possible to download the skymap for the selected events (skymap is the event's localization on the sky).</li>
                <li style="margin-bottom: 10px;">Users can also download the parameters for all confident events and plot histograms for different parameters.</li>
                <li style="margin-bottom: 10px;">Another option is to create scatter plots of selected parameters.</li>
                <li style="margin-bottom: 10px;">If users have previously downloaded the parameters of a specific GW event, they have the option to highlight it in the histogram and scatter plots.</li>
            </ul>
        </div>
        """
        else:
            help_text = """
            <h1>Help</h1>
            <p>This is a simple help content for the application.</p>
            <ul>
                <li><b>Feature 1:</b> Description of feature 1.</li>
                <li><b>Feature 2:</b> Description of feature 2.</li>
                <li><b>Feature 3:</b> Description of feature 3.</li>
            </ul>
            """ 


############################
# PI:  Get current tab index
# This method is then used to show the help content for the current tab

    def get_current_tab(self):
            # Get the current tab index from the tabwidget and map it to a name
            current_index = self.tabWidget.currentIndex()

            if current_index == 0:
                # print("current tab is:", current_index)    
                return "Tab 1"
            elif current_index == 1:
                # print("current tab is:", current_index)    
                return "Tab 2"
            elif current_index == 2:
                # print("current tab is:", current_index)    
                return "Tab 3"
            

############################
#PI: Draw the plot window 

    def create_plot_window(self, fig, *args):   
        plot_window = AnotherWindow(fig, self)
        plot_window.show()
        return plot_window
    

############################
# PI: Method to update plot window content or create it if it does not exist

    def update_plot_window(self, fig, window_id):
        if hasattr(self, window_id) and getattr(self, window_id) is not None and getattr(self, window_id).isVisible():
            # Update the existing window
            getattr(self, window_id).update_plot(fig)
        else:
            # Create a new window if it doesn't exist
            setattr(self, window_id, self.create_plot_window(fig))


############################

    def set_label_min_t(self):
        #since the slider can accept only integers steps I will use a factor 100 to have decimal values
        new_value = str(self.horizontalSlider.value()/self.decimals)
        self.label_24.setText(new_value)


############################

    def set_label_max_t(self):
        #since the slider can accept only integers steps I will use a factor 100 to have decimal values
        new_value = str(self.horizontalSlider_2.value()/self.decimals)
        self.label_29.setText(new_value)
        

############################

    def download_data(self):
        #the inputs need to be read inside the method so that every time the button is pushed their value is updated
        
        # finding the content of current item in combo box (detector)
        self.det_label = self.comboBox.currentText()
        #get the detector names from the detector labels
        if (self.det_label=="LIGO-Hanford"):
            self.det = "H1"
        elif(self.det_label=="LIGO-Livingston"):
            self.det = "L1"
        elif(self.det_label=="Virgo"):
            self.det = "V1"
        elif(self.det_label=="KAGRA"):
            self.det = "K1"
        elif(self.det_label=="GEO"):
            self.det = "G1"            
            
#        self.event_long = self.comboBox_2.currentText()
        #the event name is the first part of the event string
#        self.event = self.event_long.split(" ")[0] #previously a comment was added after the event name
        
        self.glitch = self.comboBox_3.currentText()

        self.GPS_start = 0  
        self.GPS_end = 0
        self.download_event = False
        self.GPS_ref = 0 #this is used to store the central value of the glitch and the merger time for an event
        self.event = 0
        
        if(self.comboBox_2.currentText()!='None' or self.EventNameTab3_2.text()!=''):
            self.event = self.verify_correct_event_name(self.comboBox_2.currentText(), self.EventNameTab3_2.text())
            #if this fails, the program show not try to download the data
            if (not self.event):
                return
            try:    
                self.GPS_ref = event_gps(self.event)    
                self.GPS_start =  self.GPS_ref + self.doubleSpinBox.value()
                self.GPS_end =  self.GPS_ref + self.doubleSpinBox_2.value()
                if self.doubleSpinBox.value()>=0:
                    text = f"The starting time is calculated as the (merger time) + (time before the merger) so this number is expected to be negative. Do you want to download anyway?"
                    details = f"The most visible part of the event is the inspiral which happens before the merger time so we suggest to download data before the merger."
                    response = self.showdialogWarning(text, details, True)
                    if response == QMessageBox.StandardButton.No:
                        #in this case the data should not been downloaded
                        self.write_log("- The download was interrupted\n")
                        return
            except:
                text = f"Please, verify that you have written correctly the event name"
                details = f"You can check the list of available events in the website gwosc.org."
                self.showdialogWarning(text, details)
                return
            
        
        if (self.det_label == 'None' and self.glitch=='None'):
            text = f"Please select a detector"
            details = f"Use the drop down menu in the section 'Select a Detector' to select a detector for which you want to download the data. If you select an example of known glitch it is not necessary to select a detector."
            self.showdialogWarning(text, details)
            #self.write_log(f"Please select a detector\n")
            
        elif ((self.event and self.glitch!='None') or 
        (self.event and self.GPSstart.text()!= '') or (self.event and self.GPSend.text()!= '') or
        (self.glitch!='None' and self.GPSstart.text()!= '') or (self.glitch!='None' and self.GPSend.text()!= '')
        ):
#            self.write_log(f"Please, choose only one type of download: GPS interval, GW event or glitch\n")
            text = f"Please, choose only one type of download: GPS interval, GW event or glitch"
            details = f"Set the drop down menu of glitches and events to None if you don't want to download one of them or if you want to select by hand a time interval."
            self.showdialogWarning(text, details)

        else:
            
            if (not self.event and self.glitch=='None'):
                #check GPS start
                self.GPS_start, error_start = self.check_GPS('start')
        
                #check GPS stop
                self.GPS_end, error_end = self.check_GPS('stop')
                
                if (not self.GPS_start or not self.GPS_start):
                    text = error_start + '\n' + error_end
                    details = f"Write the correct GPS times in the 'Select data by time interval' section, or select a known GW event or a known glitch."
                    self.showdialogWarning(text, details)
                    return
                

            if (self.event):
                self.download_event = True
                #use the default options for GW150914 in general
                edict = self.events_dict['GW150914']
                list_d = str(event_detectors(self.event))
                list_d = list_d.replace("H1", "LIGO-Hanford")
                list_d = list_d.replace("L1", "LIGO-Livingston")
                list_d = list_d.replace("V1", "Virgo")
                list_d = list_d.replace("K1", "KAGRA")
                list_d = list_d.replace("G1", "GEO")
                self.write_log(f"Data for this event are available for the following detectors: {list_d}")
                if (self.event in self.events_dict):
                    #if the event is part of the dictionary the setting options saved in the dictionary will be used
                    edict = self.events_dict[self.event] #renaming the dictionary with a shorter name
                    self.write_log(f"{edict['text']}")
                    
                    
                    
                self.write_log(f"Downloading data for the {self.event} event in {self.det_label} between {self.GPS_start} and {self.GPS_end}\n")
                
                #setting default values according to the selected event
                #fmin
                self.spinBox_3.setProperty("value", edict["fmin"])
                #fmax
                self.spinBox_4.setProperty("value", edict["fmax"])
                #Qmin
                self.spinBox.setProperty("value", edict["Qmin"])
                #Qmax
                self.spinBox_2.setProperty("value", edict["Qmax"])
                #Emax
                self.spinBox_5.setProperty("value", edict["Emax"])
                
                
                            
            if (self.glitch in self.glitches_dict):
                #currently all glitches examples are from the same detector
                if (self.det_label != 'None'):
                    text = f"Your detector choice will be ignored in this case"
                    details = f"Glitches can happen in different times for each detector. The examples provided here are chosen for a specific detector so the detector choice is disabled."
                    self.showdialogWarning(text, details)
                self.det = 'H1'
                self.det_label ="LIGO-Hanford"
                gdict = self.glitches_dict[self.glitch]
                self.GPS_ref = gdict["GPS_central"]
                self.GPS_start = self.GPS_ref - gdict["Delta_t"]
                self.GPS_end = self.GPS_ref + gdict["Delta_t"]
                self.write_log(f"Downloading data for a glitch of type {self.glitch} in {self.det_label}\n between {self.GPS_start} and {self.GPS_end}\n")
#                self.write_log(f"(Set the glitch field to None if you want to use other options to download the data)\n")
                
                #setting default values according to the glitch type
                #fmin
                self.spinBox_3.setProperty("value", gdict["fmin"])
                #fmax
                self.spinBox_4.setProperty("value", gdict["fmax"])
                #Qmin
                self.spinBox.setProperty("value", gdict["Qmin"])
                #Qmax
                self.spinBox_2.setProperty("value", gdict["Qmax"])
                #Emax
                self.spinBox_5.setProperty("value", gdict["Emax"])

                
                
                                
            
            if (self.GPS_start != 0 and self.GPS_end !=0 and self.GPS_end<=self.GPS_start):
                self.write_log(f"GPS stop has to be > GPS start\n")
        
                
            if(self.GPS_start != 0 and self.GPS_end !=0 and self.GPS_end>self.GPS_start):
                
                #now that I know the GPS start and stop I can set the max and min for the zoom window
                self.duration = self.GPS_end - self.GPS_start

                if (self.duration<2):
                    text = f"The duration of the data requested is less that 2 seconds. In this case the whitening procedure in the next tab will not be available. Do you want to download the data anyway?"
                    details = f"The whitening procedure allows data to be re-weighted according to noise at each frequency, but to be done at least 2 seconds of data are required."
                    response = self.showdialogWarning(text, details, True)
                    if response == QMessageBox.StandardButton.No:
                        #in this case the data should not been downloaded
                        self.write_log("- The download was interrupted\n")
                        return

                
                #I also adjust the min max and the steps of the sliders
                self.modify_zoom_sliders()

                #and I can also set the default value 
                
                #this is for events
                if (self.event):
                    #set the min and max only if the data cover the expected range
                    if ((self.GPS_start - self.GPS_ref)<edict["tmin"] and (self.GPS_end - self.GPS_ref) > edict["tmax"]):
                        #tmin
                        self.horizontalSlider.setProperty("value", self.decimals*edict["tmin"])
                        #tmax
                        self.horizontalSlider_2.setProperty("value", self.decimals*edict["tmax"])
                
                
                #this is for glitches
                if (self.glitch in self.glitches_dict):
                    #tmin
                    self.horizontalSlider.setProperty("value", self.decimals*gdict["tmin"])
                    #tmax
                    self.horizontalSlider_2.setProperty("value", self.decimals*gdict["tmax"])

                        
                self.write_log("- Wait, the download is ongoing...\n")

                #PI: Show the progress bar
                self.download_progressBar.setVisible(True)
            
                worker = Worker(self.fetch_open_data) # Any other args, kwargs are passed to the run function
                worker.signals.result.connect(self.print_output)
                worker.signals.finished.connect(self.thread_complete)
                worker.signals.progress.connect(self.progress_fn)    

                # Execute
                self.threadpool.start(worker)

            else:
                #self.write_log("- Please, give correct GPS times to download the data\n")
                text = f"Please, give correct GPS times to download the data"
                details = f"This error may occur if you have not selected a correct GPS interval. You can also choose to download data around a known GW event or a glitch"
                self.showdialogWarning(text, details)
                

############################
#Agata: define method to change both the sliders max and min for the zoom but also the steps

    def modify_zoom_sliders(self):
        #if duration is too long change the step of the slider
        if self.duration>10:
            #get the order of magnitude of the duration
            om = math.floor(math.log(self.duration, 10))
            #set the steps in the horizontal bar depending on the previous result
            self.horizontalSlider.setPageStep(10**om)
            self.horizontalSlider_2.setPageStep(10**om)
        self.horizontalSlider.setMinimum(round(-(self.duration)*(self.decimals/2)))
        self.horizontalSlider_2.setMaximum(round(self.duration*(self.decimals/2)))


############################
# PI: method to save the downloaded GW data to a file

    def save_data(self):

    # If the data has not been downloaded yet, return without saving and display a warning message to the user in the logger
        if self.data is None:
            self.write_log("Please download data before saving it, or load data from a previously downloaded file.")
            return
        
        print(self.data)
        
        """
        Create a save file dialog with `QFileDialog.getSaveFileName()`.
        - User specifies save location and a suggested filename is provided.
        - Include format extension in the filename (e.g., 'data.hdf5').
        - Supported formats: HDF5, GWF, ASCII (from `gwpy` docs).
        - Option `QFileDialog.DontConfirmOverwrite` of `QFileDialog` is not set by default. 
        -- So overwrite confirmation is prompted and no need for additional filename existence check.
        - Get user's home directory cross-platform: os.path.expanduser('~').
        """
        # Suggested filename naming convention: 'DETECTOR_GWDATAPLOTTER_SAMPLERATE-GPSstart-DURATION.hdf5'
        # User can change the file type in the save dialog.
        sample_rate_khz = self.data.sample_rate.value // 1000 # Convert the sample rate to kHz by integer division
        suggested_filename = f"{self.det}_GWDATAPLOTTER_{sample_rate_khz:.0f}KHZ-{self.GPS_start:.0f}-{self.duration:.0f}.hdf5"

        # Loop to reopen the save file dialog with the suggested filename if the user changes it
        while True:
            filename, _ = QFileDialog.getSaveFileName(
                self, 
                'Save File', 
                os.path.join(os.path.expanduser('~'), suggested_filename), 
                'HDF5 files (*.hdf5);;GWF files (*.gwf);;ASCII files (*.txt);;All Files (*)'
            )
            if not filename:  # If the user cancels the dialog, return without saving
                return

            # Check if the user changed the suggested filename.
            # Check only the basename and don't bother with the file extension.
            if os.path.basename(filename).split('.')[0] != suggested_filename.split('.')[0]:
                response = self.warning_message_box()
                if response == QMessageBox.StandardButton.No:
                    # Continue the loop to reopen the save file dialog with the suggested filename
                    continue           
            break
                
        try:
            # If we have reached this point, the user has already confirmed that they want to overwrite the file.
            if filename.endswith('.hdf5'):
                # For HDF5 files, use the 'overwrite=True' option to overwrite the file if it exists already.
                self.data.write(filename, overwrite=True)

            # For other file formats (GWF and TXT), call write() without the overwrite option, as they do not support it.    
            elif filename.endswith('.txt'):     
                self.data.write(filename)

            elif filename.endswith('.gwf'):
                # For GWF files, set the "data.name" to a channel name based on a GWOSC-inspired naming convention.
                # This is the only way to be able to read afterwards the saved GWF file, using the (now known) channel name.
                # See open PR #1552 in gwpy for more details: https://github.com/gwpy/gwpy/pull/1552
                channel_name = f"{self.det}:GWDATAPLOTTER-{sample_rate_khz:.0f}KHZ_STRAIN"
                self.data.name = channel_name
                print("self.data.name",self.data.name) 
                print("self.data",self.data) 

                # When trying to save downloaded data to GWF, Agata Trovato reported the following error:
                # XLAL Error - XLALFrameAddREAL8TimeSeriesProcData: Series start time 1126259461.399902300 is earlier than frame start time 1126259461.399902344
                # XLAL Error - XLALFrameAddREAL8TimeSeriesProcData: Invalid argument
                # This probably could be linked to: 
                # (i) how floating point numbers are handled by the GWF format  
                # (ii) possible differences in floating point implementation across different processors (e.g. x86_64 vs ARM processors).
                # Try rounding the GPS start time to set number of decimals to avoid this error.
                self.GPS_start = round(self.GPS_start, 5)
                print("Rounded GPS start time:", self.GPS_start)

                self.data.write(filename)
                # print('Here is how the data looks after the channel name hack\n', self.data)    

            self.write_log(f"Data saved to {filename}")

        except Exception as e:
            self.write_log(f"Error saving data: {str(e)}")


############################
    def check_GPS(self, label):
        '''
        This method is used to check if the GPS times given by the user are reasonable
        It will write error messages in the log if the GPS format is not correct
        It will always return a value GPS_out, which is zero if the GPS format is not correct 
        '''
        
        GPS_out = 0
        error_code = ''
        
        
        if label == 'start':
            GPS_in = self.GPSstart.text()
        if label == 'stop':
            GPS_in = self.GPSend.text()
            
        if GPS_in:
            
            try:
                self.write_log(f"GPS {label} requested: {GPS_in} (UTC: {from_gps(GPS_in)})")
                GPS_out = float(GPS_in)
                if len(str(int(GPS_out))) < 10:
                    GPS_out = 0
                    raise ValueError(f"GPS {label} has to have 10 digits")

            except ValueError as ve:
                error_code = f"Value error for GPS {label}: "+str(ve)
                #self.write_log(f"Value error for GPS {label}: "+str(ve))
        else:
            #self.write_log(f"Fill the GPS {label}")    
            error_code = f"Fill the GPS {label}"
        return GPS_out, error_code


############################
# PI: method to load GW data from a file

    def load_data(self):

        # Create a file dialog window to load the data with `QFileDialog.getOpenFileName()`.
        # The user can specify the file name and location.
        # The format extension must be included in the filename, it does not get added automatically.
        # Main supported file formats are (from `gwpy` documentation): HDF5, GWF, ASCII.
        #
        # NOTE: Cross-platform way to get the user's home directory => os.path.expanduser('~')
        #
        filename, _ = QFileDialog.getOpenFileName(self, 'Load File', os.path.expanduser('~'), 'HDF5 files (*.hdf5);;GWF files (*.gwf);;ASCII files (*.txt);;All Files (*)')
        if not filename:  # If the user cancels the dialog, return without loading
            return

        #Agata: if the user loads data from a file even if previously data for an event have been downloaded 
        #the self.download_event needs to be set to false to avoid wrong titles in the plots
        self.download_event = False
        try:
            # Load a TXT or HDF5 file that was previously saved with the app
            self.data = TimeSeries.read(filename)
            self.write_log(f"Data loaded from {filename}")
            print(self.data)


            # Extract the detector name from the filename
            #
            # To avoid errors about labels missing raised by plot_strain() and plot_Qscan() methods, we need to ensure that the 
            # detector name is set.
            #
            # In the case of loading data previously downloaded with the app:
            # - the detector name is not saved in the HDF5 file internally (at least gwpy does not save it with the write() method)
            # - we cannot be certain that the user saved the data following the naming convention of GWOSC in order to get the detector name from the filename
            # 
            # With that in mind, the following extraction assumes a filename that adopts the suggested naming convention: 
            # 'DETECTOR_GWDATAPLOTTER_SAMPLERATE-GPSstart-DURATION'
            # 
            base_name = filename.split("/")[-1]
            self.det = base_name.split("_")[0].split("_")[0]
            print(self.det)

            # Set needed options for plotting when loading data
            self.set_options_loaded_data()
            
            #check for Nans
            self.check_for_nans()
            

        # Trying to read HDF5 or TXT files downloaded from GWOSC will raise a ValueError
        except ValueError:

            # Load HDF5 files downloaded from GWOSC website
            if filename.endswith(".hdf5"):

                # Specify format='hdf5.gwosc' to read the data from the hdf5 file downloaded from GWOSC
                # Otherwise, one needs to use 'h5py' to read the GWOSC file.
                self.data = TimeSeries.read(filename, format='hdf5.gwosc')
                self.write_log(f"Data loaded from {filename}")
                print(self.data)


                # Extract the detector name from the filename
                base_name = filename.split("/")[-1]
                self.det = base_name.split("-")[1].split("_")[0]
                print(self.det)

                # Set needed options for plotting when loading data
                self.set_options_loaded_data()

                #check for Nans
                self.check_for_nans()


            # Load TXT files downloaded from GWOSC website    
            elif filename.endswith(".txt"):
        
                # Read the strain data points
                # The first 3 rows of the txt file start with '#' and are automatically skipped (treated as comments).
                strain_data_points=np.loadtxt(filename)
                print(strain_data_points)
                

                # Read separately the first lines containing useful info
                with open(filename) as f:
                    for i, line in enumerate(f):  
                        if i==0: # Contains GW event name and detector name, not needed here
                            continue
                        elif i==1: # Contains the sample rate
                            freq = int(line.split()[4])
                        elif i==2: # Contains the GPS start time and the duration of the data
                            GPSstart = int(line.split()[3])
                        else:
                            break        
               

                # Create the Timeseries object using the information read from the TXT file
                self.data = TimeSeries(strain_data_points, sample_rate=freq, epoch=GPSstart)
                self.write_log(f"Data loaded from {filename}")
                print(self.data)


                # Extract the detector name from the filename
                base_name = filename.split("/")[-1]
                self.det = base_name.split("-")[1].split("_")[0]
                print(self.det)

                # Set needed options for plotting when loading data
                self.set_options_loaded_data()  

                #check for Nans
                self.check_for_nans()


        # Trying to read GWF files will raise a TypeError 
        # This happens because an additional argument is needed in TimeSeries.read(), i.e. the channel name.
        except TypeError:

            # For GWF files the channel name can be inferred from the filename
            base_name = filename.split("/")[-1]

            # Check if the filename is from GWOSC or from the App
            if "_GWOSC_" in base_name:
                list_strings = base_name.split("-")[1].split("_")
            elif "_GWDATAPLOTTER_" in base_name:
                list_strings = base_name.split("-")[0].split("_")
            else:
                self.write_log(f"Seems like the file is not from GWOSC or the App. Support for this case is not implemented yet.")
                return
            
            # Construct the channel name from the filename
            print(list_strings)
            print(len(list_strings))
            if len(list_strings)==3:    # for filenames like 'H1_GWDATAPLOTTER_4KHZ-1242459841-32.gwf'
                # the channel name construction convention is known from the save_data() method:
                # i.e. 'DETECTOR:GWDATAPLOTTER-SAMPLERATE_STRAIN'
                channel_name = list_strings[0]+":"+list_strings[1]+"-"+list_strings[2]+"_STRAIN"    
            if len(list_strings)==4:
                channel_name = list_strings[0]+":"+list_strings[1]+"-"+list_strings[2]+"_"+list_strings[3]+"_STRAIN"
            if len(list_strings)==5:
                channel_name = list_strings[0]+":"+list_strings[1]+"-"+list_strings[3]+"_"+list_strings[4]+"_STRAIN"    
            print(channel_name)


            # Load the GWF file using the reconstructed channel name as argument    
            self.data = TimeSeries.read(filename, channel=channel_name)
            self.write_log(f"Data loaded from {filename}")
            print(self.data)


            # Set the detector name from the filename read above
            self.det = list_strings[0]
            print(self.det)

            # Set needed options for plotting when loading data
            self.set_options_loaded_data()  
            
            #check for Nans
            self.check_for_nans()

        except Exception as e:
            self.write_log(f"Error loading data: {str(e)}")

        
############################
# PI: method to set the detector label based on the detector name

    def set_detector_label(self):
        # Set the detector label based on the detector name
        if self.det == "H1":
            self.det_label = "LIGO-Hanford"
        elif self.det == "L1":
            self.det_label = "LIGO-Livingston"
        elif self.det == "V1":
            self.det_label = "Virgo"
        elif self.det == "K1":
            self.det_label = "KAGRA"


############################
# PI: method to set needed options for plotting when loading data

    def set_options_loaded_data(self):
            # Set the detector label based on the detector name
            self.set_detector_label()
            print(self.det_label)

            # Set the GPS start and end times from the loaded data (to avoid errors when trying to plot)
            self.GPS_start = self.data.t0.value
            self.GPS_end = self.data.times.value[-1]
            print("data type of GPS start is: ", type(self.GPS_start))
            print("data type of GPS end is: ", type(self.GPS_end))
            print(f"GPS start time of loaded data: {self.GPS_start}")
            print(f"GPS end time of loaded data: {self.GPS_end}")

            # Set the duration of the loaded data (again needed for plotting)
            # Set the min and max values of the sliders so that the respective values get updated when loading data
            self.duration = self.GPS_end - self.GPS_start
            print(f"Duration of loaded data: {self.duration}")
            self.modify_zoom_sliders()
            
            # The option for self.glitch is not read from the user options as done when downloading data.
            # Set self.glitch to None to avoid errors in the plot_Qscan() method
            self.glitch = None
            print(self.glitch)


############################
#AT: for the moment I implemented this method to check for Nans but other alternatives are possible

    def check_for_nans(self):
        #warn the user if the data contains NaNs, i.e. periods of time not good enough to be released
        nans = np.isnan(self.data.value)

        if (nans.any()):
            text_to_be_print = f"WARNING: this file contains NaNs which corresponds to periods not good enough to be released\n"
            text_to_be_print +="NaNs will be replaced by zeroes to allow for plotting (without whitening)\n"
            self.data.value[nans] = 0
            #remove the selection of the whitening
            self.checkBox_5.setChecked(False)
            #remove the frequency selection
            self.checkBox_7.setChecked(True)            
            #remove the zoom in time
            self.checkBox.setChecked(False)
                       
    
            #we could add specify which are the intervals of "good data" in the file
            text_to_be_print +=f"The segments of available data in the file are in the GPS intervals:\n"
            time_array = np.arange(start=self.data.t0.value, stop=self.data.t0.value + (self.data.dt.value*len(self.data.value)), step=self.data.dt.value)
            list_of_segments = my_consecutive_bools(~nans)
            for no_nans in list_of_segments:
                time_no_nans = time_array[no_nans]
                text_to_be_print +=f"[{time_no_nans[0]},{time_no_nans[-1]+self.data.dt.value})\n"
            self.write_log(text_to_be_print)    


############################

    def write_log(self, text, textB = None):
        #this method just writes into the logger 
        #by default it writes in the logger of the first tab
        if textB == None:
            textB = self.textBrowser
#        self.textBrowser.setPlainText(self.textBrowser.toPlainText()+text+"\n")
        cursor = QTextCursor(textB.document())
        cursor.setPosition(0)
        textB.setTextCursor(cursor)
        textB.insertPlainText(text+'\n')
#        self.textBrowser.insertHtml('<b>'+text+'<\b>')


############################

    def write_log_plot(self, text):
        #this method just writes into the logger of the second tab
        self.write_log(text,self.textBrowser_2)


############################

    def check_if_text_is_already_there(self, text):
        is_there = False
        previous_text = self.textBrowser_2.toPlainText()
        if text in previous_text:
            is_there = True
        return is_there    


############################

    def write_log_event(self, text):
        #this method just writes into the logger of the second tab
        self.write_log(text,self.textBrowser_3)
        
                
############################
# PI: trial to incorporate the download progress bar
    def progress_fn(self, value):
        #this needs to be improved or eliminated
        self.download_progressBar.setValue(value)
        print("%d%% done" % value)


############################

    def print_output(self, s):
        print(s)
        self.write_log(s)


############################

    def thread_complete(self):
        #this needs to be improved or eliminated
        print("THREAD COMPLETE!")
 

############################
# PI: instruct a specific code block to be executed only AFTER the data has been downloaded

    def catalogs_download_finished(self):
            
            print("Download complete!")

            # PI: depending on what the user wants to do, execute the corresponding code block
            if self.user_action_tab3 == "plot_histogram":
                self.plot_hist_after_download()
            elif self.user_action_tab3 == "2D_scatter_plot":
                self.plot_2D_scatter_after_download()


############################
# PI: This code block plots the histogram of a specified parameter for all GW events.
# It must run only AFTER the catalogs data has been downloaded.

    def plot_hist_after_download(self):

            key = self.comboBox_5.currentText()

            db_name = self.event_parameters[key]['db_name']
            param = []
            
            for c in self.catalogs:
                for e in c['events']:
                    value = c['events'][e][db_name]
                    if value: #this is to remove Nones
                        param.append(value)
                

            fig = Figure()
            ax = fig.add_subplot()        
            
            if self.checkBox_3.isChecked():
                self.write_log_event("\nFor the histogram, selecting the 'Log x scale' will actually allow you to plot the log10 of the parameter")
                ax.hist(np.log10(param), label='all events', bins=20)
                ax.set_xlabel(f"log$_{{10}}$ {key} [log$_{{10}}$ {self.event_parameters[key]['unit']}]")
            else:
                ax.hist(param, label='all events', bins=20)
                ax.set_xlabel(key+" ["+self.event_parameters[key]['unit']+"]")
            ax.set_ylabel('Counts')


            if self.checkBox_4.isChecked():
                ax.set_yscale('log')

            if self.checkBox_2.isChecked():
                try:
                    x=self.event_parameters[key]['value']
                    if self.checkBox_3.isChecked(): #replace with the log10 also in this case
                        x = np.log10(x)
                    ax.axvline(x=x, color='tab:orange', label=self.event_tab3)
                except KeyError:
                    text = f"The value of {key} will not be highlighted on the plot for the selected event"
                    details = "Use the button 'Get event parameters' to get the value of the parameters for the event and then plot the histogram again"
                    self.showdialogWarning(text, details)
                    # except AttributeError or TypeError:
                except TypeError:
                    text = f"The value of {key} will not be highlighted on the plot for the selected event"
                    details = f"The parameter {key} for {self.event_tab3} is not defined"
                    self.showdialogWarning(text, details)
                
            ax.legend()

            
            # PI: Create plot window identifier (used to update the plotting windows or avoid duplicates) 
            window_id = 'histogram_plot'

            # Update the plot_window with the new figure (or create it if it does not exist)
            self.update_plot_window(fig, window_id)


###########################
# PI: This code block plots a 2D scatter plot of the specified parameters for all GW events.
# It must run only AFTER the catalogs data has been downloaded.

    def plot_2D_scatter_after_download(self):

        key1 = self.comboBox_5.currentText()
        key2 = self.comboBox_6.currentText()

        db_name1 = self.event_parameters[key1]['db_name']
        db_name2 = self.event_parameters[key2]['db_name']
        param1 = []
        param2 = []
        
        for c in self.catalogs:
            for e in c['events']:
                param1.append(c['events'][e][db_name1])
                param2.append(c['events'][e][db_name2])
            
        fig = Figure()
        ax = fig.add_subplot()        
        
        ax.scatter(param1, param2, label='all events', alpha=0.8)                  
        ax.set_xlabel(key1+" ["+self.event_parameters[key1]['unit']+"]")
        ax.set_ylabel(key2+" ["+self.event_parameters[key2]['unit']+"]")
        if self.checkBox_3.isChecked():
            ax.set_xscale('log')
        if self.checkBox_4.isChecked():
            ax.set_yscale('log')
        if self.checkBox_2.isChecked():
            #check that the values for the parameters are numbers for the selected event 
            try:
                if (self.event_parameters[key1]['value'] and self.event_parameters[key2]['value']):
                    ax.scatter(self.event_parameters[key1]['value'], self.event_parameters[key2]['value'], edgecolors='tab:orange', facecolor="none", label=self.event_tab3)
                else:
                    text = f"The values of {key1} and {key2} will not be highlighted on the plot for the selected event"
                    details = f"One among the parameters {key1} and {key2} for {self.event_tab3} is not defined"
                    self.showdialogWarning(text, details)    
            except KeyError:
                text = f"The values of {key1} and {key2} will not be highlighted on the plot for the selected event"
                details = "Use the button 'Get event parameters' to get the value of the parameters for the event and then plot the histogram again"
                self.showdialogWarning(text, details)

        ax.legend()
    
        # PI: Create plot window identifier (used to update the plotting windows or avoid duplicates) 
        window_id = 'scatter_plot'          

        # Update the plot_window with the new figure (or create it if it does not exist)
        self.update_plot_window(fig, window_id)


############################

    def fetch_open_data(self, progress_callback):
        output = ""
        if not self.download_event:
            events = []
            events_with_repetitions = find_datasets(type='events', segment = (self.GPS_start,self.GPS_end), detector = self.det)
            #remove multiple versions of the same event
            for e in events_with_repetitions:
                if (e[:2]=="GW" and e[:-3] not in events):
                    events.append(e[:-3])
            
            #Check that there are not duplicates of the same event
            #A way to check is verifying that a v1 exists for all events
            events = [e for e in events if e+"-v1" in events_with_repetitions]
            
            if len(events):
                output+="Note that the data requested contains the following events:\n"
                for e in events:
                    output+=e+" at GPS time: "+str(event_gps(e))+"\n"
                    
        try:
            # PI: added verbose=True to show the URL from which the data is downloaded
            self.data = TimeSeries.fetch_open_data(self.det, self.GPS_start,self.GPS_end, verbose=True)
            # print(self.data)
            # url = self.data.meta['url']
            # output += f"\nData downloaded from URL: {url}\n"
        except ValueError as ve:
            error = str(ve)
            error = error.replace("H1", "LIGO-Hanford")
            error = error.replace("L1", "LIGO-Livingston")
            error = error.replace("V1", "Virgo")
            error = error.replace("K1", "KAGRA")
            error = error.replace("G1", "GEO")
            return error
        except TimeoutError as te:
            return f"Error: {te}. This could be due to a momentary connection problem or maintenance period, try later."
        except Exception as e:
            return str(e)
        
                
        progress_callback.emit(100)
        return output+"\n- Done!\n"


############################

    def switch1 (self):
        #this method allows to change tab and go to the second tab
        self.tabWidget.setCurrentIndex(1)


############################

    def switch0 (self):
        #this method allows to change tab and go to the first tab
        self.tabWidget.setCurrentIndex(0)


############################

    def check_common_plot_options(self):
        #this is to check the plotting option common to the strain and Q scan
        label_w = "raw"
        do_whiten = False
        do_freq_sel = True #note that this is clicked when no selection is done
        do_zoom = False
        fmin=self.spinBox_3.value()
        fmax=self.spinBox_4.value()
        bp_label = f", f=({fmin},{fmax}) [Hz]"
        tmin = self.horizontalSlider.value()/self.decimals
        tmax = self.horizontalSlider_2.value()/self.decimals
        if self.checkBox_5.isChecked():
            do_whiten = True
            label_w = "whitened"
        if self.checkBox_7.isChecked():    
            do_freq_sel = False
            bp_label = ""
        if self.checkBox.isChecked():    
            do_zoom = True
        return do_whiten,do_freq_sel,fmin,fmax,do_zoom,tmin,tmax, label_w, bp_label


############################

    def tips_for_plotting(self,gdict, name):
        text_to_be_printed = "-----------------------------\n"
        text_to_be_printed += f"Tips for plotting this {name} (default values):\n"
        text_to_be_printed +=" - We suggest to whiten the data\n"
        text_to_be_printed +=" - select a f range between " + str(gdict["fmin"])+ " and " + str(gdict["fmax"]) + " Hz\n"        
        text_to_be_printed +=" - and zoom in time in ("+str(gdict["tmin"])+","+str(gdict["tmax"])+") s around t_center\n"
        text_to_be_printed +=" - For the Qscan options:\n"
        text_to_be_printed +=" - Q between "+str(gdict["Qmin"])+" and "+str(gdict["Qmax"])+"\n"
        text_to_be_printed +=" - Use Log y axis\n"
        text_to_be_printed +=" - Set Max Energy colorbar at the value of "+str(gdict["Emax"])+"\n"
        text_to_be_printed +="-----------------------------"
        #verify if the text is already there, and add it to the logger only if it is not there already
        is_there = self.check_if_text_is_already_there(text_to_be_printed)
        if not is_there:
            self.write_log_plot(text_to_be_printed)        
            
        
############################

    def plot_strain(self):
        #if the data have not been downloaded show a warning
        if self.data is None:
            warn_text = f"Please, go to the previous tab and download the data."
            warn_details = f"In the first tab you can download the data or load them from a file already saved locally."
            self.showdialogWarning(warn_text, warn_details)
            return
            
        #print tips for plotting in case of known event or glitch            
        if self.event in self.events_dict:
            self.tips_for_plotting(self.events_dict[self.event], 'GW event')            
        elif self.glitch in self.glitches_dict:
            self.tips_for_plotting(self.glitches_dict[self.glitch], 'glitch')    
        
        do_whiten,do_freq_sel,fmin,fmax,do_zoom,tmin,tmax, label_w, bp_label = self.check_common_plot_options()
        if (self.GPS_end - self.GPS_start)<2 and do_whiten:
            warn_text = f"At least 2 seconds of data are required to whiten them."
            warn_details = f"Use the previous tab to download a segment of data at least 2 seconds long or disable the whiten option in the Plot settings."
            self.showdialogWarning(warn_text, warn_details)
        else:
            try:    
                start_segment = self.GPS_start
                data_to_be_plot = self.data
                
                if do_whiten:  
                    white_data = data_to_be_plot.whiten()
                    data_to_be_plot = white_data

                if do_freq_sel:
                    #after the bandpass the data will be cropped so the residual duration has to be checked to avoid problems
                    if ((self.GPS_start+0.1)==(self.GPS_end-0.1)):
                        warn_text = f"At least 0.2 seconds of data are required to apply a bandpass filter."
                        warn_details = "Bacause of border effects caused by the band pass filter, data are cropped by 0.1 s at both ends."
                        warn_details += " The duration of the data you have downloaded is not enough to have residual data to plot after the cropping."
                        warn_details +=" You can download a longer segment of data or disable the bandpass filter option."
                        self.showdialogWarning(warn_text, warn_details)
                        return
                    bp_data = data_to_be_plot.bandpass(fmin, fmax)
                    bp_cropped = bp_data.crop(self.GPS_start+0.1, self.GPS_end-0.1)
                    data_to_be_plot = bp_cropped
                    #change allowed times for zoom in time because of the crop
                    half = self.decimals/2
                    self.horizontalSlider.setMinimum(int(-(self.duration)*half+0.1*self.decimals)) 
                    self.horizontalSlider_2.setMaximum(int(self.duration*half-0.1*self.decimals)) 
                    #add a warning in the logger if it is not already there
                    text_to_be_printed = "Data have been cropped by 0.1 s at both ends to avoid border effects due to the bandpass filter"
                    is_there = self.check_if_text_is_already_there(text_to_be_printed)
                    if not is_there:
                        self.write_log_plot(text_to_be_printed)

                if do_zoom:
                    duration = self.GPS_end - self.GPS_start
                    t_center = self.GPS_start + (duration/2)
                    start_segment = t_center+tmin
                    zoom = data_to_be_plot.crop(start_segment, t_center+tmax)
                    data_to_be_plot = zoom

                fig = (data_to_be_plot).plot()
                ax = fig.gca()
                if (self.GPS_ref):
                    ax.set_epoch(self.GPS_ref)
                else:
                    ax.set_epoch(start_segment)    
            
                if (self.download_event):
                    ax.set_title(f'{self.det_label} {label_w} strain data around {self.event}{bp_label}')
                else:
                    ax.set_title(f'{self.det_label} {label_w} strain data{bp_label}')    
                ax.set_ylabel('Amplitude [strain]')
                
                # PI: Create plot window identifier (used to update the plotting windows or avoid duplicates) 
                window_id = 'strain_plot'

                # Update the plot_window with the new figure (or create it if it does not exist)
                self.update_plot_window(fig, window_id)


#                if self.window2.isVisible():
#                    self.window2.hide()

#                else:
#                    self.window2.show()
            except Exception as e:
                self.write_log_plot("- An arror occurred, have you got the data before plotting?\n(go to the preious tab and select a GPS interval or an event or a glitch example)\n")
                self.write_log_plot("This error occurred: "+str(e))#for debugging purposes, remove later


############################

    def plot_Qscan(self):
        #if the data have not been downloaded show a warning
        if self.data is None:
            warn_text = f"Please, go to the previous tab and download the data."
            warn_details = f"In the first tab you can download the data or load them from a file already saved locally."
            self.showdialogWarning(warn_text, warn_details)
            return
                    
        #print tips for plotting in case of known event or glitch            
        if self.event in self.events_dict:
            self.tips_for_plotting(self.events_dict[self.event], 'GW event')            
        elif self.glitch in self.glitches_dict:
            self.tips_for_plotting(self.glitches_dict[self.glitch], 'glitch')    
        
        Qmin=self.spinBox.value()
        Qmax=self.spinBox_2.value()
        set_vmax = False
        if self.checkBox_8.isChecked():
            set_vmax = True
            vmax = self.spinBox_5.value()
        
        do_whiten,do_freq_sel,fmin,fmax,do_zoom,tmin,tmax, label_w, bp_label  = self.check_common_plot_options()
        
        start_segment = self.GPS_start
        end_segment = self.GPS_end
        if do_zoom:
            duration = self.GPS_end - self.GPS_start
            t_center = self.GPS_start + (duration/2)
            start_segment = t_center+tmin
            end_segment = t_center+tmax

        
        if (self.GPS_end - self.GPS_start)<2 and do_whiten:
            warn_text = f"At least 2 seconds of data are required to whiten them."
            warn_details = f"You can use the previous tab to download a segment of data long at least 2 seconds or disable the whiten option in the Plot settings."
            self.showdialogWarning(warn_text, warn_details)
        else:    
          try:    
            
              
            if do_freq_sel:
                qscan = (self.data).q_transform(whiten=do_whiten, frange=(fmin, fmax),outseg=(start_segment, end_segment),qrange=(Qmin,Qmax))
            else:
                qscan = (self.data).q_transform(whiten=do_whiten,outseg=(start_segment, end_segment),qrange=(Qmin,Qmax))
            
            if set_vmax:
                fig = qscan.plot(vmax=vmax)    
            else:    
                fig = qscan.plot()
            ax = fig.gca()
            if (self.GPS_ref):
                ax.set_epoch(self.GPS_ref)
            else:
                ax.set_epoch(start_segment)    
            
#            ax.set_epoch(start_segment)

            ax.colorbar(label="Normalised energy", cmap='viridis')
            if self.checkBox_6.isChecked():
                ax.set_yscale('log')

            if (self.download_event):
                    ax.set_title(f'{self.det_label} {label_w} strain data around {self.event}')
            else:
                    ax.set_title(f'{self.det_label} {label_w} strain data')


            # PI: Create plot window identifier (used to update the plotting windows or avoid duplicates) 
            window_id = 'qscan_plot'

            # Update the plot_window with the new figure (or create it if it does not exist)
            self.update_plot_window(fig, window_id)


#            if self.window3.isVisible():
#                self.window3.hide()

#            else:
#                self.window3.show()
          except Exception as e:
            self.write_log_plot("- An arror occurred, have you got the data before plotting?\n(go to the previous tab and select a GPS interval or an event or a glitch example)\n")
            self.write_log_plot("This error occurred: "+str(e))
            #for debugging purposes, remove later


############################
	
    def showdialog(self):
        msg = QMessageBox()
        msg.setIcon(QMessageBox.Icon.Information)

        
        msg.setText("This window contains instructions on how to use this tab")
        msg.setInformativeText("This is additional information")
        msg.setWindowTitle("MessageBox demo")
        msg.setDetailedText("The details are as follows:\n This is not a good choice because the app in not active when this window is open.\nFind a way to make the Main Window active when running this.")
 #       msg.setStandardButtons(QMessageBox.Ok | QMessageBox.Cancel)
 #       msg.buttonClicked.connect(msgbtn)
        msg.exec()
#        print( "value of pressed message box button:", retval)
	
#    def msgbtn(i):
#        print ("Button pressed is:",i.text())


############################

    def showdialogWarning(self, text="Additional information", details = "Details", response=False):
        msg = QMessageBox()
        msg.setIcon(QMessageBox.Icon.Warning)

        
        msg.setText("Warning")
        msg.setInformativeText(text)
        msg.setWindowTitle("Warning")
        msg.setDetailedText(details)
        
        
        if(response):
            msg.setStandardButtons(QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
            msg.setDefaultButton(QMessageBox.StandardButton.No)
            response = msg.exec()
            return response
        else:
            msg.exec()

############################

    # PI: A method to display a warning message box when the user tries to change the suggested filename
    # AT: Note that this method is similar to the previous one so they could be merged
    def warning_message_box(self):
        # Display a warning message
        warning_msg_box = QMessageBox()
        warning_msg_box.setIcon(QMessageBox.Icon.Warning)
        warning_msg_box.setWindowTitle("Warning")
        warning_msg_box.setText("We recommend not changing the suggested filename to ensure proper handling of files when loading data previously downloaded with the application. Are you sure you want to continue?")
        warning_msg_box.setStandardButtons(QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        warning_msg_box.setDefaultButton(QMessageBox.StandardButton.No)
        
        # NOTE: the text in the message box appears a bit small. 
        # Find a way to increase the font size of the text in the message box.

        response = warning_msg_box.exec()
        return response


############################

    def verify_correct_event_name(self, dropdown, textbox):
        #default value is 0 if the next conditions are not satisfied
        event_name = 0
        if (dropdown == "None" and textbox == ""):
#            self.write_log_event("Please select an event")
            textw = f"Please select an event"
            detailsw = f"Select an event from the drop down menu or write an event name in the text box"
            self.showdialogWarning(textw, detailsw)
        elif ((dropdown != "None") and (textbox == "")):
            event_name = dropdown.split(" ")[0]
            event_ok = True
        elif (textbox != "" and dropdown == "None"):
            event_name = textbox
            
            #check if the user have written the event name with lower case
            if (event_name[:2] == 'gw'):
                event_name = 'GW' + event_name[2:]
            #add a check to verify that this event exists...
            event_ok = True
        else:
#            self.write_log_event("Please choose only one option between writing the event name and selecting from a list")
            textw = f"Please choose only one option between writing the event name and selecting from a list"
            detailsw = f"Verify that the drop down menu is set to None when you write the event name in the text box"
            self.showdialogWarning(textw, detailsw)
        return event_name


############################

    def print_event_params(self):

        event = self.verify_correct_event_name(self.comboBox_4.currentText(), self.EventNameTab3.text())
            
        #the method verify_correct_event_name withh return 0 if the event name is not correct
        if event:
            
            self.event_tab3 = event
            try:
                info = fetch_event_json(self.event_tab3)
                text_to_be_printed = f"------------------------------------------\n"
                text_to_be_printed += f"Main info about {self.event_tab3}:\n"

                #version = '-v3' #for GW150914 and GW170817 this is the last version, to be checked for other events <---->
                #find the last version of the event in the database
                version = 0
                for v in info['events']:
                    version = v

                for key in self.event_parameters:
                    entry = self.event_parameters[key]
                    db_name = entry['db_name']
                    entry['value'] = info['events'][version][db_name]
                    if key != "Merger Time":
                        unit = info['events'][version][db_name+'_unit']
                        upper = info['events'][version][db_name+'_upper']
                        lower = info['events'][version][db_name+'_lower']
                        text_to_be_printed += f"- {key}: {entry['value']} (+{upper}, {lower}) [{unit}]\n"
                    else:
                        text_to_be_printed += f"- {key}: {entry['value']} [{entry['unit']}] (UTC: {from_gps(entry['value'])})\n"

                
                #print also the links to download the skymaps and the files with all the PE samples
                #I have to choose a PE sample version to do so
                pe_v = version
                for pe in info['events'][version]['parameters']:
                    if 'combined' in pe:
                        pe_v = pe
                skymap_link = info['events'][version]['parameters'][pe_v]['links']['skymap']
                                
                text_to_be_printed += f"\nThe link to download the skymap in fits is {skymap_link}\n"        
                PE_link = info['events'][version]['parameters'][pe_v]['data_url']
                text_to_be_printed += f"\nThe link to download the complete list of all the posterior sample is {PE_link}\n"
                self.write_log_event(text_to_be_printed)
            except ValueError:
                self.write_log_event("\nVerify that you have correctly written the event name. You can check the list of all published events in the website gwosc.org")
            except KeyError:    
                #This happen probably if the links to the PE or skymaps are not found
                #Not to sure what to write in this case
                self.write_log_event(text_to_be_printed)


############################

    def display_skymap(self):

        event = self.verify_correct_event_name(self.comboBox_4.currentText(), self.EventNameTab3.text())

        #the method verify_correct_event_name will return 0 if the event name is not reasonable
        if event:
            self.event_tab3 = event
            try:
                info = fetch_event_json(self.event_tab3)
                version = self.event_tab3
                for v in info['events']:
                    version = v #there should be only one version for each event
                #print('version',version)

                #check for graceDB link:
                # print('graceDB',info['events'][version]['gracedb_id'])
            
                gracedb_id = info['events'][version]['gracedb_id']


                #if possible download the skymaps via grace db
                found_gracedb = False

                
                # We need to check which skymaps are available on gracedb
                list_available_png = []


                # get url with 'requests'
                response = requests.get(f"https://gracedb.ligo.org/api/superevents/{gracedb_id}/files/?format=json")
                # print('response status:', response.status_code) # for checking purposes: 200 means OK 
                data = response.json()
                # print(data) # for checking purposes
                for key in data:
                    if 'png' in key and 'volume' not in key:
                        list_available_png.append(key)
                # print('list of available png:', list_available_png) # for checking purposes


                # If the list of available PNG files is empty, it means that no skymap is present on GraceDB. 
                # In this case we get the skymap from the gwcat database.
                if not list_available_png:
                    self.write_log_event("No PNG files available from GraceDB. Getting skymap from the gwcat database...")
                    link_skymap = f"https://ligo.gravity.cf.ac.uk/~chris.north/gwcat-data/data/png/{self.event_tab3}_moll_pretty.png"
                    skymap_file = f"{self.event_tab3}_skymap.png"

                else:
                    for png in list_available_png:
                        if 'PublicationSamples' in png:
                            link_skymap = f"https://gracedb.ligo.org/apiweb/superevents/{gracedb_id}/files/{png}"
                            skymap_file = f"{png}"
                            break
                        elif 'LALInference' in png:
                            link_skymap = f"https://gracedb.ligo.org/apiweb/superevents/{gracedb_id}/files/{png}"
                            skymap_file = f"{png}"
                            break
                        elif 'bayestar' in png:
                            link_skymap = f"https://gracedb.ligo.org/apiweb/superevents/{gracedb_id}/files/{png}"
                            skymap_file = f"{png}"
                            break
                        else:
                            link_skymap = f"https://gracedb.ligo.org/apiweb/superevents/{gracedb_id}/files/{png}"    
                            skymap_file = f"{png}"
                    found_gracedb = True


                print('link_skymap',link_skymap)
                print('found_gracedb',found_gracedb)
            

                warn_text = f"You will now choose the directory where to save the {skymap_file}. The file will be displayed after you save it."
                warn_details = f"You can also retrieve the same file at the url {link_skymap}"
                if(not found_gracedb):
                    warn_text += "\nFor this event the original skymap provided from the LVK via the gracedb website cannot be downloaded so an alternative is provided."
                self.showdialogWarning(warn_text, warn_details)
                
                
                #open. window to choose where to save the file
                
                # Loop to reopen the save file dialog with the suggested filename if the user changes it
                while True:
                    filename, _ = QFileDialog.getSaveFileName(
                               self, 
                               'Save File', 
                               os.path.join(os.path.expanduser('~'), skymap_file), 
                               'png files (*.png)'
                           )
                    if not filename:  # If the user cancels the dialog, return without saving
                        return
                    break
                # print("filename",filename)     # for checking purposes         
                

                # Download the skymap file
                response_skymap_file = requests.get(link_skymap)
                with open(filename, 'wb') as file:
                    file.write(response_skymap_file.content)

    

                dialog = QtWidgets.QDialog()
                lay = QtWidgets.QVBoxLayout(dialog)
            
                title = QtWidgets.QLabel()
                title.setText(f"Skymap for {self.event_tab3}")
                lay.addWidget(title)
            
                label = QtWidgets.QLabel()
                lay.addWidget(label)
                pixmap = QtGui.QPixmap(filename)

                #check size of the skyma and rescale if too big
                map_width = pixmap.rect().width()
                map_height = pixmap.rect().height()
                if (map_height>1000):
                    pixmap = pixmap.scaled(QSize(int(map_width/5), int(map_height/5)))
            
                label.setPixmap(pixmap)
                dialog.exec()
            except Exception as e:
                self.write_log_event("Something went wrong!")
                self.write_log_event(f"Type of the exception: {type(e)}") 
                self.write_log_event(f"This error occurred: {e}")



############################

    def get_catalogs(self):
        self.write_log_event("\nDownloading parameters for all confident detections published by the LIGO-Virgo-KAGRA collaborations...\n")
        worker = Worker(self.download_catalogs)
        worker.signals.result.connect(self.print_output_tab3)
        # worker.signals.finished.connect(self.thread_complete) 
        worker.signals.finished.connect(self.catalogs_download_finished)
        worker.signals.progress.connect(self.progress_fn)
        # Execute
        self.threadpool.start(worker)
        
        

        

############################

    def download_catalogs(self, progress_callback):
        output = "Catalogs downloaded:\n"
        catalog_list_names = ['GWTC-1-confident','GWTC-2.1-confident', 'GWTC-3-confident']
        # Add all the confident catalogs not already included in the list
        all_catalogs = find_datasets(type="catalog")
        for c in all_catalogs:
            if re.match(r"GWTC-[0-9]-confident", c):
                if c not in catalog_list_names:
                    catalog_list_names.append(c)

        # Add GWTC-4-confident is not present in the updated list add O4_Discovery_Papers
        if 'GWTC-4-confident' not in catalog_list_names:
            catalog_list_names.append('O4_Discovery_Papers')
        
        self.catalogs = []
        for catalog in catalog_list_names:
            c = fetch_json(f"https://gwosc.org/eventapi/json/query/show?release={catalog}&lastver=true")
            output += catalog
            output += "\n"
            self.catalogs.append(c)

        progress_callback.emit(100)
        return output+"\n- Done!\n"


############################

    def print_output_tab3(self, s):
        print(s)
        self.write_log_event(s)


############################

    def plot_parameter_histogram(self):
        
        self.user_action_tab3 = "plot_histogram"
        key = self.comboBox_5.currentText()

        if (key == "None"):
            self.write_log_event("Select a parameter for the histogram")
        elif (self.catalogs is None):
            # PI: download catalogs if they are not there already
            self.get_catalogs()
        else:
            # PI: e.g if the catalogs are downloaded already but we want to plot some other parameter
            self.plot_hist_after_download()


############################

    def plot_parameter_scatter(self):
        
        self.user_action_tab3 = "2D_scatter_plot"
        key1 = self.comboBox_5.currentText()
        key2 = self.comboBox_6.currentText()

        if (key1 == "None" or key2 == "None"):
            self.write_log_event("\nSelect two parameters for the scatter plot")
        elif (self.catalogs is None):
            # PI: download catalogs if they are not there already
            self.get_catalogs()
        else:  
            # PI: e.g if the catalogs are downloaded already but we want to plot some other pair of parameters
            self.plot_2D_scatter_after_download()



#----------------------------------------------------            
class AnotherWindow(QtWidgets.QWidget):
    """
    This "window" is a QWidget. If it has no parent,
    it will appear as a free-floating window.
    """

    # def __init__(self, fig, plot_id, main_window):
    def __init__(self, fig, main_window):

        # Set the main_window as the parent of the plotting_window
        # This is needed if we want the separate plotting window to close too when the main window is closed.
        super().__init__(main_window)

        # Set the window title
        self.setWindowTitle("Plotting window")


        # Set the window flags to make the plotting_window a top-level window
        # This is needed , because the window is created as a child of the main window
        # (otherwise it does not appear at all)
        self.setWindowFlag(QtCore.Qt.WindowType.Window)
        

        self.layout = QtWidgets.QVBoxLayout()
        self.setLayout(self.layout)
        self.canvas = FigureCanvas(fig) # create canvas
        self.layout.addWidget(self.canvas)   # add canvas to layout
 
        # Create and add toolbar
        toolbar = NavigationToolbar(self.canvas, self)
        self.layout.addWidget(toolbar)

    def update_plot(self, fig):    
        # Remove the old canvas
        self.layout.removeWidget(self.canvas)
        self.canvas.deleteLater()

        # Add the new canvas
        self.canvas = FigureCanvas(fig)
        # self.layout.addWidget(self.canvas)
        # PI: Insert the new canvas at the top of the layout, ensuring that the navigation toolbar remains at the bottom    
        self.layout.insertWidget(0, self.canvas) 
        self.canvas.draw()    

#----------------------------------------------------            
# PI: class to display help text in a new window
class HelpWindow(QtWidgets.QWidget):
    """
    This "window" is a QWidget. If it has no parent,
    it will appear as a free-floating window.
    """

    def __init__(self, help_text, main_window):
        # Set the main_window as the parent of the help_window
        # This is needed if we want the separate help window to close too when the main window is closed.
        super().__init__(main_window) 

        # Set the window title
        self.setWindowTitle("Help window")

        # Set the window flags to make the help_window a top-level window
        # This is needed , because the window is created as a child of the main window
        # (otherwise it does not appear at all)
        self.setWindowFlag(QtCore.Qt.WindowType.Window)

        # Set the initial size of the help window
        self.resize(600, 400)  # Width: 600, Height: 400

        # Define the horizontal space between the Main Window and the Help Window
        horizontal_space = 20  # Adjust this value as needed

        # Get the geometry of the main window
        main_frame_geometry = main_window.frameGeometry()

        # Set the position of the help window relative to the main window
        # and add some horizontal space to the right of the main window
        self.move(main_frame_geometry.right() + horizontal_space, main_frame_geometry.top())

        # # Set the initial position of the help window
        # self.move(100, 100)  # X: 100, Y: 100

        # Create QTextBrowser instance
        helpbrowser = QtWidgets.QTextBrowser()
        
        # Set the help text
        # helpbrowser.setText(help_text)
        helpbrowser.setHtml(help_text)
        
        # Add the QTextBrowser to the layout
        layout = QtWidgets.QVBoxLayout()
        layout.addWidget(helpbrowser)
        self.setLayout(layout)
        
        
#----------------------------------------------------
if __name__ == '__main__':
    app = QtWidgets.QApplication(sys.argv)
    window = MainWindow()
    window.show()
    app.exec()