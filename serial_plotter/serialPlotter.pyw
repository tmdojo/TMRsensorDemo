# Copyright (c) 2016 Shunya Sato
# Author: Shunya Sato
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.

# make this code Py2 and Py3 compatible
# make sure you have "pip install future"
from __future__ import (absolute_import, division,
						print_function, unicode_literals)
from builtins import (
		 bytes, dict, int, list, object, range, #str, #paho uses isinstance of str and doesn't like future's str
		 ascii, chr, hex, input, next, oct, open,
		 pow, round, super,
		 filter, map, zip)

import logging
logging.basicConfig(level=logging.DEBUG,
					format='[%(levelname)s] (%(threadName)-10s) %(message)s',
					)

import os, sys, time
import json
from datetime import datetime

from PyQt4 import QtCore, QtGui
import pyqtgraph as pg

import numpy as np
import serial
import paho.mqtt.client as mqtt

from ui_serialPlotter import Ui_MainWindow

class SerialWorker(QtCore.QObject):
	# http://stackoverflow.com/questions/6783194/background-thread-with-qthread-in-pyqt
	finished = QtCore.pyqtSignal()
	dataReady = QtCore.pyqtSignal(str)

	def __init__(self):
		super(SerialWorker, self).__init__()
		self.addr  = "COM1"
		self.baud  = 115200 #9600
		self.running = False
		self.port = None
		self.fname = "magi_log.txt"
		self.use_file = False

	@QtCore.pyqtSlot()
	def processA(self):
		print("SerialWorker.processA")
		if self.use_file:
			self.port = open(self.fname, "r")
		else:
			try:
				print("Try opening serial port: {}".format(self.addr))
				self.port = serial.Serial(self.addr,self.baud)
			except:
				print("Error opening serial port!")
				self.port = None
				return None
		print("opened port")
		while self.running:
			#print "SerialWorker is running"
			line = str(self.port.readline())
			self.dataReady.emit(line)
			if self.use_file:
				time.sleep(0.01)

		print("SerialWorker finished processA")
		self.port.close()
		print("port is closed")
		self.finished.emit()

	def startRunning(self, portname):
		if portname == "FILE":
			self.use_file = True
		else:
			self.use_file = False
			self.addr = portname
		self.running = True

	def stopRunning(self):
		self.running = False

	def setFilename(self, fname):
		self.fname = fname

	def __del__(self):
		self.running = False
		if self.port:
			self.port.close()

class MqttWorker(QtCore.QObject):
	# http://stackoverflow.com/questions/6783194/background-thread-with-qthread-in-pyqt
	finished = QtCore.pyqtSignal()
	dataReady = QtCore.pyqtSignal(str)

	def __init__(self):
		super(MqttWorker, self).__init__()
		self.host  = "192.168.10.110"
		self.port  = 1883
		self.running = False
		self.fname = "magi_log.txt"

	@QtCore.pyqtSlot()
	def processA(self):
		print("MqttWorker.processA")
		self.client = mqtt.Client()
		self.client.on_connect = self.on_connect
		self.client.on_message = self.on_message
		print("Connecting to MQTT broker at {}".format(self.settings['host']))
		self.client.connect(**self.settings)
		self.client.loop_start()
		while self.running:
			time.sleep(1)
		print("MqttWorker finished processA")
		self.client.loop_stop()
		self.finished.emit()

	def on_connect(self, client, userdata, flags, rc):
		print("Connected with result code "+str(rc))

		# Subscribing in on_connect() means that if we lose the connection and
		# reconnect then subscriptions will be renewed.
		#client.subscribe("$SYS/#")
		#self.client.subscribe("feeds/currentsensors/#")
		# subscribe requires string not unicode ...
		print("Topic: {}".format(self.topic))
		self.client.subscribe(str(self.topic))

	# The callback for when a PUBLISH message is received from the server.
	def on_message(self, client, userdata, msg):
		self.dataReady.emit(msg.payload)

	def startRunning(self, topic, host, port):
		self.settings = {}
		self.settings['host'] = host
		self.settings['port'] = port
		self.topic = topic
		self.running = True

	def stopRunning(self):
		self.running = False

	def __del__(self):
		self.running = False

