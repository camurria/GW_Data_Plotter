Get Data
========

The :guilabel:`Get Data` tab allows users to download publicly available GW data originally hosted on the 
`GWOSC <https://gwosc.org/>`_ website. Users can download data in one of the following ways:

.. image:: _static/get_data_tab.png
    :width: 100%
    :align: center

By time interval
------------------------------------

Under the :guilabel:`Select Data by time interval` section the user can specify a time interval by typing the starting and 
ending times in GPS format, which is the convention used by the GW community. 
In this convention, the time is calculated by counting seconds from a reference date (6th January 1980). 
To convert `UTC time`_ to GPS time format visit `this link <https://gwosc.org/gps/>`_.


By selecting a known GW event 
-----------------------------

Under the :guilabel:`Select a known GW event` section, users can choose to download a few showcase GW events 
or type the name of a specific GW event published by the LIGO-Virgo-KAGRA (LVK) collaboration.
To get the GPS times and names of all known detections, check `this page <https://gwosc.org/eventapi/>`_.  

The subsection :guilabel:`Select duration of data segment` can be used to decide how many seconds of data you want 
to download before and after the merger time of the event. 
The starting time for the data download is calculated as :code:`(merger time) + (time before the merger)` so the 
time before the merger is expected to be a negative number.
    
By selecting a known glitch
---------------------------

A glitch is a short-time noise artifact which can mimic a GW signal. 
Possible glitches are already identified in the LVK data. 
Under the :guilabel:`Select an example of a known glitch` section, users can select 
to download a few examples of glitches. 
A good source to get the full list of known glitches (with their GPS times of occurrence) in the first three 
observing runs is the `GravitySpy Zenodo repository`_.


Data handling
-------------

The :guilabel:`Get Data` tab contains 3 buttons:

* :guilabel:`Download Data`: download the data and save them in memory for later plotting (no file will be saved on your PC) 
* :guilabel:`Load data`: load data from a file already saved locally in one of the formats: ``hdf5``, ``gwf`` and 
  ``txt``. 
  The loading can read any file previously saved with the **GW Data Plotter** app or downloaded from the 
  `GWOSC <https://gwosc.org/>`_ website.
* :guilabel:`Save data`: save data already downloaded in a local file. Also in this case the formats available are 
  ``hdf5``, ``gwf`` and ``txt``.

.. _whitening_section_label:

Whitening
---------

The whitening procedure allows data to be re-weighted according to the detector noise at each frequency, 
so it is equivalent to a sort of noise removal.
We strongly advise using it when possible.
To use the whitening procedure, we suggest downloading at least 2 seconds of data.
Remember to select a detector if you are downloading the data via time interval or selecting a known GW event.

.. _UTC time: https://en.wikipedia.org/wiki/Coordinated_Universal_Time
.. _GravitySpy Zenodo repository: https://zenodo.org/records/5649212