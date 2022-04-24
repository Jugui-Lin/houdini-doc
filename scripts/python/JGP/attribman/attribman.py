import hou

from hutil.Qt import QtCore,QtWidgets,QtUiTools

class AttribManager(QtWidgets.QWidget):
    def __init__(self):
        QtWidgets.QWidget.__init__(self)

        print('Hey I am a class!!!')


def show():
    AttribManager()




print('hello from the package') 