class DataObject(object):
	def __init__(self, name, plotwdg, pen=pg.mkPen('r', width=1.0, style=QtCore.Qt.SolidLine)):
		self.pen = pen
		self.ydata = np.zeros(300)
		#self.dataplot = plotwdg.plot(self.ydata, symbol='o', symbolBrush=(255,0,0), symbolPen='w')
		self.dataplot = plotwdg.plot(self.ydata, symbol='o', symbolSize=2)
		self.dataplot.setPen(self.pen)
		self.name = name

		parent = None #self.groupBox_liveUpdate
		#TODO: start work here
		self.horizontalLayout = None
		self.checkbox_show = QtGui.QCheckBox(parent)
		self.checkbox_show.setChecked(True)
		self.lineedit_name = None
		self.botton_color = None
		self.checkbox_marker = None

	def hidePlot(self):
		self.dataplot.setPen(None)
		self.dataplot.setSymbol(None)

	def showPlot(self):
		self.dataplot.setPen(self.pen)
		self.dataplot.setSymbol("o")

	def resetData(self):
		self.ydata = np.zeros(300)
		self.dataplot.setData(self.ydata)

	def pushData(self, newData):
		self.ydata[:-1] = self.ydata[1:]
		self.ydata[-1] = newData
		self.dataplot.setData(self.ydata)

	def setPen(self, newPen):
		self.pen = newPen
		self.dataplot.setPen(self.pen)

class LissajousObject(object):
	def __init__(self, plotwdg, symbolPen=pg.mkPen('r', width=1.0, style=QtCore.Qt.SolidLine)):
		self.plotwdg = plotwdg
		self.plotwdg.setAspectLocked(lock=True, ratio=1)
		# plot data points
		self.xdata = np.zeros(300)
		self.ydata = np.zeros(300)
		self.dataplot = plotwdg.plot(self.xdata, self.ydata, pen=None, symbol='o', symbolPen=symbolPen, symbolSize=2)
		# plot max distance circle
		self.radius = 1200
		self.phis=np.arange(0,np.pi*2,0.01)
		self.rimplot = plotwdg.plot(self.radius*np.cos(self.phis), self.radius*np.sin(self.phis), pen=pg.mkPen('g', width=1.0, style=QtCore.Qt.SolidLine))
		maxval = 1.1 * self.radius
		self.plotwdg.setRange(xRange=(-1*maxval, maxval), yRange=(-1*maxval, maxval))
		self.currentX = 0
		self.currentY = 0
		self.currentplot = plotwdg.plot([0],[0], pen=None, symbol='o', symbolPen=pg.mkPen('c', width=2.0, style=QtCore.Qt.SolidLine), symbolSize=6)

	def pushData(self, sindata, cosdata):
		self.xdata[:-1] = self.xdata[1:]
		self.xdata[-1] = cosdata
		self.ydata[:-1] = self.ydata[1:]
		self.ydata[-1] = sindata
		self.dataplot.setData(self.xdata, self.ydata)
		rho = np.sqrt(cosdata**2 + sindata**2)
		if(self.radius < rho):
			self.updateRim(rho)
		self.currentplot.setData([cosdata], [sindata])

	def updateRim(self, radius):
		self.radius = radius
		self.rimplot.setData(self.radius*np.cos(self.phis), self.radius*np.sin(self.phis))
		maxval = 1.1 * self.radius
		self.plotwdg.setRange(xRange=(-1*maxval, maxval), yRange=(-1*maxval, maxval))

