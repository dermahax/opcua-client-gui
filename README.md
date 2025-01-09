
Forked from: https://github.com/FreeOpcUa/opcua-client-gui

* Modified such that the graph update rate can be set <= 1 Sec for better live visualizations.
* Added a graphArrays widget, that visualizes array nodes.


Simple OPC-UA GUI client.

[![Scrutinizer Code Quality](https://scrutinizer-ci.com/g/FreeOpcUa/opcua-client-gui/badges/quality-score.png?b=master)](https://scrutinizer-ci.com/g/FreeOpcUa/opcua-client-gui/?branch=master)
[![Build Status](https://travis-ci.org/FreeOpcUa/opcua-client-gui.svg?branch=master)](https://travis-ci.org/FreeOpcUa/opcua-client-gui)
[![Build Status](https://travis-ci.org/FreeOpcUa/opcua-widgets.svg?branch=master)](https://travis-ci.org/FreeOpcUa/opcua-widgets)

Written using freeopcua python api and pyqt. Most needed functionalities are implemented including subscribing for data changes and events, write variable values listing attributes and references, and call methods. PR are welcome for any whished improvments

It has also a contextual menu with a few usefull function like putting the mode id in clipboard or the entire browse path which can be used directly in you program: client.nodes.root.get_child(['0:Objects', '2:MyNode'])

![Screenshot](/screenshot.png?raw=true "Screenshot")

What works:
* connecting and disconnecting
* browsing with icons per node types
* showing attributes and references
* subscribing to variable
* available on pip: sudo pip install opcua-client
* remember connections and show connection history
* subscribing to events
* write variable node values
* gui for certificates
* gui for encryption 
* call methods
* plot method values
* remember last browsed path and restore state

TODO (listed after priority):

* detect lost connection and automatically reconnect 
* gui for loging with certificate or user/password (can currently be done by writting them in uri)
* Maybe read history
* Something else?

# How to Install  

*Note: PyQT 5 is required.*

  
### Windows:  

1. Clone the project
2. Create a virtual environment
3. Move to the project directory in your console/terminal
4. run *pip install .*



