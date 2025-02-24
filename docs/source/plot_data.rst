Plot Data
=========

The :guilabel:`Plot Data` tab allows users to visualize the GW data. 

.. image:: _static/plot_data_tab.png
    :width: 100%
    :align: center

Strain and Q scan
-----------------
You can plot the data in two different ways, via the corresponding buttons:

* :guilabel:`Plot strain` allows you to plot the gravitational wave data (called strain) 
  as a function of time.
* :guilabel:`Plot Qscan` allows you to plot the time-frequency evolution of the 
  gravitational wave data.

  * In particular, we use a time-frequency representation commonly used by 
    the GW community based on the `Q-transform`_ (see also `this paper`_). 
  * This plot depends on a quality factor Q. Check `this tutorial`_ to help you choose 
    the right Q value for your plot.

Plot settings
-------------

Under the :guilabel:`Plot settings` section, the user can select plotting options that 
apply to both plots:

* A check box can be used to indicate whether to whiten the data or not 
  (see also :ref:`whitening_section_label`).
* A bandpass filter will be applied unless the :guilabel:`No freq selection` is 
  clicked (band passing is filtering within a specific frequency range). 
  The user can choose the frequency range with which to filter the data.
* To zoom in time users can select a time window using as reference the central time 
  of the available segment.

Under the :guilabel:`Q scan` section, the user can select additional settings, specific 
to the Q scan plot:

* Set the maximum and minimum values of Q.
* Set the y-axis to log scale.
* Set the maximum energy for the colour bar.

Notes on plotting
-----------------

- After changing the parameters, click the buttons :guilabel:`Plot Qscan` and 
  :guilabel:`Plot Qscan` again to update the plots.
- If you have downloaded data for GW events or glitches from the dropdown menus, 
  the default values of all the plot settings will be automatically fixed to the values 
  that allow optimal plots. 
  In addition, the x-axis representing time will have its zero at the expected time of 
  the merger for the GW event or at the central time for the glitch (what is called 
  :code:`event_time` in the `GravitySpy repository`_).
- Only the most loud events, i.e. events with a high `signal-to-noise ratio`_, are visible by eye with the minimal post-processing 
  allowed by this app.


.. _Q-transform: https://en.wikipedia.org/wiki/Constant-Q_transform
.. _this paper: https://iopscience.iop.org/article/10.1088/0264-9381/21/20/024
.. _this tutorial: https://github.com/jkanner/gw-intro/blob/main/extra/Estimate%20Q-value.ipynb
.. _GravitySpy repository: https://zenodo.org/records/5649212
.. _signal-to-noise ratio: https://en.wikipedia.org/wiki/Signal-to-noise_ratio