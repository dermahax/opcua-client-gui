#! /usr/bin/env python3

import logging
from PyQt5.QtCore import QTimer, Qt
from PyQt5.QtWidgets import QLabel

from asyncua import ua
from asyncua.sync import SyncNode

from uawidgets.utils import trycatchslot

use_graph = True
try:
    import pyqtgraph as pg
    import numpy as np
except ImportError:
    print("pyqtgraph or numpy are not installed, use of graph feature disabled")
    use_graph = False

if use_graph:
    pg.setConfigOptions(antialias=True)
    pg.setConfigOption('background', 'w')
    pg.setConfigOption('foreground', 'k')

logger = logging.getLogger(__name__)


class GraphUI(object):

    # use tango color schema (public domain)
    colorCycle = ['#4e9a06ff', '#ce5c00ff', '#3465a4ff', '#75507bff', '#cc0000ff', '#edd400ff']
    acceptedDatatypes = ['Decimal128', 'Double', 'Float', 'Integer', 'UInteger']

    def __init__(self, window, uaclient, connect_actions=True):
        self.window = window
        self.uaclient = uaclient

        # exit if the modules are not present
        if not use_graph:
            self.window.ui.graphLayout.addWidget(QLabel("pyqtgraph or numpy not installed"))
            return
        self._node_list = []  # holds the nodes to poll
        self._channels = []  # holds the actual data
        self._curves = []  # holds the curve objects
        self.pw = pg.PlotWidget(name='Plot1')
        self.pw.showGrid(x=True, y=True, alpha=0.3)
        self.legend = self.pw.addLegend()
        self.window.ui.graphLayout.addWidget(self.pw)

        if connect_actions:
            self.window.ui.actionAddToGraph.triggered.connect(self._add_node_to_channel)
            self.window.ui.actionRemoveFromGraph.triggered.connect(self._remove_node_from_channel)

            # populate contextual menu
            self.window.ui.treeView.addAction(self.window.ui.actionAddToGraph)
            self.window.ui.treeView.addAction(self.window.ui.actionRemoveFromGraph)

        # connect Apply button
        self.window.ui.buttonApply.clicked.connect(self.restartTimer)
        self.restartTimer()

    def restartTimer(self):
        # stop current timer, if it exists
        if hasattr(self, 'timer') and self.timer.isActive():
            self.timer.stop()

        # define the number of polls displayed in graph
        self.N = self.window.ui.spinBoxNumberOfPoints.value()
        self.ts = np.arange(self.N)
        # define the poll intervall
        self.intervall = self.window.ui.spinBoxIntervall.value() 

        # overwrite current channel buffers with zeros of current length and add to curves again
        for i, channel in enumerate(self._channels):
            self._channels[i] = np.zeros(self.N)
            self._curves[i].setData(self._channels[i])

        # starting new timer
        self.timer = QTimer()
        self.timer.setInterval(self.intervall)
        self.timer.timeout.connect(self.pushtoGraph)
        self.timer.start()

    @trycatchslot
    def _add_node_to_channel(self, node=None):
        if not isinstance(node, SyncNode):
            node = self.window.get_current_node()
            if node is None:
                return
        if node not in self._node_list:
            dtype = node.read_attribute(ua.AttributeIds.DataType)

            dtypeStr = ua.ObjectIdNames[dtype.Value.Value.Identifier]

            if dtypeStr in self.acceptedDatatypes and not isinstance(node.get_value(), list):
                self._node_list.append(node)
                displayName = node.read_display_name().Text
                colorIndex = len(self._node_list) % len(self.colorCycle)
                self._curves.append \
                    (self.pw.plot(pen=pg.mkPen(color=self.colorCycle[colorIndex], width=3, style=Qt.SolidLine), name=displayName))
                # set initial data to zero
                self._channels.append(np.zeros(self.N))  # init data sequence with zeros
                # add the new channel data to the new curve
                self._curves[-1].setData(self._channels[-1])
                logger.info("Variable %s added to graph", displayName)

            else:
                logger.info("Variable cannot be added to graph because it is of type %s or an array", dtypeStr)

    @trycatchslot
    def _remove_node_from_channel(self, node=None):
        if not isinstance(node, SyncNode):
            node = self.window.get_current_node()
            if node is None:
                return
        if node in self._node_list:
            idx = self._node_list.index(node)
            self._node_list.pop(idx)
            displayName = node.read_display_name().Text
            self.legend.removeItem(displayName)
            self.pw.removeItem(self._curves[idx])
            self._curves.pop(idx)
            self._channels.pop(idx)

    def pushtoGraph(self):
        # ringbuffer: shift and replace last
        for i, node in enumerate(self._node_list):
            self._channels[i] = np.roll(self._channels[i], -1)  # shift elements to the left by one
            self._channels[i][-1] = float(node.get_value())
            self._curves[i].setData(self.ts, self._channels[i])

    def clear(self):
        pass

    def show_error(self, *args):
        self.window.show_error(*args)



