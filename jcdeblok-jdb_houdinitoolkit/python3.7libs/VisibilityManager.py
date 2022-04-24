
######################################################################### 
#  VisibilityManager
#  Jonathan de Blok - jonathan@jdbgraphics.nl  
#########################################################################

import hou

from PySide2 import QtCore, QtGui, QtWidgets

def Enum(**enums):
    return type('Enum', (), enums)

uiscale = hou.ui.globalScaleFactor()


    
#main panel     
class QuickSwitch(QtWidgets.QWidget):
    
    
    #constructior
    def __init__(self, paneTab):
        self.qw=QtWidgets.QWidget.__init__(self)
        self.paneTab = paneTab
        self.buttons=[]
        self.toggles=[]
        self.root=[]
        
        self.update()
        self.peekBuf=[]
        
    def getContext(self):
        context=[]
        if len(hou.selectedNodes())>0:
            context=hou.selectedNodes()[0].parent().children()
        else:
            i=0
            main=None
            cursize=0
            while hou.ui.paneTabOfType(hou.paneTabType.NetworkEditor,i):
                pane =  hou.ui.paneTabOfType(hou.paneTabType.NetworkEditor,i)
                
                if pane.isCurrentTab():
                    if pane.size()[0]*pane.size()[1]>cursize:
                        cursize=pane.size()[0]*pane.size()[1]
                        main=pane
                i=i+1
            if main:
                context=main.pwd().children()            
        
        return context    
    
        
    def update(self,f=0):
                
        self.setStyleSheet("QPushButton {padding: "+str(4*uiscale)+"px; }")
           
        self.toggles.append(QtWidgets.QPushButton(self))
        self.toggles[0].setText("Show All +")
        self.toggles[0].move(QtCore.QPoint(10*uiscale, 10*uiscale))
        self.toggles[0].setStyleSheet("QPushButton {height: "+str(19*uiscale)+"px; width: "+str(110*uiscale)+"px}")
        self.toggles[0].clicked.connect( self.showAll )   
        self.toggles[0].update()
        self.toggles[0].show()
        
        self.toggles.append(QtWidgets.QPushButton(self))
        self.toggles[1].setText("Hide All +")
        self.toggles[1].move(QtCore.QPoint(135*uiscale, 10*uiscale)) 
        self.toggles[1].setStyleSheet("QPushButton {height: "+str(19*uiscale)+"px; width: "+str(110*uiscale)+"px}")
        self.toggles[1].clicked.connect( self.hideAll )   
        self.toggles[1].show()
        
        self.toggles.append(QtWidgets.QPushButton(self))
        self.toggles[2].setText("Invert +")
        self.toggles[2].move(QtCore.QPoint(260*uiscale, 10*uiscale)) 
        self.toggles[2].setStyleSheet("QPushButton {height: "+str(19*uiscale)+"px; width: "+str(110*uiscale)+"px}")
        self.toggles[2].clicked.connect( self.invertAll )   
        self.toggles[2].show()
        
        
        
        self.toggles.append(QtWidgets.QPushButton(self))
        self.toggles[3].setText("Selected Only")
        self.toggles[3].move(QtCore.QPoint((10+250)*uiscale, 45*uiscale)) 
        self.toggles[3].setStyleSheet("QPushButton {height: "+str(19*uiscale)+"px; width: "+str(110*uiscale)+"px}")
        self.toggles[3].clicked.connect( self.showSel )   
        self.toggles[3].show()
        
        self.toggles.append(QtWidgets.QPushButton(self))
        self.toggles[4].setText("Hide Selected")
        self.toggles[4].move(QtCore.QPoint(135*uiscale, 45*uiscale) )
        self.toggles[4].setStyleSheet("QPushButton {height: "+str(19*uiscale)+"px; width: "+str(110*uiscale)+"px}")
        self.toggles[4].clicked.connect( self.hideSel )   
        self.toggles[4].show()
        
        self.toggles.append(QtWidgets.QPushButton(self))
        self.toggles[5].setText("Unhide Selected")
        self.toggles[5].move(QtCore.QPoint(10*uiscale, 45*uiscale) )
        self.toggles[5].setStyleSheet("QPushButton {height: "+str(19*uiscale)+"px; width: "+str(110*uiscale)+"px}")
        self.toggles[5].clicked.connect( self.unhideSel )   
        self.toggles[5].show()
        
        
        self.h=QtWidgets.QLabel(self)
        self.h.setText("+Shift: Includes Nulls     +Ctrl: Includes Non-Selectable")
        self.h.move(QtCore.QPoint(10*uiscale, 80*uiscale) )
        
        
        self.toggles.append(QtWidgets.QPushButton(self))
        self.toggles[6].setText("Select Down +")
        self.toggles[6].move(QtCore.QPoint(10*uiscale, 115*uiscale) )
        self.toggles[6].setStyleSheet("QPushButton {height: "+str(19*uiscale)+"px; width: "+str(110*uiscale)+"px}")
        self.toggles[6].clicked.connect( self.selDown )   
        self.toggles[6].show()
        
        self.toggles.append(QtWidgets.QPushButton(self))
        self.toggles[7].setText("Select Up +")
        self.toggles[7].move(QtCore.QPoint(135*uiscale, 115*uiscale) )
        self.toggles[7].setStyleSheet("QPushButton {height: "+str(19*uiscale)+"px; width: "+str(110*uiscale)+"px}")
        self.toggles[7].clicked.connect( self.selUp )   
        self.toggles[7].show()
       
        
        self.h=QtWidgets.QLabel(self)
        self.h.setText("+Shift: First/Last     +Ctrl: Up/Down Single    +Alt: Clear Current")
        self.h.move(QtCore.QPoint(10*uiscale, 148*uiscale) )
        
        
        self.toggles.append(QtWidgets.QPushButton(self))
        self.toggles[8].setText("Select Tree")
        self.toggles[8].move(QtCore.QPoint(260*uiscale, 115*uiscale) )
        self.toggles[8].setStyleSheet("QPushButton {height: "+str(19*uiscale)+"px; width: "+str(110*uiscale)+"px}")
        self.toggles[8].clicked.connect( self.selTree )   
        self.toggles[8].show()
    
        self.toggles.append(QtWidgets.QPushButton(self))
        self.toggles[9].setText("Select Invisible")
        self.toggles[9].move(QtCore.QPoint(10*uiscale, 180*uiscale) )
        self.toggles[9].setStyleSheet("QPushButton {height: "+str(19*uiscale)+"px; width: "+str(110*uiscale)+"px}")
        self.toggles[9].clicked.connect( self.selInvisble )   
        self.toggles[9].show()
        
        
        self.toggles.append(QtWidgets.QPushButton(self))
        self.toggles[10].setText("Select Non-Sel.")
        self.toggles[10].move(QtCore.QPoint(135*uiscale, 180*uiscale) )
        self.toggles[10].setStyleSheet("QPushButton {height: "+str(19*uiscale)+"px; width: "+str(110*uiscale)+"px}")
        self.toggles[10].clicked.connect( self.selNonselectable )   
        self.toggles[10].show()
        
        
        self.toggles.append(QtWidgets.QPushButton(self))
        self.toggles[11].setText("Sel. Same Color")
        self.toggles[11].move(QtCore.QPoint(260*uiscale, 180*uiscale) )
        self.toggles[11].setStyleSheet("QPushButton {height: "+str(19*uiscale)+"px; width: "+str(110*uiscale)+"px}")
        self.toggles[11].clicked.connect( self.selSameColor )   
        self.toggles[11].show()
        
        self.toggles.append(QtWidgets.QPushButton(self))
        self.toggles[12].setText("Peek")
        self.toggles[12].move(QtCore.QPoint(10*uiscale, 220*uiscale) )
        self.toggles[12].setStyleSheet("QPushButton {height: "+str(19*uiscale)+"px; width: "+str(110*uiscale)+"px}")
        self.toggles[12].pressed.connect( self.peekStart )   
        self.toggles[12].released.connect( self.peekEnd )   
        self.toggles[12].show()

        self.toggles.append(QtWidgets.QPushButton(self))
        self.toggles[13].setText("FilterTime Depend")
        self.toggles[13].move(QtCore.QPoint(135*uiscale, 220*uiscale) )
        self.toggles[13].setStyleSheet("QPushButton {height: "+str(19*uiscale)+"px; width: "+str(110*uiscale)+"px}")
        self.toggles[13].clicked.connect( self.selectTD )   
  
        
        
        
        self.toggles[13].show()
    
        
    def peekStart(self):
        self.peekBuf=[]
        start=hou.selectedNodes()

        
        if  QtWidgets.QApplication.keyboardModifiers() != QtCore.Qt.AltModifier:
            items=self.getContext()
            for item in items:
                try:
                    self.peekBuf.append( [item, item.isDisplayFlagSet() ])
                    if not item in start:
                        item.setDisplayFlag(False)
                except:
                    pass
        else:
            for item in start:    
                try:
                    self.peekBuf.append( [item, item.isDisplayFlagSet() ])
                    item.setDisplayFlag(False)
                except:
                    pass    
  
    def selectTD(self):
       
        sel=hou.selectedNodes()
        for item in sel:
            if not item.isTimeDependent():
                item.setSelected(False) 
        
    def peekEnd(self):
        for item in self.peekBuf:
            item[0].setDisplayFlag(item[1])    
    
        
        
    def selTree(self):
        with hou.undos.group("Select Tree"): 
            check=len(hou.selectedNodes())
            check2=0  
            while check!=check2:
                check2=check
                self.doSelUp()
                self.doSelDown()
                check=len(hou.selectedNodes())
            
    
    def selUp(self):
        with hou.undos.group("Select Up"): 
            self.doSelUp()
        
    def selDown(self):
        with hou.undos.group("Select Down"): 
            self.doSelDown()

        
    def doSelUp(self):
        start=hou.selectedNodes()
        if  QtWidgets.QApplication.keyboardModifiers() == QtCore.Qt.ControlModifier:
            hou.clearAllSelected()
        
        for node in start:
            n=node
            
            if  QtWidgets.QApplication.keyboardModifiers() == QtCore.Qt.ShiftModifier:
                while len(n.inputs())>0:
                    n=n.inputs()[0]
                    if len(n.inputs())==0:
                        n.setSelected(True, clear_all_selected=False)    
            
            elif  QtWidgets.QApplication.keyboardModifiers() == QtCore.Qt.ControlModifier:
                n=node.inputs()[0]
                if n:
                    n.setSelected(True, clear_all_selected=False)         
            
            elif  QtWidgets.QApplication.keyboardModifiers() == QtCore.Qt.AltModifier:                    
                while len(n.inputs())>0:
                    n=n.inputs()[0]
                    n.setSelected(True, clear_all_selected=False)
            
                node.setSelected(False,  clear_all_selected=False)   
            else:    
                while len(n.inputs())>0:
                    n=n.inputs()[0]
                    n.setSelected(True, clear_all_selected=False)
                
            
        

    def doSelDown(self):

        start=hou.selectedNodes()
        hou.clearAllSelected()
        
        def getInputs(node):
            for x in node.outputs():
                getInputs(x)
                x.setSelected(True, clear_all_selected=False)
                
        def getLastInputs(node):
            for x in node.outputs():
                getLastInputs(x)
                if len(x.outputs())==0:
                    x.setSelected(True, clear_all_selected=False)        
        
        for n in start:
            node= n 
            if  QtWidgets.QApplication.keyboardModifiers() == QtCore.Qt.ControlModifier:

                for tmp in n.outputs():
                    tmp.setSelected(True, clear_all_selected=False)
           
            elif  QtWidgets.QApplication.keyboardModifiers() == QtCore.Qt.ShiftModifier:

                n.setSelected(False, clear_all_selected=True)
                getLastInputs(n)
    
                    
                    
            elif  QtWidgets.QApplication.keyboardModifiers() == QtCore.Qt.AltModifier:

                n.setSelected(True, clear_all_selected=False)
                getInputs(n)
                
                node.setSelected(False,  clear_all_selected=False)   
            else:
                n.setSelected(True, clear_all_selected=False)
                getInputs(n)
    
            
    
    def selNonselectable(self):
        items=self.getContext()
        
        hou.clearAllSelected()
        for item in items:
            try:
                if not item.isSelectableInViewport():
                    item.setSelected(True, clear_all_selected=False)
            except:
                pass


    def selNonselectable(self):
        items=self.getContext()
        
        hou.clearAllSelected()
        for item in items:
            try:
                if not item.isSelectableInViewport():
                    item.setSelected(True, clear_all_selected=False)
            except:
                pass

    def selSameColor(self):                
    
        start=hou.selectedNodes()
        items=self.getContext()
        hou.clearAllSelected()
        
        for src in start:
            for item in items:
                try:
                    if item.color()==src.color():
                        item.setSelected(True, clear_all_selected=False)
                except:
                    pass
                
    def selInvisble(self):
        items=self.getContext()
        hou.clearAllSelected()
        for item in items:
            try:
                if not item.isDisplayFlagSet():
                    item.setSelected(True, clear_all_selected=False)
            except:
                pass
            
            
    def showAll(self):
        with hou.undos.group("Show All"):    
            for item in self.getContext():
                try:
                
                    if item.isSelectableInViewport() or  QtWidgets.QApplication.keyboardModifiers() == QtCore.Qt.ControlModifier:
                        if item.type().name()!="null" or QtWidgets.QApplication.keyboardModifiers() == QtCore.Qt.ShiftModifier:
                            item.setDisplayFlag(True)
                except:
                    pass
            
            
    def hideAll(self):
        with hou.undos.group("Hide All"): 
            for item in self.getContext():
                try:
                
                    if item.isSelectableInViewport() or  QtWidgets.QApplication.keyboardModifiers() == QtCore.Qt.ControlModifier:
                        if item.type().name()!="null" or QtWidgets.QApplication.keyboardModifiers() == QtCore.Qt.ShiftModifier:
                            item.setDisplayFlag(False)
                except:
                    pass

            
    def showSel(self):
        with hou.undos.group("Show Selected"): 
            self.hideAll()
            for item in hou.selectedNodes():
                item.setDisplayFlag(True)         
                 
    def hideSel(self):
        with hou.undos.group("Hide Selected"):
            for item in hou.selectedNodes():
                item.setDisplayFlag(False)
             
                  
    def unhideSel(self):
        with hou.undos.group("Unhide Selected"):
            for item in hou.selectedNodes():
                item.setDisplayFlag(True)       
          
                         
    def invertAll(self):
        with hou.undos.group("Invert Selection"):
            for item in self.getContext():
                try:
                
                    if item.isSelectableInViewport() or  QtWidgets.QApplication.keyboardModifiers() == QtCore.Qt.ControlModifier:
                        if item.type().name()!="null" or QtWidgets.QApplication.keyboardModifiers() == QtCore.Qt.ShiftModifier:
                            item.setDisplayFlag(not item.isDisplayFlagSet())
                except:
                    pass
                    
                
    def paintEvent(self, event):
        painter = QtGui.QPainter(self).fillRect(0, 0, self.width(), self.height(), hou.qt.getColor("BackColor"))
       
     
      
  
    