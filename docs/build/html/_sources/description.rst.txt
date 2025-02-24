Description
===========

GUI overview
------------

The content is organised in three tabs, see the respective pages for details:

- :doc:`get_data`
- :doc:`plot_data`
- :doc:`explore_data` 

All the tabs have two common features, a :guilabel:`Help` button and a :guilabel:`Log window`.

- The :guilabel:`Help` button displays documentation specific to each tab in a separate window.
- The :guilabel:`Log window` displays the output of ongoing operations (e.g. the status of downloads) 
  or tips (e.g. for plotting). The most recent messages will appear in the upper part of the window. 

The app will also display warning messages to guide users when they enter invalid input or specify conflicting options.


Technical details
-----------------

- **GW Data Plotter** is written in *Python*. 
- Its main functionalities are based on packages `gwosc`_ and `GWpy`_ developed by the GW community.
- The graphical interface was created with `Qt`_, a cross-platform GUI toolkit, using the *Python* binding `PyQt`_.
- The standalone executable files are created with `PyInstaller`_.


.. _gwosc: https://gwosc.readthedocs.io/en/stable/
.. _GWpy: https://gwpy.github.io/
.. _PyInstaller: https://pyinstaller.org/en/stable/
.. _PyQt: https://www.riverbankcomputing.com/software/pyqt/
.. _Qt: https://en.wikipedia.org/wiki/Qt_(software)