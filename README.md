# GW Data Plotter
GW Data Plotter is a desktop application that simplifies access to Gravitational Wave (GW) data and facilitates basic 
visualization and analysis. 
This reposity contains the source files to run the GW Data Plotter App from a python script. 
The code is based on [PyQt6](https://www.riverbankcomputing.com/software/pyqt/) for the graphical interface, and
[gwpy](https://gwpy.github.io) and [gwosc](https://pypi.org/project/gwosc/) python packages for the gravitational wave 
related part.

[![DOI](https://img.shields.io/badge/dynamic/json?url=https://zenodo.org/api/records/13778827&label=DOI&query=$.doi&color=blue)](https://doi.org/10.5281/zenodo.13778827)
[![License: GPL-3.0-or-later](https://img.shields.io/badge/License-GPL--3.0--or--later-blue)](https://choosealicense.com/licenses/gpl-3.0/)


## Description of the python scripts
This repository contains 3 python scripts:
* `gw_data_plotter.py`: main script; to get the app just execute on a terminal `python gw_data_plotter.py`
* `layout.py`: it is imported by the main script and contains the details of the layout of the app
* `app_resources.py`: it is imported by the main script and contains the resources used by the app

## Conda environment
To run the code you will need to set up an appropriate conda environment. 
We provide yml files so that you can build directly the conda environment for your machine in the folder `conda_environments`. 
You can select the environment more suited for your Operating System (OS) and then create the environment with:

`conda env create --file environment.yml`

(replacing environment.yml with the appropriate name of the environment file for your machine). And activate it with:

`conda activate app`

Use:
* `environment_LinuxOS.yml` for Linux users;
* `environment_MacOS_arm64.yml` for Mac users with an Apple processor;
* `environment_MacOS_x86_64.yml` for Mac users with an Intel processor;
* `environment_WindowsOS.yml` for Windows users.

## Main python packages
If for some reason you can't use the previous environment files you can anyway build your environment 
installing the following packages:
* `PyQt6` (version 6.6.1, this version is not directly available on conda so you have to install it with pip);
* `gwpy`(version 3.0.8);
* `gwosc` (version 0.7.1).
