GW Data Plotter
===============

What does it do?
----------------

**GW Data Plotter** is a desktop application that simplifies access to Gravitational Wave (GW) data 
and facilitates basic visualization and analysis.

The app allows users to download *public* gravitational wave data from the LIGO, Virgo, KAGRA, and 
GEO detectors via the `Gravitational Wave Open Science Center <https://gwosc.org>`_. 

- `Source Code @ GitHub`_
- `Issue Tracker`_

.. Zenodo badge that points to the latest release
.. image:: https://img.shields.io/badge/dynamic/json?url=https://zenodo.org/api/records/13778827&label=DOI&query=$.doi&color=blue   
  :target: https://doi.org/10.5281/zenodo.13778827  

.. license badge
.. image:: https://img.shields.io/badge/License-GPL--3.0--or--later-blue
    :target: https://choosealicense.com/licenses/gpl-3.0/
    :alt: License: GPL-3.0-or-later 


Who is it for?
--------------

Accessing and visualizing GW data can be challenging for non-experts. Even though the data is publicly available and the 
software tools to analyze it are open-source, the learning curve can be steep.

**GW Data Plotter** aims to lower this barrier by providing a graphical user interface to improve GW data accessibility. 
Users do not need to be experts in programming to use the app or know the details of the specific software packages 
used in GW data analysis.

Initially developed for scientists outside the GW community wishing to access GW data for their research, the app is also 
intended for students and educators that first enter the field of GW astronomy. 

Serving as a stepping stone, the app helps 
to achieve familiarization with GW data, allowing even novice users to interact with *actual* GW events putting aside the 
technical details.



Installing the app
------------------

- The easiest way to install the app is to download and run the executable file suitable for your operating system from the 
  `Zenodo repository`_. 
- Executable files are available for Windows, Linux, and macOS.
- For further details on how to install the app, please refer to the :doc:`install` page.


Citing the app
--------------

If you have used **GW Data Plotter** in a project, please acknowledge this by citing the DOI of the specific version 
of the app you have used. You can find the DOI in the `Zenodo repository`_. See the *Citation* section on the Zenodo page 
for different citation formats.


Report an issue
---------------

If you encounter any bugs or issues while using the app, or you would like to share your feedback please create a *New issue* on the `Issue Tracker`_. 


.. toctree::
   :maxdepth: 2
   :caption: Contents

   Home <self>
   install
   description
   get_data 
   plot_data
   explore_data
   links
   ack

License
-------

This software is licensed under the **GNU General Public License v3 or later (GPL-3+).**
Please read the `license`_ text for full details.

.. _Zenodo repository: https://zenodo.org/records/13778827
.. _license: https://choosealicense.com/licenses/gpl-3.0/
.. _Source Code @ GitHub: https://github.com/camurria/GW_Data_Plotter/
.. _Issue Tracker: https://github.com/camurria/GW_Data_Plotter/issues

