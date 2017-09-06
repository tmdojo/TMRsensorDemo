# serial_plotter

Python code to

1. Read data from serial port or MQTT subscription
2. Save data to file
3. Plot data in real time

This tool works nice with Arduino and the like.

## Dependancies

* Python 3.5
* PyQt4
* pyqtgraph
* numpy
* pySerial
* paho

## Environment setup

It is recommended to setup a new anaconda environment and install dependancies. Take special note that conda installs PyQt5 by default and you need to downgrade it to PyQt4.

conda create -n serialplotter python=3.5 anaconda
source activate serialplotter
conda install pyqt=4.11.4
conda install pyqtgraph pySerial
pip install paho-mqtt
