######################################################################## 
#  ProBezierAssist for Houdini
#  Jonathan de Blok - jonathan@jdbgraphics.nl 
########################################################################
 
import math
import hou
import math
import toolutils
from PySide2 import QtCore, QtGui, QtWidgets
import random
  
uiscale = hou.ui.globalScaleFactor()
 
class Slider(QtWidgets.QSlider):
    green=50
    red=100
    oldVal=0;
    hasInfluence=False
    parmTarget = "undoCBx";
    uiscale = hou.ui.globalScaleFactor()
    snap=[]

    def setSnap(self, data):
        self.snap=data
        
    def __init__(self, *args, **kwargs):
        super(Slider, self).__init__(*args, **kwargs)
        self.updateCSS()
    
    def setInfluence(self, val):
        if self.hasInfluence!=val:
            self.hasInfluence  = val
            self.updateCSS()

 

    def updateCSS(self):    
        uiscale = hou.ui.globalScaleFactor()
        
        
        
        
        self.css='QSlider {   width: '+str(int(320*uiscale))+'px;  padding: 0px; height '+str(int(20*uiscale))+'px;  min-height '+str(int(20*uiscale))+'px; max-height: '+str(int(20*uiscale))+'px} '
        self.css += 'QSlider::handle:horizontal  { background-color: #888; margin: -'+str(int(8*uiscale))+'px 0px; width: '+str(int(4*uiscale))+'px; border-left: '+str(int(uiscale))+'px solid #bbb; border-top: '+str(int(uiscale))+'px solid #bbb;  } '
        
        self.css += 'QSlider {height: '+str(int(20*uiscale))+'px; min-height: '+str(int(20*uiscale))+'px; max-heiht: '+str(int(20*uiscale))+'px}' 
        
        
        if self.value()>self.red:
            self.css += 'QSlider:sub-page {  height:  '+str(int(uiscale))+'px; background-color: #800;} '
            
        if self.value()==self.green:   
            self.css += 'QSlider:sub-page {  height:  '+str(int(uiscale))+'px; background-color: #080;} '
        
        if self.hasInfluence:       
            self.css += 'QSlider:sub-page {  height:  '+str(int(uiscale))+'px; background-color: #555;} '

        self.setStyleSheet(self.css )
 
    
    def updateValue(self, val, store=True):
        if self.value()!=val:
            if  QtWidgets.QApplication.keyboardModifiers() == QtCore.Qt.ShiftModifier:
                for sp in self.snap:
                    if abs(sp-val)< (self.maximum() - self.minimum())/20 :
                        val=sp
        
            self.setValue(val)
            
            
            
            self.updateCSS()
            #self.parent().updateSliderColors()
            #hou.node("/obj").parm(self.parmTarget).set(val)


        if store:
            self.__doCB=True
        
            
    def mousePressEvent(self, event):
        if event.button() == QtCore.Qt.LeftButton:
            with hou.undos.disabler():
                self.oldVal = self.value()
                val = self.pixelPosToRangeValue(event.pos())
                self.updateValue(val)
                self.parent().updateKeyframes(self.parent().getKeyframes(), self.parent().getUiValues())
    
    def mouseReleaseEvent(self, event):
            
        val=self.value()
            
        with hou.undos.disabler():
            self.updateValue(self.oldVal)
            self.parent().updateKeyframes(self.parent().getKeyframes(), self.parent().getUiValues())
            
        with hou.undos.group("Undo PBA adjustment"):
            self.updateValue(val)
            self.parent().updateKeyframes(self.parent().getKeyframes(), self.parent().getUiValues())
            self.parent().primeUndo() 
        self.update()
        self.parent().update()

                  
    def mouseMoveEvent(self, event):
        with hou.undos.disabler():
            val = self.pixelPosToRangeValue(event.pos())
            if self.value()!=val:
                self.updateValue(val)     
                
                self.parent().updateKeyframes(self.parent().getKeyframes(), self.parent().getUiValues())
                
                #self.updateCSS()

    def pixelPosToRangeValue(self, pos):
        opt = QtWidgets.QStyleOptionSlider()
        self.initStyleOption(opt)
        gr = self.style().subControlRect(QtWidgets.QStyle.CC_Slider, opt, QtWidgets.QStyle.SC_SliderGroove, self)
        sr = self.style().subControlRect(QtWidgets.QStyle.CC_Slider, opt, QtWidgets.QStyle.SC_SliderHandle, self)

        sliderLength = sr.width()
        sliderMin = gr.x()
        sliderMax = gr.right() - sliderLength + 1
    
        pr = pos - sr.center() + sr.topLeft()
        p = pr.x() 
        
        return QtWidgets.QStyle.sliderValueFromPosition(self.minimum(), self.maximum(), p - sliderMin, sliderMax - sliderMin, opt.upsideDown)
                                              
