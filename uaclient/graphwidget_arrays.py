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

class GraphArraysUI(object):
    """
    A widget to handle plotting of array-valued variables.
    """

    colorCycle = ['#4e9a06ff', '#ce5c00ff', '#3465a4ff',
                  '#75507bff', '#cc0000ff', '#edd400ff']

    def __init__(self, window, uaclient):
        """
        :param window: reference to the MainWindow or a parent widget
        :param uaclient: reference to the OPC UA client
        """
        self.window = window
        self.uaclient = uaclient

        # If pyqtgraph or numpy isn't available, bail out
        if not use_graph:
            self.window.ui.graphArraysLayout.addWidget(
                QLabel("pyqtgraph or numpy not installed")
            )
            return

        # Keep track of array nodes and their curves
        self._node_list = []
        self._curves = []

        # Create the PlotWidget
        self.pw = pg.PlotWidget(name='PlotArrays')
        self.pw.showGrid(x=True, y=True, alpha=0.3)
        self.legend = self.pw.addLegend()
        self.window.ui.graphArraysLayout.addWidget(self.pw)

        # (Optional) If you want a timer that re-reads the values periodically:
        self.timer = QTimer()
        self.timer.setInterval(1000)  # e.g. 1 second
        self.timer.timeout.connect(self.update_plot)
        self.timer.start()

    @trycatchslot
    def add_node(self, node=None):
        """Add the given node to the array plot if it really has array data."""
        if not isinstance(node, SyncNode):
            # If caller didn’t pass a node, get whichever is selected
            node = self.window.get_current_node()
            if node is None:
                return

        # Don’t add duplicates
        if node in self._node_list:
            logger.info("Array node is already being plotted: %s", node)
            return

        try:
            value = node.get_value()
            if isinstance(value, (list, tuple)) or (use_graph and isinstance(value, np.ndarray)):
                display_name = node.read_display_name().Text
                self._node_list.append(node)

                # Choose a pen color from the cycle
                colorIndex = len(self._node_list) % len(self.colorCycle)
                curve = self.pw.plot(
                    pen=pg.mkPen(color=self.colorCycle[colorIndex],
                                 width=3,
                                 style=Qt.SolidLine),
                    name=display_name
                )
                self._curves.append(curve)

                logger.info("Array node '%s' added to array graph", display_name)
            else:
                logger.info("Node is not an array, ignoring.")
        except Exception as ex:
            logger.error("Error adding array node: %s", ex)

    @trycatchslot
    def remove_node(self, node=None):
        """Remove the given node from the array plot."""
        if not isinstance(node, SyncNode):
            node = self.window.get_current_node()
            if node is None:
                return

        if node in self._node_list:
            idx = self._node_list.index(node)
            self._node_list.pop(idx)
            display_name = node.read_display_name().Text

            # Remove from legend and from the plot
            self.legend.removeItem(display_name)
            self.pw.removeItem(self._curves[idx])
            self._curves.pop(idx)

            logger.info("Array node '%s' removed from array graph", display_name)

    def update_plot(self):
        """
        Periodically read each array node’s current value and update its curve.
        """
        for i, node in enumerate(self._node_list):
            try:
                value = node.get_value()
                # For safety, check if it's an array
                if isinstance(value, (list, tuple)) or (use_graph and isinstance(value, np.ndarray)):
                    # If it’s a python list, convert to numpy for convenience
                    if isinstance(value, list):
                        value = np.array(value)
                    x_data = np.arange(len(value))
                    self._curves[i].setData(x=x_data, y=value)
            except Exception as ex:
                logger.error("Error updating array node: %s", ex)

    def clear(self):
        """Clear all items if needed."""
        self.pw.clear()
        self._node_list.clear()
        self._curves.clear()