# New: GraphArraysUI for handling array data
class GraphArraysUI(GraphUI):
    """
    Inherits from GraphUI but overrides:
      - __init__ to place the PlotWidget in graphArraysLayout
      - connections to actionAddToGraphArrays / actionRemoveFromGraphArrays
      - _add_node_to_channel to accept array data
      - pushtoGraph to update array data properly
    """

    def __init__(self, window, uaclient):
        # Call parent constructor
        super().__init__(window, uaclient, connect_actions=False)

        # 1) Remove the PlotWidget from the old layout (graphLayout)
        #    and re-add it to the array graph layout
        self.window.ui.graphLayout.removeWidget(self.pw)
        self.window.ui.graphArraysLayout.addWidget(self.pw)

        # 2) Connect our new array actions
        self.window.ui.actionAddToGraphArrays.triggered.connect(self._add_node_to_channel)
        self.window.ui.actionRemoveFromGraphArrays.triggered.connect(self._remove_node_from_channel)

        # 3) Add them to the treeView context menu
        self.window.ui.treeView.addAction(self.window.ui.actionAddToGraphArrays)
        self.window.ui.treeView.addAction(self.window.ui.actionRemoveFromGraphArrays)

        # You may want a different default timer interval for arrays,
        # or keep parent’s restartTimer behavior. Example:
        self.restartTimer()

    @trycatchslot
    def _add_node_to_channel(self, node=None):
        """
        Overrides the parent's method to accept array data.
        We'll store the full array in _channels[i] and just plot it directly
        (not ring-buffer style, unless you want to store multiple 'frames').
        """
        if not isinstance(node, SyncNode):
            node = self.window.get_current_node()
            if node is None:
                return

        # If node is already in the list, do nothing
        if node in self._node_list:
            logger.info("Node already added to arrays graph.")
            return

        try:
            value = node.get_value()
            # Check if it's an array
            if isinstance(value, (list, tuple)) or (use_graph and isinstance(value, np.ndarray)):
                self._node_list.append(node)
                displayName = node.read_display_name().Text
                colorIndex = len(self._node_list) % len(self.colorCycle)
                pen = pg.mkPen(color=self.colorCycle[colorIndex], width=3, style=Qt.SolidLine)
                new_curve = self.pw.plot(name=displayName, pen=pen)
                self._curves.append(new_curve)

                # Store the array data in _channels (for consistency)
                # This could be a list or np.array; here we store the last known array
                arr_data = np.array(value) if isinstance(value, list) else value
                self._channels.append(arr_data)

                # Plot immediately
                x_vals = np.arange(len(arr_data))
                new_curve.setData(x_vals, arr_data)

                logger.info("Array variable %s added to arrays graph", displayName)
            else:
                logger.info("Node value is not an array—cannot add to arrays graph.")
        except Exception as ex:
            logger.error("Error reading node value: %s", ex)

    def pushtoGraph(self):
        """
        Instead of ring-buffering, re-read each array node's value
        and plot the full array each time.
        """
        for i, node in enumerate(self._node_list):
            try:
                value = node.get_value()
                if isinstance(value, (list, tuple)) or (use_graph and isinstance(value, np.ndarray)):
                    arr_data = np.array(value) if isinstance(value, list) else value
                    self._channels[i] = arr_data

                    x_vals = np.arange(len(arr_data))
                    self._curves[i].setData(x_vals, arr_data)
                else:
                    # If it's no longer an array, skip or log
                    logger.debug("Node %s no longer returning array data", node)
            except Exception as ex:
                logger.error("Error updating array graph for node %s: %s", node, ex)