class PbaPanel(QtWidgets.QWidget):

    __store= {}
    __doCB=True
    
    #constructior
    def __init__(self, paneTab):
        QtWidgets.QWidget.__init__(self)
        self.paneTab = paneTab
        #self.paneTab = paneTab
        self.setup()
        
    def setup(self):
 
        uiscale = hou.ui.globalScaleFactor()
        node = hou.node("/obj")
        with hou.undos.disabler():
            if node.parm("undoCBx")!=None:
                parm_group = node.parmTemplateGroup()
                parm_group.remove("undoCB")
                
                node.setParmTemplateGroup(parm_group)
                
            
            parm_group = node.parmTemplateGroup()
            parm_group.addParmTemplate(hou.FloatParmTemplate("undoCB", "undoCB", 4))
            node.setParmTemplateGroup(parm_group)
            
        px=15*uiscale
        py=45*uiscale
        self.pstore=[]
        self.slider_ease = Slider( QtCore.Qt.Horizontal, self)
        self.slider_ease.setSnap([50,100])
        self.slider_ease.setFocusPolicy(QtCore.Qt.StrongFocus)
        self.slider_ease.setTickPosition(QtWidgets.QSlider.TicksBothSides)
        self.slider_ease.setTickInterval(0.1)
        self.slider_ease.setSingleStep(1)
        self.slider_ease.setMinimum(0)
        self.slider_ease.setMaximum(150)
        self.slider_ease.setSingleStep(1)
        self.slider_ease.setProperty("value", 75)
        self.slider_ease.setAttribute(QtCore.Qt.WA_StyledBackground) 
        self.slider_ease.green=-1
        self.slider_ease.red=100
        self.slider_ease.parmTarget ="undoCBx"
        hou.node("/obj").parm(self.slider_ease.parmTarget).set(self.slider_ease.value())
        

        self.slider_bias = Slider( QtCore.Qt.Horizontal, self)
        self.slider_bias.setFocusPolicy(QtCore.Qt.StrongFocus)
        self.slider_bias.setTickPosition(QtWidgets.QSlider.TicksBothSides)
        self.slider_bias.setTickInterval(0.1)
        self.slider_bias.setSingleStep(1)
        self.slider_bias.setMinimum(0)
        self.slider_bias.setMaximum(100)
        self.slider_bias.setSnap([50])
        self.slider_bias.setSingleStep(1)
        self.slider_bias.setProperty("value", 50)
        self.slider_bias.green=50
        self.slider_bias.red=101
        self.slider_bias.updateCSS()
        self.slider_bias.parmTarget ="undoCBy"
        hou.node("/obj").parm(self.slider_bias.parmTarget).set(self.slider_bias.value())
        
        self.slider_relax = Slider( QtCore.Qt.Horizontal, self)
        self.slider_relax.setFocusPolicy(QtCore.Qt.StrongFocus)
        self.slider_relax.setTickPosition(QtWidgets.QSlider.TicksBothSides)
        self.slider_relax.setTickInterval(0.1)
        self.slider_relax.setSingleStep(1)
        self.slider_relax.setMinimum(0)
        self.slider_relax.setMaximum(200)
        self.slider_relax.setSnap([50,100,150])
         
        self.slider_relax.setSingleStep(1)
        self.slider_relax.setProperty("value", 0)
        self.slider_relax.green=-1
        self.slider_relax.red=1000
        self.slider_relax.parmTarget ="undoCBz"
        hou.node("/obj").parm(self.slider_relax.parmTarget).set(self.slider_relax.value())
 
        self.slider_apex = Slider( QtCore.Qt.Horizontal, self)
        self.slider_apex.setFocusPolicy(QtCore.Qt.StrongFocus)
        self.slider_apex.setTickPosition(QtWidgets.QSlider.TicksBothSides)
        self.slider_apex.setTickInterval(0.1)
        self.slider_apex.setSingleStep(1)
        self.slider_apex.setMinimum(0)
        self.slider_apex.setMaximum(100)
        self.slider_apex.setSnap([25,50,75])
        self.slider_apex.setSingleStep(1)
        self.slider_apex.setProperty("value", 50)
        self.slider_apex.green=50
        self.slider_apex.red=101
        self.slider_apex.updateCSS()
        self.slider_apex.parmTarget ="undoCBw"
        hou.node("/obj").parm(self.slider_apex.parmTarget).set(self.slider_apex.value())
            
        self.slider_ease.move(QtCore.QPoint(px+50*uiscale,py))
        self.slider_bias.move(QtCore.QPoint(px+50*uiscale,py+25*uiscale))        
        self.slider_relax.move(QtCore.QPoint(px+50*uiscale,py+50*uiscale))
        self.slider_apex.move(QtCore.QPoint(px+50*uiscale,py+75*uiscale))
        
        self.lab1 = QtWidgets.QLabel('Linear', self)
        self.lab1.move(QtCore.QPoint(px,py))
        self.lab2 = QtWidgets.QLabel('Easing', self)
        self.lab2.move(QtCore.QPoint(px+385*uiscale,py))
        
        self.lab1 = QtWidgets.QLabel('Ease In', self)
        self.lab1.move(QtCore.QPoint(px,py+25*uiscale))
        self.lab2 = QtWidgets.QLabel('Ease Out', self)
        self.lab2.move(QtCore.QPoint(px+385*uiscale,py+25*uiscale))
        
        self.lab1 = QtWidgets.QLabel('Sharp', self)
        self.lab1.move(QtCore.QPoint(px,py+50*uiscale))
        self.lab2 = QtWidgets.QLabel('Round', self)
        self.lab2.move(QtCore.QPoint(px+385*uiscale,py+50*uiscale))

        self.lab1 = QtWidgets.QLabel('Apex In', self)
        self.lab1.move(QtCore.QPoint(px,py+75*uiscale))
        self.lab2 = QtWidgets.QLabel('Apex Out', self)
        self.lab2.move(QtCore.QPoint(px+385*uiscale,py+75*uiscale))
         
        self.but_approx = QtWidgets.QPushButton(  self)
        self.but_approx.setText('Get Current')
        self.but_approx.move(QtCore.QPoint(10*uiscale,10*uiscale))
        self.setStyleSheet("QPushButton {padding: "+self.sizeToPx(3)+" "+self.sizeToPx(15)+"; }")
        self.but_approx.clicked.connect(self.reverse)
         
        self.but_preset = hou.qt.ComboBox()
        self.but_preset.setParent(self)
        self.but_preset.move(QtCore.QPoint(281*uiscale,10*uiscale))
        self.but_preset.addItems(["Presets", "Default", "Ease out", "Ease in", "Straight", "Smooth"])
        self.but_preset.setStyleSheet("ComboBox {padding: "+self.sizeToPx(2)+" "+self.sizeToPx(8)+";   width: "+str(43*uiscale)+"px; }")
        self.but_preset.activated.connect(self.preset)

        self.but_ext = hou.qt.ComboBox()
        self.but_ext.setParent(self)
        self.but_ext.move(QtCore.QPoint(370*uiscale,10*uiscale))
        self.but_ext.addItems(["Set Ext", "Default", "Hold", "Cycle", "Extend", "Slope", "CycleOffset", "Oscillate"])
        self.but_ext.setStyleSheet("QComboBox {padding: "+self.sizeToPx(2)+" "+self.sizeToPx(8)+"; width: "+self.sizeToPx(45)+"}")
        self.but_ext.activated.connect(self.setExt)
        
        self.but_source = hou.qt.ComboBox()
        self.but_source.setParent(self)
        self.but_source.move(QtCore.QPoint(115*uiscale,10*uiscale))
        self.but_source.addItems(["AnimEditor Selection", "Playbar Selection", "Lock Selection"])
        self.but_source.setStyleSheet("QComboBox {padding: "+self.sizeToPx(2)+" "+self.sizeToPx(8)+"; width: "+self.sizeToPx(120)+"}")
        self.but_source.activated.connect(self.openAE)
        
        self.but_apply= QtWidgets.QPushButton(  self)
        self.but_apply.setText('Apply')
        self.but_apply.move(QtCore.QPoint(10*uiscale,150*uiscale))
        self.but_apply.clicked.connect(self.Apply)
        
        self.but_shift= QtWidgets.QPushButton(  self)
        self.but_shift.setText('Normalize')
        self.but_shift.move(QtCore.QPoint(110*uiscale,150*uiscale))
        self.but_shift.clicked.connect(self.MakeNormalize)
        
        
        self.but_shift= QtWidgets.QPushButton(  self)
        self.but_shift.setText('Shift -')
        self.but_shift.move(QtCore.QPoint(225*uiscale,150*uiscale))
        self.but_shift.clicked.connect(self.shiftm)

        self.but_shift2= QtWidgets.QPushButton(  self)
        self.but_shift2.setText('Shift +')
        self.but_shift2.move(QtCore.QPoint(292*uiscale,150*uiscale))
        self.but_shift2.clicked.connect(self.shiftp)

        self.but_shift2= QtWidgets.QPushButton(  self)
        self.but_shift2.setText('Shift ?')
        self.but_shift2.move(QtCore.QPoint(362*uiscale,150*uiscale))
        self.but_shift2.clicked.connect(self.shiftr)
        
        #self.but_shift2.setStyleSheet("QPushButton {height: "+self.sizeToPx(19)+"};  QLabel, QComboBox, QPushButton { color: #bababa; font-size: "+self.sizeToPx(13)+"; height: "+self.sizeToPx(17)+"}  " )
  
 
        
        self.updateSliderColors()
   
    def Apply(self):
        with hou.undos.group("Undo PBA adjustment"):
            self.updateKeyframes(self.getKeyframes(), self.getUiValues())
            self.primeUndo() 

        
    def getFriends(self, kfs, frame):
       
        out=[]
        for item in kfs:
            if frame==item[1].frame() and not item in out:
                out.append(item)
 
        return out
    
        
    def MakeNormalize(self):
        with hou.undos.group("PBA Normalize velocity"):
            self.normalize()
  

        

    def shiftKey(self, parm, kf, frame):    
        fRangeStart=kf.frame();
        fRangeEnd=kf.frame();
        shift = frame - fRangeStart
        scr="chkeymv -r %s %s %s %s %s" %(parm.path(), fRangeStart, fRangeEnd, fRangeStart + shift, fRangeEnd + shift)
        hou.hscript( scr )
    
    def normalize(self):
    
        kfs=self.getKeyframes()
        
        ct=[]
        seg=[]
        translates=[]
        
        for item in kfs:
            
            kf=item[1]
            parm=item[0]
          
            tup = parm.tuple()
            if tup!=None:
                if tup.name()=='t' and tup not in translates:
                    translates.append(tup)
             
                if tup.name()=='t' and kf.frame() not in ct:
                    ct.append(kf.frame())
                        
        ct.sort()        
        
        for translate in translates:
            dist=0   
            t_delta=0
            pos=hou.Vector3(translate.evalAtFrame( int(ct[0]) ) )
            seg_d=[0.0]
            seg_t=[0.0]
            
            for i in range(int(ct[0]+1), int(ct[-1]+1)):
                cpos= hou.Vector3(translate.evalAtFrame(i))
                dist=dist +  cpos.distanceTo(pos)
                t_delta=t_delta+1.0
                pos=cpos
               
                if i in ct:
                    seg_d.append(dist)
                    seg_t.append(t_delta)
                   
                 
                    dist=0    
                    t_delta=0
            if sum(seg_t)==0:
                print("Can't normalize current keyframe selection")
                return False
                
            speed=(sum( seg_d)/ sum( seg_t))
            start=ct[0]
            
            for i in range(1,len(seg_d)-1):
            
                fac = ( seg_d[i] / seg_t[i]) / speed
                new_time = int((seg_t[i]*fac) + start)
                
            
                        
                part=translate[0]
                
                for item in self.getFriends(kfs,ct[i]):
                    parm=item[0]
                    kf=item[1]
              
                    old_time=kf.frame()
                    
                    if old_time!=new_time:
                         self.shiftKey(parm, kf, new_time)
                
                start=new_time
    
    
    def shift(self, amount, rnd=False):
    
    
        with hou.undos.group("Shift Keyframes"):
            keyframes=hou.playbar.selectedKeyframes()
            out=[]

            for parm in keyframes.keys():
                for keyframe in keyframes[parm]:
                    for hit in (x for x in parm.keyframes() if x.time() == keyframe.time()):
                        out.append( [parm.node().name(),hit,parm,type])
        
            out.sort(key = lambda x: x[0])
             
            i=0
            flip=1
            if len(out):
            
                amount=0.3
            
                start=out[0][0]
                for row in out:
                    if row[0]!=start:
                        start=row[0]
                        i=i+1
                        if rnd:
                            random.seed(row[2].path())
                            flip=(random.randint(0,1)*2)-1
                            i=amount
                    parm=row[2]
                    kf=row[1]
                    
                    new_time = kf.frame()+(i)*amount*flip
                 
                    self.shiftKey(parm, kf, new_time)
                
                
                
    def shiftp(self):
        self.shift(1 )
        
    def shiftm(self):
        self.shift(-1)
        
    def shiftr(self):
        self.shift(1, True)        
        
        
    def sizeToPx(self, val):
        
        return str(int(val*hou.ui.globalScaleFactor()))+"px"
    
    
    def openAE(self):
        if self.but_source.currentIndex()==0:
            channel_editor = hou.ui.paneTabOfType(hou.paneTabType.ChannelEditor)
            if channel_editor == None:
                channel_editor = hou.ui.curDesktop().createFloatingPaneTab(hou.paneTabType.ChannelEditor)
     
    
            
    def setExt(self):

        i=self.but_ext.currentIndex()-1
        if i==-1:
            return False
        
        enums=[hou.parmExtrapolate.Default , hou.parmExtrapolate.Hold , hou.parmExtrapolate.Cycle , hou.parmExtrapolate.Extend, hou.parmExtrapolate.Slope, hou.parmExtrapolate.CycleOffset, hou.parmExtrapolate.Oscillate ]
        keys=self.getKeyframes()
        with hou.undos.group("Undo PBA apply keframe extend"):
            for parm in keys:
                parm[0].setKeyframeExtrapolation(False, enums[i])
                parm[0].setKeyframeExtrapolation(True, enums[i])
              
            
            
    def preset(self):
  
        i=self.but_preset.currentIndex()-1
        if i==-1:
            return False
        p=[]
        p.append([75,50,0,50])
        p.append([95,95,0,50])
        p.append([95,5,0,50])
        p.append([0,50,0,50])
        p.append([80,50,75,50])

        with hou.undos.group("Undo PBA apply preset"):      
            self.slider_ease.updateValue(p[i][0])
            self.slider_bias.updateValue(p[i][1])
            self.slider_relax.updateValue(p[i][2])
            self.slider_apex.updateValue(p[i][3])
            self.updateKeyframes(self.getKeyframes(), self.getUiValues())
            self.primeUndo()
        
    def getKeyframes(self):

        keyframes=[]
         
        if self.but_source.currentIndex() == 0:
            channel_editor = hou.ui.paneTabOfType(hou.paneTabType.ChannelEditor)
            if channel_editor== None:
                return []
            keyframes = channel_editor.graph().selectedKeyframes()
            self.__store=keyframes
        
        if self.but_source.currentIndex() == 1:
            keyframes= hou.playbar.selectedKeyframes()
            self.__store=keyframes
            
        if self.but_source.currentIndex() == 2:
            keyframes=self.__store
            
        out=[]
        for parm in keyframes.keys():
            for keyframe in keyframes[parm]:
                for hit in (x for x in parm.keyframes() if x.time() == keyframe.time()):
                
                    type=1
                    
                    prevp=parm.keyframesBefore(keyframe.frame()-1)[-1:]
                    nextp=parm.keyframesAfter(keyframe.frame()+1)[:1]
                    
                    if len(prevp)==0:
                        type=0
                    
                    if len(nextp)==0:
                        type=2
                     
                    out.append([parm,hit,type])
                
        return out
    
    
    def reverse(self, calcOnly=False, kfs=None):
        
        Bias=0
        Ease=0
        Relax=0
        Apex=0
        
        k_dt1=[]
        k_dt2=[]
        k_dt3=[]
        
        k_dv1=[]
        k_dv2=[]
        k_dv3=[]
        
        dt1=1
        dt2=1
        dt3=2
        
        dv1=0
        dv2=0
        dv3=0
        
        cnt=0
        i=0
 
        keyframes=kfs
        
        if keyframes==None:
            keyframes = self.getKeyframes()
        
       
        if len(keyframes)==0:
            return False
            
        for data in keyframes:
            keyframe=data[1]
            parm=data[0]
            
            prevp=parm.keyframesBefore(keyframe.frame()-1)[-1:]
            nextp=parm.keyframesAfter(keyframe.frame()+1)[:1]
            
            if len(prevp)>0 and len(nextp)>0:
                prev=prevp[0]
                next=nextp[0]
        
                
                dt1= keyframe.time() - next.time()
                dt2= keyframe.time() - prev.time()
                dt3= prev.time() - next.time()
                
                dv1= keyframe.value() - next.value() * 1.0
                dv2= keyframe.value() - prev.value() * 1.0
                dv3= prev.value()- next.value() * 1.0
        
            #first    
            if len(prevp)==0 and len(nextp)>0 : 
                
                next=nextp[0]
            
                dt1= keyframe.time() - next.time()
                dt2= dt1* -1
                dt3= dt1 * 2.0
                
                dv1= keyframe.value() - next.value()  
                dv2= dv1*-1 
                dv3=  dv1 * 2.0
            #last
            if len(prevp)>0 and len(nextp)==0 : 
                
                prev=prevp[0]
            
                dt1= (keyframe.time() - prev.time())  * -1.0
                dt2= (keyframe.time() - prev.time()) * 1.0
                dt3=  dt1 * 2.0
                
                dv1= (keyframe.value() - prev.value()) * -1.0
                dv2=  keyframe.value() - prev.value() * 1.0
                dv3=  dv2 * 2.0
         
            k_dt1.append(dt1)
            k_dt2.append(dt2)
            k_dt3.append(dt3)
            
            k_dv1.append(dv1)
            k_dv2.append(dv2)
            k_dv3.append(dv3)
            
            a=max(0.1, keyframe.accel())
            A=a

            try:
                A=max(0.1, keyframe.inAccel())
            except:
                pass
                  
            s=keyframe.slope()
            try:
                s=( keyframe.slope() + keyframe.inSlope())/2
            except:
                pass
                
            t=dt1 * -1
            T=dt2 
            cnt=cnt+1
            
            t1 =  (100*A * t) / (T*a + A*t)
            t2 =   (100*(a*T+A*t)*math.sqrt(s*s+1))/(t*T*(s*s+1))
            
            Bias = Bias + t1
            Ease = Ease + t2
              
        if cnt>0:
            Bias=Bias/cnt
            Ease=Ease/cnt
         
        rng=range(50,51)
        for item in keyframes:
            if item[2]==1:
                rng= range(0,100,2)
                break
        
        best=-1     
        for R in range(0,100,2):
            for A in rng:
                error= 0  
                i=0
                for data in keyframes:
        
                    keyframe=data[1]
                    parm=data[0]
                    type=data[2]
                    
                    s=keyframe.slope()
                    try:
                        s=( keyframe.slope() + keyframe.inSlope())/2
                    except:
                        pass
                    
                    sl1= (k_dv1[i]/k_dt1[i]) * R / 100.0  
                    sl2= (k_dv2[i]/k_dt2[i]) * R / 100.0                   
                    sl= ((sl2 * A) + (sl1 * (100-A)))/100.0                    
                    error=error+ abs ( s - sl  ) 
                    i=i+1
                    
                if error<=best or best==-1:
                    Relax=R
                    Apex=A
                    best=error
        

        if calcOnly:
            
            return [Ease, Bias, Relax, Apex]
                    
        self.__doCB=False
        self.slider_ease.updateValue(Ease, False)
        self.slider_bias.updateValue(Bias,False)
        self.slider_relax.updateValue(Relax,False)
        self.slider_apex.updateValue(Apex,True)
    
        
    def getUiValues(self):
        out=[]
        out.append( self.slider_ease.value() )
        out.append( self.slider_bias.value() )
        out.append( self.slider_relax.value() )
        out.append( self.slider_apex.value() )
        
        return out;
     
    def updateKeyframes(self, keyframes, settings, alt=True):
     
    
        alt = QtWidgets.QApplication.keyboardModifiers() == QtCore.Qt.AltModifier
    
        #update slider colors
        ease=settings[0]
        bias=settings[1]
        relax=settings[2]
        apex=settings[3]
   
        self.updateSliderColors(keyframes)
   
        kf=[]

        for data in keyframes:
            keyframe=data[1]
            parm=data[0]
            
            if keyframe.expression()[:8]=="bezier()":
                keyframe.setSlopeAuto(False)
                keyframe.setInSlopeAuto(False)
    
                prevp=parm.keyframesBefore(keyframe.frame()-1)[-1:]
                nextp=parm.keyframesAfter(keyframe.frame()+1)[:1]
                
                dt1=0
                dt2=0
                dt3=0
                dv1=0
                dv2=0
                dv3=0
                
                ease=settings[0]
                bias=settings[1]
                relax=settings[2]
                apex=settings[3]
                
                if len(prevp)>0  or len(nextp)>0:
                    
                    if len(prevp)>0 and len(nextp)>0:
                        prev=prevp[0]
                        next=nextp[0]
                  
                        dt1= keyframe.time() - next.time()
                        dt2= keyframe.time() - prev.time()
                        dt3= prev.time() - next.time()
                        
                        dv1= keyframe.value() - next.value()  
                        dv2= keyframe.value() - prev.value()  
                        dv3= prev.value()- next.value()  
                    
                    boundry=False    

                    #first    
                    if len(prevp)==0 and len(nextp)>0 : 
                        boundry=True
                        next=nextp[0]
                    
                        dt1= keyframe.time() - next.time()
                        dt2= dt1 * -1.0
                        dt3= dt1 * 2.0
                        
                        dv1= keyframe.value() - next.value()  
                        dv2= dv1 * -1.0
                        dv3=  dv1 * 2.0
                        
                    #last
                    if len(prevp)>0 and len(nextp)==0 : 
                        boundry=True
                        prev=prevp[0]
                    
                        dt1= (keyframe.time() - prev.time()) *-1
                        dt2= keyframe.time() - prev.time() 
                        dt3=  dt1 * 2.0
                        
                        dv1= (keyframe.value() - prev.value()) *-1
                        dv2=  keyframe.value() - prev.value() 
                        dv3=  dv2 * 2.0
                    
                    relax_val = relax
                    if boundry and alt!=True:
                        relax_val = 0

                        
                    sl1= (dv1/dt1) * relax_val / 100.0  
                    sl2= (dv2/dt2) * relax_val / 100.0  
                    sl= ((sl2 * apex) + (sl1 * (100-apex )))/100 
                    keyframe.setSlope(sl)
                    
                    try:
                        if keyframe.inSlope()!=sl:
                            keyframe.setInSlope(sl)
                    except:
                        pass
                        
                    bias_val = (100.0-bias) / 100.0
                    ac1=  (ease * dt1) / -100.0  
                    ac2=  (ease * dt2) / 100.0  
                    keyframe.setAccel( max(0.01 , math.sqrt(math.pow(ac1,2.0) + math.pow(sl*ac1,2.0)) * bias_val ) )
                    keyframe.setInAccel(  max(0.01,  math.sqrt(math.pow(ac2,2.0) + math.pow(sl*ac2,2.0)) * (1.0 - bias_val) ) )
                  
                    #end keyrames                            
                    parm.setKeyframe(keyframe)
    
                   
              
    def undoTrigger(self,**kwargs):
        if self.__doCB:
            self.handleCallback() 
              
    
    def handleCallback(self):
         
        self.slider_ease.updateValue(hou.node("/obj").parm("undoCBx").eval())
        self.slider_bias.updateValue(hou.node("/obj").parm("undoCBy").eval())
        self.slider_relax.updateValue(hou.node("/obj").parm("undoCBz").eval())
        self.slider_apex.updateValue(hou.node("/obj").parm("undoCBw").eval())
       
    def primeUndo(self):
        for item in hou.node("/obj").eventCallbacks():
            if item[0][0]==hou.nodeEventType.ParmTupleChanged and item[1].__name__=="undoTrigger":
                 hou.node("/obj").removeEventCallback((hou.nodeEventType.ParmTupleChanged,), item[1])
        
        hou.node("/obj").addEventCallback((hou.nodeEventType.ParmTupleChanged,), self.undoTrigger)
    
    def paintEvent(self, event):
        painter = QtGui.QPainter(self).fillRect(0, 0, self.width(), self.height(), hou.qt.getColor("BackColor"))
       
    def resizeEvent(self, event):
        pass
        
    def wheelEvent(self,event):
        pass
    
    def updateSliderColors(self, keyframes=None):
        self.slider_bias.setInfluence(self.slider_ease.value()==0)
        self.slider_relax.setInfluence(self.slider_ease.value()==0)
        
        noMidSelected=True
        if keyframes==None:
            keyframes=self.getKeyframes()
            
        for data in keyframes:
            if data[2]==1:
                noMidSelected=False 
                    
        self.slider_apex.setInfluence(self.slider_ease.value()==0 or noMidSelected or self.slider_relax.value()==0 )
        
  
    def enterEvent(self, event): 
        self.updateSliderColors()
        pass
        
    def keyPressEvent(self, event):
        super(PbaPanel, self).keyPressEvent(event)