class MainWindow(QtGui.QMainWindow, Ui_MainWindow):
	"""
		Serial data logger program
		This version is good for plotting fast (up to about 100Hz)
		sampling and saving to file. This version uses Qt's QThread
		and Signal/Slot mechanics.
		For more saving options with slower (<10Hz) signals, use
	"""
	def __init__(self, parent=None):
		super(MainWindow, self).__init__(parent)
		self.setupUi(self)

		self.thread = QtCore.QThread()  # no parent!
		self.serialreader = SerialWorker()  # no parent!
		self.serialreader.moveToThread(self.thread)
		#self.serialreader.dataReady.connect(self.printPayload)
		self.serialreader.dataReady.connect(self.processPayload)
		self.thread.started.connect(self.serialreader.processA)

		self.thread_mqtt = QtCore.QThread()  # no parent!
		self.mqttreader = MqttWorker()  # no parent!
		self.mqttreader.moveToThread(self.thread_mqtt)
		self.mqttreader.dataReady.connect(self.processPayload)
		self.thread_mqtt.started.connect(self.mqttreader.processA)

		# if you want the thread to stop after the worker is done
		# you can always call thread.start() again later
		# obj.finished.connect(thread.quit)

		# one way to do it is to start processing as soon as the thread starts
		# this is okay in some cases... but makes it harder to send data to
		# the worker object from the main gui thread.  As you can see I'm calling
		# processA() which takes no arguments
		#thread.started.connect(obj.processA)
		#thread.finished.connect(app.exit)
		#thread.start()

		#self._serialReader = serialreader()
		#self._serialReader.updated.connect(self.processPayload)
		self.pushButton.clicked.connect(self.start)
		self.pushButton_mqtt_connect.clicked.connect(self.start_mqtt)
		self.pushButton_update.clicked.connect(self.populatePort)
		self.pushButtonUpdateFileName.clicked.connect(self.populateFileName)
		self.pushButton_AutoRange.clicked.connect(self.onAutoRange)

		self.populatePort()
		self.populateFileName()

		self.running = False
		self.logfileh = None

		self.dataObject_list = []
		dataNames = ['millis', 'a0', 'single', 'diff']
		colors = [(228,26,28), (55,126,184), (77,175,74), (152,78,163),
					(255,127,0), (255,255,51), (166,86,40), (247,129,191)]
		for color in colors:
			pen = pg.mkPen(color, widht=1.0, style=QtCore.Qt.SolidLine)
			self.dataObject_list.append(DataObject("", self.plotwdg, pen))

		self.plot_ckboxes = [self.checkBox_d0, self.checkBox_d1
						, self.checkBox_d2, self.checkBox_d3
						, self.checkBox_d4, self.checkBox_d5
						, self.checkBox_d6, self.checkBox_d7]
		# TODO: hate this mess...
		self.groupBox_liveUpdate.toggled.connect(lambda: self.clearPlot(None))
		self.checkBox_d0.toggled.connect(lambda: self.clearPlot(0))
		self.checkBox_d1.toggled.connect(lambda: self.clearPlot(1))
		self.checkBox_d2.toggled.connect(lambda: self.clearPlot(2))
		self.checkBox_d3.toggled.connect(lambda: self.clearPlot(3))
		self.checkBox_d4.toggled.connect(lambda: self.clearPlot(4))
		self.checkBox_d5.toggled.connect(lambda: self.clearPlot(5))
		self.checkBox_d6.toggled.connect(lambda: self.clearPlot(6))
		self.checkBox_d7.toggled.connect(lambda: self.clearPlot(7))

		self.lissajous = LissajousObject(self.plotwdg_2)


	def onAutoRange(self):
		self.plotwdg.enableAutoRange()

	def populatePort(self):
		self.comboBox.clear()
		serials = [('FILE', '', ''),]
		import serial.tools.list_ports
		#print list(serial.tools.list_ports.comports())
		serials += list(serial.tools.list_ports.comports())
		for device in serials:
			self.comboBox.addItem(device[0])

		# select last one as default
		nports = self.comboBox.count()
		if nports != 0:
			self.comboBox.setCurrentIndex(nports-1)

	def populateFileName(self):
		now = datetime.now()
		fname = "magilog_{:04d}{:02d}{:02d}{:02d}{:02d}{:02d}.txt".format(now.year, now.month, now.day, now.hour, now.minute, now.second)
		self.lineEdit.setText(os.path.join("log", fname))

	def populateCheckBox(self, data):
		pass

	def start(self):
		if not self.running:
			print("Start running!")
			if str(self.comboBox.currentText()) == 'FILE':
				self.serialreader.setFilename(str(QtGui.QFileDialog.getOpenFileName(self, 'Open log file', 'log/', '*.txt')))
			self.serialreader.startRunning(str(self.comboBox.currentText()))
			self.thread.start()
			self.running = True
			self.pushButton.setText("STOP")
			self.pushButton_mqtt_connect.setEnabled(False)
			if self.checkBox_csv.isChecked():
				#TODO: except IOError. happens when log directory does not exist.
				self.logfileh = open(str(self.lineEdit.text()), 'w')

		else:
			print("Stop running.")
			self.serialreader.stopRunning()
			self.thread.quit()
			self.running = False
			self.pushButton.setText("START")
			self.pushButton_mqtt_connect.setEnabled(True)
			if self.logfileh:
				self.logfileh.close()
				self.logfileh = None

	def start_mqtt(self):
		if not self.running:
			print("Start running!")
			#str(self.comboBox.currentText())
			topic = str(self.lineEdit_mqtt_topic.text())
			host = str(self.lineEdit_mqtt_host.text())
			port = int(self.lineEdit_mqtt_port.text())
			self.mqttreader.startRunning(topic, host, port)
			self.thread_mqtt.start()
			self.running = True
			self.pushButton_mqtt_connect.setText("STOP")
			self.pushButton.setEnabled(False)
			if self.checkBox_csv.isChecked():
				#TODO: except IOError. happens when log directory does not exist.
				self.logfileh = open(str(self.lineEdit.text()), 'w')

		else:
			print("Stop running.")
			self.mqttreader.stopRunning()
			self.thread_mqtt.quit()
			self.running = False
			self.pushButton_mqtt_connect.setText("START")
			self.pushButton.setEnabled(True)
			if self.logfileh:
				self.logfileh.close()
				self.logfileh = None

	def processPayload(self, payloadQs):
		"""
		Receive QString payload
		"""
		#convert QString payload to Python String
		payload = unicode(payloadQs).encode('latin-1')
		#payload = payloadQs
		self.textBrowser_log.append(payload.strip())
		if self.checkBox_autoscroll.isChecked():
			self.textBrowser_log.moveCursor(QtGui.QTextCursor.End)
		if self.logfileh:
			self.logfileh.write(unicode(payload))

		if self.radioButton_csv.isChecked():
			# parse as csv
			data_list = payload.split(',')
			#data = OrderedDict()
			data = []
			for i, item in enumerate(data_list):
				#name = "data{}".format(i)
				#data[name] = float(item.strip())
				try:
					data.append(float(item.strip()))
				except:
					#print("Not a number: {}".format(item))
					pass
		else:
			# format is json
			try:
				data_dic = json.loads(payload)
			except:
				#print("Not json: {}".format(payload))
				return None
			data = data_dic.values()

		self.updatePlot(data)
		self.updateLabels(data)
		self.lissajous.pushData(data[0], data[1])

	def updateLabels(self, data):
		self.label_sin.setText(str(data[0]))
		self.label_cos.setText(str(data[1]))
		self.label_angle.setText(str(data[2]))
		self.label_rho.setText(str(np.sqrt(data[0]**2+data[1]**2)))
		self.label_rho_max.setText(str(self.lissajous.radius))

	def updatePlot(self, data):
		checkBoxes = [self.checkBox_d0, self.checkBox_d1, self.checkBox_d2, self.checkBox_d3]
		for i, item in enumerate(data):
			if checkBoxes[i].isChecked():
				self.dataObject_list[i].pushData(item)

	def clearPlot(self, index=None):
		if index == None:
			if self.groupBox_liveUpdate.isChecked():
				for i, ckbox in enumerate(self.plot_ckboxes):
					if ckbox.isChecked():
						self.dataObject_list[i].showPlot()
					else:
						self.dataObject_list[i].hidePlot()
			else:
				for i, ckbox in enumerate(self.plot_ckboxes):
					self.dataObject_list[i].hidePlot()
		else:
			if self.plot_ckboxes[index].isChecked():
				self.dataObject_list[index].showPlot()
			else:
				self.dataObject_list[index].hidePlot()

	def __del__(self):
		# make sure serial is closed.
		self.serialreader.stopRunning()
		self.thread.quit()
		if self.logfileh:
			self.logfileh.close()
			self.logfileh = None
		#super(MainWindow, self).__del__(parent)

	def closeEvent(self, event):
		pass

if __name__ == '__main__':
	app = QtGui.QApplication(sys.argv)
	form = MainWindow()
	form.show()
	app.exec_()
