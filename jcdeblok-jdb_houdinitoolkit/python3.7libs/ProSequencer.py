
#########################################################################       
#  ProSequencer for Houdini 
#  Jonathan de Blok - jonathan@jdbgraphics.nl
#########################################################################        
   
 
import math
import os
import sys
import hou
import math
import toolutils
import re
import platform
import subprocess
import json
import time
import importlib

try:
    import jdb
except:
    pass


#load any plugins if available
ProSequencerPlugins=None
try:
    import ProSequencerPlugins
    importlib.reload(ProSequencerPlugins)
except: 
    ProSequencerPlugins=None
    pass
   
from PySide2 import QtCore, QtGui, QtWidgets

def Enum(**enums):
    return type('Enum', (), enums)
        
class PsTrack(QtWidgets.QPushButton):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.dragType = Enum(No=-1, Left=0, Center=1, Right=2)
    
        self.index = 0
        self.dataNode = None
        self.trackEnabled=True
        self.trackTake=False
        self.trackCamera=False
        self.trackOrder=0
        self.inpoint=1
        self.outpoint=100
        self.oldInpoint=1
        self.oldOutpoint=100
        self.completed=0
        self.setMouseTracking(True)
        self.drag=self.dragType.No
        self.setCursor(QtCore.Qt.SizeHorCursor)   
        self.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self.on_context_menu)
        self.selected = False
        self.trackName = "Track"
        self.setAcceptDrops(True)
        
        #styling,  'defaultstyle' is used to pick values from to revert to. 'style' is the actual style that is applied
        self.defaultStyle = {'background-color': '#555', 'color': '#ddd', 'border-right' : str(int(5 * hou.ui.globalScaleFactor()))+'px solid green', 'border-left' :  str(int(5 * hou.ui.globalScaleFactor()))+'px solid green', 'padding-left': '4px' ,'text-align' : 'left', 'font-size': str(int(12 * hou.ui.globalScaleFactor()))+"px", 'padding':'0px' }   
        self.style = self.defaultStyle.copy()
        self.SetStyle()


        #makesure everything is dispalyed correctly
        #self.Update()
    
     
    def dragEnterEvent(self, event):
        event.acceptProposedAction()

        
    #Handle drop events on track 
    def dropEvent(self, event, **kwargs ):
       
        ctake=hou.takes.currentTake()
        if hou.takes.rootTake()!=ctake:
            hou.takes.setCurrentTake(hou.takes.rootTake())   
 
        parts=event.mimeData().text().split(',')

        #parse all dropped nodes
        for part in parts:
            node=hou.node(part)
            affectTracks = [self]
            
            
            #if multiple tracks are selected, parse drop on those tracks as well
            for item in self.parent().tracks:
                if (item!=self):
                    if item.selected:
                        affectTracks.append(item)
             
            #handle different types of dropped nodes              
            if node:
                if node.type().name()=='cam':
                    for track in affectTracks:
                        track.dataNode.parm("camera").deleteAllKeyframes() 
                        track.dataNode.parm("camera").set(node.path())
                        track.UpdateLabel()
                        
                        if node.name()!=track.dataNode.name():
                            if hou.ui.displayConfirmation("Rename Camera to match track?"):
                                node.setName(track.dataNode.name(),True)
                        
                        
                    self.parent().updateDependends()
                    self.parent().outputPlaybarEvent() 
     
                elif node.type().name()=='timeshift':
                    node.parm("frame").deleteAllKeyframes()      
                    node.parm("frame").setExpression('ch("'+self.dataNode.path()+'/range1")', hou.exprLanguage.Hscript)
                
                elif node.type().name()=='filecache':
                    node.parm("f1").deleteAllKeyframes()      
                    node.parm("f1").setExpression('ch("'+self.dataNode.path()+'/range1")', hou.exprLanguage.Hscript)
                    node.parm("f2").deleteAllKeyframes()      
                    node.parm("f2").setExpression('ch("'+self.dataNode.path()+'/range2")', hou.exprLanguage.Hscript)
              
                elif node.type().name()=='rslightdome::2.0':
                    try:
                        node.parm("backPlateEnabled").deleteAllKeyframes()   
                        node.parm("backPlateEnabled").set(True)   
                        node.parm("tex1").deleteAllKeyframes()  
                        node.parm("tex1").set( self.dataNode.parm("camera").evalAsNode().parm("vm_background").rawValue() )  
                    except:
                        print("Failed to set backplate.. no cam?")
                        pass
                        
                   
                    
                    
                    
                elif node.type().name()=='timewarp':
                    node.parm("outrange1").deleteAllKeyframes()      
                    node.parm("outrange1").setExpression('ch("'+self.dataNode.path()+'/range1")', hou.exprLanguage.Hscript)
                    node.parm("outrange2").deleteAllKeyframes()      
                    node.parm("outrange2").setExpression('ch("'+self.dataNode.path()+'/range2")', hou.exprLanguage.Hscript)
       
                elif node.type().name()=='retime':
                    node.parm("outputrangex").deleteAllKeyframes()      
                    node.parm("outputrangex").setExpression('ch("'+self.dataNode.path()+'/range1")', hou.exprLanguage.Hscript)
                    node.parm("outputrangey").deleteAllKeyframes()      
                    node.parm("outputrangey").setExpression('ch("'+self.dataNode.path()+'/range2")', hou.exprLanguage.Hscript)
                    
       
                    
                elif node.type().name()=='deadline':
                    for track in affectTracks:
                        track.dataNode.parm("deadline").deleteAllKeyframes()
                        track.dataNode.parm("deadline").set(node.path())
                        track.UpdateLabel()        

                elif node.type().name()=='kinefx::fbxanimimport' or  node.type().name()=='kinefx::motionclipretime' :
                   
  

                    parm=self.parent().getAuxByNote(self.dataNode, "user_offset", "float", returnParm=True ) 
                    if not parm:
                        self.dataNode.parm("auxfloat").set( self.dataNode.parm("auxfloat").eval()+1)

                        id= self.dataNode.parm("auxfloat").eval()

                        self.dataNode.parm("notefloat"+str(id)).set("user_offset")

                        parm=self.dataNode.parm("auxfloat"+str(id))
                    
                    
                    parmd=self.dataNode.parm("duration")
                    parmr=self.dataNode.parm("range1")

                  
                    if parm and node.type().name()=='kinefx::fbxanimimport':

                        node.parm("useanimationstartframe").set(1)
                        node.parm("animationendframe").set(1)
                        node.parm("playbackstartframe").set(1)
                        node.parm("timeshiftmethod").set(1)
                        node.parm("frame").deleteAllKeyframes() 
                        node.parm("frame").setExpression("$FF", hou.exprLanguage.Hscript)

                        node.parm("animationstartframe").deleteAllKeyframes() 
                        node.parm("animationstartframe").setExpression("ch(\""+parm.path()+ "\")", hou.exprLanguage.Hscript)

                        node.parm("animationendframe").deleteAllKeyframes() 
                        node.parm("animationendframe").setExpression("ch(\"animationstartframe\")+ch(\""+parmd.path()+"\")", hou.exprLanguage.Hscript)
 
                        node.parm("playbackstartframe").deleteAllKeyframes() 
                        node.parm("playbackstartframe").setExpression("ch(\""+parmr.path()+ "\")", hou.exprLanguage.Hscript)
                        affectTracks[0].dataNode.setName( node.name() )
                   
                    if parm and node.type().name()=='kinefx::motionclipretime':
                    
           
                        node.parm("setanimstart").set(1)
                        node.parm("setanimend").set(1)
                        node.parm("setshift").set(1)
                        node.parm("animstart").deleteAllKeyframes() 
                        node.parm("animstart").setExpression("ch(\""+parm.path()+ "\")", hou.exprLanguage.Hscript)

                        node.parm("animend").deleteAllKeyframes() 
                        node.parm("animend").setExpression("ch(\"animationstartframe\")+ch(\""+parmd.path()+"\")", hou.exprLanguage.Hscript)
 
                        node.parm("shift").deleteAllKeyframes() 
                        node.parm("shift").setExpression("ch(\""+parmr.path()+ "\")", hou.exprLanguage.Hscript)
                        affectTracks[0].dataNode.setName( node.name() )

                         

                
                elif node.type().name()=='channel':
                    for track in affectTracks:
                        track.dataNode.parm("animlayer").deleteAllKeyframes()
                        track.dataNode.parm("animlayer").set(node.path())
                        for j in node.outputs():
                            for i, item in enumerate(j.inputs()):
                                 if item==node:
                                    j.parm("weight"+str(i)).deleteAllKeyframes()
                                    j.parm("weight"+str(i)).setExpression('ch("'+track.dataNode.path()+'/active")', hou.exprLanguage.Hscript)
                        
                        
                elif node.type().name()=='output':
                    node.parm("f1").deleteAllKeyframes()      
                    node.parm("f1").setExpression('ch("'+self.dataNode.path()+'/range1")', hou.exprLanguage.Hscript)
                    node.parm("f2").deleteAllKeyframes()      
                    node.parm("f2").setExpression('ch("'+self.dataNode.path()+'/range2")', hou.exprLanguage.Hscript)
                    
                    try:
                        node.parm("dopoutput").deleteAllKeyframes()      
    
                        cname=ProSequencerPlugins.getJDB()+"/cache/" + self.dataNode.name() + "/"+self.dataNode.name()+"_$F6.sim"
                        if node.evalParm("usesimframes"):
                            cname=self.getJDB()+"/cache/" + self.dataNode.name() + "/"+self.dataNode.name()+"_$SF.sim"
                        
                        node.parm("dopoutput").set(cname)   
                        node.parent().parm("playfilesname").set(cname)
                    except:
                        pass
                    
                elif node.type().name()=='rop_geometry':    
                    try:
                        node.parm("f1").deleteAllKeyframes()      
                        node.parm("f1").setExpression('ch("'+self.dataNode.path()+'/range1")', hou.exprLanguage.Hscript)
                        node.parm("f2").deleteAllKeyframes()      
                        node.parm("f2").setExpression('ch("'+self.dataNode.path()+'/range2")', hou.exprLanguage.Hscript)
                        node.parm("trange").deleteAllKeyframes()      
                        node.parm("trange").set(1)
                        
                        cname=self.getJDB()+"/cache/" + self.node.name() + "/"+self.node.name()+"_$F6.sim"
                        node.parm("sopoutput").set(cname)
                    except:
                        pass
                else:
                
                    try:
                        node.parm("f1").deleteAllKeyframes()      
                        node.parm("f1").setExpression('ch("'+self.dataNode.path()+'/range1")', hou.exprLanguage.Hscript)
                        node.parm("f2").deleteAllKeyframes()      
                        node.parm("f2").setExpression('ch("'+self.dataNode.path()+'/range2")', hou.exprLanguage.Hscript)
                        node.parm("trange").deleteAllKeyframes()      
                        node.parm("trange").set(1)
                    
                    except:
                        pass
                    cam = next((x for x in node.parms() if x.name() == "camera"), False) or next((x for x in node.parms() if x.name() == "RS_renderCamera"), False)
                    
                    trange = next((x for x in node.parms() if x.name() == "trange"), False)
                    f1 = next((x for x in node.parms() if x.name() == "f1"), False)
                    f2 = next((x for x in node.parms() if x.name() == "f2"), False)
                    f3 = next((x for x in node.parms() if x.name() == "f3"), False)   
                    take = next((x for x in node.parms() if x.name() == "take"), False)
                    
                    if   trange!=False and f1!=False and f2!=False and f3!=False and take!=False:
                        #looks like we have some sort or render node   
                        for track in affectTracks:
                            track.dataNode.parm("rop").deleteAllKeyframes()
                            track.dataNode.parm("rop").set(node.path())
        if ctake!=hou.takes.currentTake():                 
            hou.takes.setCurrentTake( ctake )
        return True         
   
    def dummy(self, event):
        pass
        
    #Context menu content    
    def on_context_menu(self, point):
    
        self.popMenu = QtWidgets.QMenu(self)         
        self.popMenu.addSeparator()

        #get selected tracks
        selTracks=[]
        for item in self.parent().tracks:
            if item.selected:
                selTracks.append(item)
        
        #takes------------------------
        cmd_curtake = self.popMenu.addAction('Assign current Take to this' )    
        if self.dataNode.evalParm("take") == hou.takes.currentTake().name() or hou.takes.currentTake() == hou.takes.rootTake() :
            cmd_curtake.setEnabled(False)

        cmd_deftake = self.popMenu.addAction('Assign Main Take this' )    
        if not self.dataNode.evalParm("take"):
            cmd_deftake.setEnabled(False)

        self.popMenu.addSeparator()    
        
        #render------------------------
        cmd_renderSelected = self.popMenu.addAction('Render ROP(s) for selected')    
        if (not hou.node(self.dataNode.evalParm("camera")) and False  ) and len(selTracks)==1 : 
            cmd_renderSelected.setEnabled(False)
            

        cmd_prepSelected = self.popMenu.addAction('Just prepare ROP(s) for selected to render' )    
        if (not hou.node(self.dataNode.evalParm("camera")) and False  ) and len(selTracks)==1 : 
            cmd_prepSelected.setEnabled(False)
            
        #deadline
        cmd_submitDeadline = self.popMenu.addAction('Submit selected to Deadline (Shift=High Prio, Alt=Supspened')        
        if (not hou.node(self.dataNode.evalParm("camera")) or len(self.getRops())==0 or not hou.node(self.dataNode.evalParm("deadline"))  ) and len(selTracks)==1  : 
            cmd_submitDeadline.setEnabled(False)
            pass
             
        #explore output        
        cmd_exploreOutput = self.popMenu.addAction('Explore output folder(s)')  
        #if not self.getPreviewPath(item.dataNode, True): 
            #cmd_exploreOutput.setEnabled(False)
        
            
        #output to mp4
        cmd_renderToMp4 = self.popMenu.addAction('Bake selected track renders to MP4' )  
        
        self.popMenu.addSeparator()
        
       
        
        #Flipbook------------------------
        cmd_renderFlipMP = self.popMenu.addAction('Flipbook this (MPlay)' )    
        cmd_renderFlipFS = self.popMenu.addAction('Flipbook selected (File sequence)' )    
        cmd_renderFlipMp4 = self.popMenu.addAction('Flipbook selected (MP4)' )   
        cmd_encodeFlipMp4 = self.popMenu.addAction('Preview to MP4' ) 
        cmd_renderFlipExplore = self.popMenu.addAction('Explore output folder(s)' )  
        cmd_playflip = self.popMenu.addAction('Play current MP4(s)' )  
        
        self.popMenu.addSeparator()
 
        #Misc------------------------   
        cmd_tokenTest = self.popMenu.addAction('Test Tokens' )  
        cmd_upgrade = self.popMenu.addAction('Upgrade all Tracks' )  
        
       
        
        #Time ------------------------
        self.popMenu.addSeparator()
        cmd_setrange = self.popMenu.addAction('Set Track(s) range to match camera keyframes' )  
        cmd_sort = self.popMenu.addAction('Order All Tracks by Name' )  
        cmd_goin = self.popMenu.addAction('Go To InPoint')
        cmd_goout = self.popMenu.addAction('Go To OutPoint')
        cmd_setpbrange = self.popMenu.addAction('Focus Playbar on Track(s)')
 
        #caches
        self.popMenu.addSeparator()
        cmd_bakeCache= self.popMenu.addAction('Bake "cache_bake" AuxOps'  )  
        cmd_renderTest= self.popMenu.addAction('Render "test_frame" AuxOps'  )  

        
          
        #NodeBundles ------------------------
        self.popMenu.addSeparator()
        cmd_addBundle = self.popMenu.addAction('Create NodeBundle for Track(s)' )  
        cmd_addToBundle = self.popMenu.addAction('Add selection to Track(s) bundle(s)' )  

        customAction=[]
        customData=[] 
          
        if (ProSequencerPlugins!=None):
            try:
                customData = ProSequencerPlugins.psCustomContext()
                self.popMenu.addSeparator()
                for cust_item in customData: 
                    if cust_item[0]!='sep':
                        customAction.append(self.popMenu.addAction(cust_item[0] ))        
                    else:
                        self.popMenu.addSeparator()
                        customAction.append("-")
            except:
                print("Issue with ProSequencer Plugin")
                pass    
          
            
        # show context menu
        action = self.popMenu.exec_(self.mapToGlobal(point))
 
        shiftPressed=QtWidgets.QApplication.keyboardModifiers() == QtCore.Qt.ShiftModifier
        for i, act in enumerate(customAction): 
        
        
            if act == action:
            
                clipboard = QtWidgets.QApplication.clipboard()
                clipboard.setText('''var proj = app.project;
                var items = proj.items;
                
                function toFolder(trg, folder) {

                    var myFolder = undefined;

                    for (var i = 1; i <= items.length; i++) {
                        item = items[i]
                        if (item instanceof FolderItem) {


                            if (item.name == folder) {
                                myFolder = item;
                                break;
                            }
                        }
                    }
         
                    if (myFolder == undefined) {
                        myFolder = app.project.items.addFolder(folder);
                    }

                    trg.parentFolder = myFolder;

                }


                function addComp(name, x, y, len, fps) {
                    var myComp = undefined;

                    for (var i = 1; i <= items.length; i++) {
                        item = items[i]
                        if (item instanceof CompItem) {
                            if (item.name == chk) {
                                myComp = item;
                                break;
                            }
                        }
                    }

                    if (myComp == undefined) {
                        myComp = app.project.items.addComp(chk, x, y, 1, len, fps)
                    }

                    return myComp

                }

                function loadFootage(path) {

                    var footage = undefined

                    for (var i = 1; i <= items.length; i++) {

                        if (items[i] instanceof FootageItem) {

                            if (items[i].file.fsName.replace(/^.*[////]/, '') == path.replace(/^.*[////]/, '')) {
                         
                                footage = items[i]
                            }

                        }

                    }
                    if (footage == undefined) {
                        var io = new ImportOptions(File(path));
                        if (io.canImportAs(ImportAsType.FOOTAGE)) {
                            io.importAs = ImportAsType.FOOTAGE;
                            io.sequence = true;

                            footage = app.project.importFile(io);
                            footage.name = path.replace(/^.*[////]/, '');
                        }
                    }

                    return footage
                }


                function addFootage(comp, footage, name) {
                    var chkLayer = comp.layer(name);

                    if (chkLayer == undefined) {
                        chkLayer = comp.layers.add(footage);
                        chkLayer.name = name
                    }

                    return chkLayer
                }
                ''')
                
                for itemt in selTracks: 
                    cam = itemt.dataNode.evalParm("camera")
                    render = itemt.getOutputPath(itemt.dataNode)
                    preview = itemt.getPreviewPath(itemt.dataNode)
                    version = itemt.dataNode.evalParm("version")
                    track = itemt.dataNode.path()
                     
                    customData[i][1]([cam, render, preview, version, track, self.parent(), QtWidgets.QApplication.keyboardModifiers() == QtCore.Qt.ShiftModifier, self , QtWidgets.QApplication.keyboardModifiers() == QtCore.Qt.ControlModifier])     
        

        if action == cmd_setpbrange:
        
            start=1000000
            end=-1
            
            for itemt in selTracks: 
 
                start=min(start,itemt.dataNode.parm("range1").eval())
                
                end=max(end,itemt.dataNode.parm("range2").eval())
            
            crange=hou.playbar.frameRange()                
                
            needUpdate=False
            if crange[0]>start:
                crange[0]=start
                needUpdate=True
                
            if crange[1]<end:
                crange[1]=end
                needUpdate=True
            
            if needUpdate:
                hou.playbar.setFrameRange(crange[0], crange[1])
                
                
                
            hou.playbar.setPlaybackRange(start,end)

            self.parent().SyncNavBar()


        

        if action == cmd_renderTest:
            for itrack in selTracks: 
                
             
        
                for frame in self.parent().getAuxByNote( itrack.dataNode,  "render_test", "float", returnArray=True):

                
                   
                    
                    for rop in itrack.getRops():
                        if not rop.isBypassed():

                            itrack.forceThisTrack(True)  
                            itrack.prepROP(itrack.dataNode)

                     
                            rop.parm("f1").set(frame)
                            rop.parm("f2").set(frame)

                            tmp=rop.parm("RS_outputFileNamePrefix").rawValue();

                            tmp=os.path.dirname(tmp)+"/render_test/"+os.path.basename(tmp)
                   
                            rop.parm("RS_outputFileNamePrefix").set( tmp  )

                            rop.render()
                              
        
        if action == cmd_bakeCache:
            for itrack in selTracks: 
                
                itrack.forceThisTrack(True)  
        
                for itemx in self.parent().getAuxByNote( itrack.dataNode,  "cache_bake", "op", returnNone=False):
            
                    itemx.parm("execute").pressButton()
                    
                    
                            
                    
        if action == cmd_setrange:
            for itemt in selTracks: 
 
                    cam = itemt.dataNode.parm("camera").evalAsNode()
             
                    if cam!=None:
                        try: 
                            range=itemt.parent().getKeyframeRange(cam)
                            itemt.dataNode.parm("range1").set(range[0])
                            itemt.dataNode.parm("range2").set(range[1])
                        except:
                            pass 
        
        if action == cmd_goin:
            if QtWidgets.QApplication.keyboardModifiers() != QtCore.Qt.ShiftModifier:
                hou.setTime( self.dataNode.evalParm('range1')/hou.fps())
            else:
                hou.setTime( (self.dataNode.evalParm('range1')+25)/hou.fps())
            
            
        if action == cmd_goout:
            if QtWidgets.QApplication.keyboardModifiers() != QtCore.Qt.ShiftModifier:
                hou.setTime( self.dataNode.evalParm('range2')/hou.fps())
            else:
                hou.setTime(( self.dataNode.evalParm('range2')-25)/hou.fps()) 
        if action == cmd_sort:
        
            seq=self.parent().currentSequence
            
            sort_tmp=[]
            for itemt in self.parent().tracks:
              
                sort_tmp.append([itemt.dataNode.name(), itemt])
            
    
            sort_tmp.sort(key=lambda x: x[0])    
            
            i=0
            for itemt in sort_tmp:
             
                seq.setInput(i, itemt[1].dataNode)
                i=i+1
                
            
                            
        if action == cmd_addBundle:
            for itemt in selTracks:
                nb=hou.nodeBundle( itemt.dataNode.name() )
                if nb==None:
                    nb = hou.addNodeBundle(itemt.dataNode.name())
                   
                nb.addNode( itemt.dataNode )  
  
        if action == cmd_addToBundle:
            for itemt in selTracks:
                nb=hou.nodeBundle( itemt.dataNode.name() )
                if nb==None:
                    nb = hou.addNodeBundle(itemt.dataNode.name())
                nb.addNode( itemt.dataNode )  

                for sel in hou.selectedNodes():
                    nb.addNode(sel)
                
                
        if action == cmd_tokenTest:
            
            print("\n----Available tokens:")
            print("{camera} {rop} {meta} {version} {take} {sequence} {track}")
            print("using a single character to prefix a token is allowed. For example {_version} will only print the '_' if version is not empty.")
        
        
            print("\nToken test:")
            for item in selTracks: 
                print("\n----"+item.dataNode.name()+" (for current frame)" )
                rops=self.getRops(item.dataNode)
    
                if len(rops)==0:
                    print("Please assing ROP(s) to track first")
             
                #print rops 
                for rop in rops:
                    path = self.getOutputPath( item.dataNode, rop, True)
                    if path:
                        print("render output '"+rop.path()+"': " + hou.expandString(path))
                    else:
                        print("Missing 'Camera', 'ROP' and/or 'Render Output' for this track")
            
                path = self.getPreviewPath(item.dataNode, True) 
                if path:
                    print("preview output: " + hou.expandString(path))
                else:
                    print("Missing 'Camera', and/or 'Preview Output' for this track")
            
            print("----done")
            
        
        #flipbook to MPlay
        if action == cmd_renderFlipMP:
        
            if not hou.node(self.dataNode.evalParm("camera")):
                self.parent().HandleError("Aborting MPlay: 'Camera' not set fror track: " + item.dataNode.path(),0)
                return False

            #setting this flag puts PS in manual mode, so it can flipbook a whole track even if it's not the dominant track
            tf = self.parent().currentSequence.isTemplateFlagSet()
            
            #set in main take
            ctake=hou.takes.currentTake() 
            hou.takes.setCurrentTake(hou.takes.rootTake() ) 
            self.parent().currentSequence.setTemplateFlag(True)
            hou.takes.setCurrentTake(ctake)
            
            self.forceThisTrack()
            self.makeFlipbook( self.dataNode.evalParm("range1"),  self.dataNode.evalParm("range2"),  '',  True,  self.dataNode.evalParm("audio"), self.dataNode.evalParm("syncaudio") )

            #restore flags and take
            ctake=hou.takes.currentTake()
            hou.takes.setCurrentTake(hou.takes.rootTake() ) 
            self.parent().currentSequence.setTemplateFlag(tf)
            hou.takes.setCurrentTake(ctake) 
                
            
        #flipbook imagesequence       
        if action == cmd_renderFlipFS or action == cmd_renderFlipMp4:
            
            tf = self.parent().currentSequence.isTemplateFlagSet()
            ctake=hou.takes.currentTake()
            hou.takes.setCurrentTake(hou.takes.rootTake() ) 
            self.parent().currentSequence.setTemplateFlag(True)
            hou.takes.setCurrentTake(ctake)
            
            #validate 
            for item in selTracks:   
                if not self.getPreviewPath(item.dataNode, True):
                    self.parent().HandleError("Aborting preview: 'Camera' and/or 'Flipbook Output' not set for track: " + item.dataNode.path(),0)
                    return False

            #do for all selected tracks        
            for item in selTracks:   
            
                fileout= self.getPreviewPath(item.dataNode)
                tmp=hou.expandString( os.path.split(fileout)[0])
 
                #attempt to create output folder for image sequence
                if not os.path.isfile(tmp):
                    if not os.path.exists(tmp):
                        try:
                            os.makedirs(tmp)
                        except:
                            self.parent().HandleError("Aborting: Error creating folder for 'Flipbook Output':\n" + tmp,0)
                            ctake=hou.takes.currentTake()
                            hou.takes.setCurrentTake(hou.takes.rootTake() ) 
                            self.parent().currentSequence.setTemplateFlag(tf)
                            hou.takes.setCurrentTake(ctake)
                            return False
                            
                    item.forceThisTrack()
                    print("Making preview")
                    
                    start=item.dataNode.evalParm("range1")
                    end=item.dataNode.evalParm("range2")
                    
                    prestart=self.parent().getAuxByNote( item.dataNode,  "preview_start", "float", returnNone=True)
                    preend=self.parent().getAuxByNote( item.dataNode,  "preview_end", "float", returnNone=True)
                    
                    if prestart!=None:
                        start=prestart
                        
                    if preend!=None:
                        end=preend
                    
                    
                    
                    
                    
                    
                    self.makeFlipbook( start,  end,  fileout,  False,  item.dataNode.evalParm("audio"), item.dataNode.evalParm("syncaudio") )
                else:
                    self.parent().HandleError("Aborting: check tokens in 'Flipbook Output':\n" + tmp,0)
            
            ctake=hou.takes.currentTake()
            hou.takes.setCurrentTake(hou.takes.rootTake() ) 
            self.parent().currentSequence.setTemplateFlag(tf)
            hou.takes.setCurrentTake(ctake)
            
        #note: action above is performed as well to generate the imageseq for the mp4    
        if action == cmd_renderFlipMp4 or action == cmd_encodeFlipMp4:
        
          
        
            for item in selTracks:   
            
                #rewrite houdini frame number in filename $F<n> to ffmpeg's  %0<n>d 
                raw=  self.getPreviewPath(item.dataNode)

            
                basefolder =  hou.expandString( os.path.split(raw)[0])+'/'
                infiles = basefolder 
                m = re.search('\$F(\d+)', raw)
                a='$F'+m.group(1)
                b='%0'+str(int(m.group(1)))+'d'
                c='review'
                
                infiles =basefolder + os.path.split( raw.replace(a,b) )[1]
                outfile =  (os.path.splitext( basefolder + os.path.split( raw.replace(a,c) )[1])[0]+".mp4")
     
                start=item.dataNode.evalParm("range1")
                end=item.dataNode.evalParm("range2")
                
                prestart=self.parent().getAuxByNote( item.dataNode,  "preview_start", "float", returnNone=True)
                preend=self.parent().getAuxByNote( item.dataNode,  "preview_end", "float", returnNone=True)
                
                if prestart!=None:
                    start=prestart
                    
                if preend!=None:
                    end=preend
                        
                        
                
                try:
                    if hou.getenv("ocio")!=None and False:
                        import jdb
                        #reload(jdb)
                        print("ACEScg to sRGB...")
                        print(basefolder + os.path.split( raw.replace(a,"*"))[1])
                        jdb.ACEScg_to_sRBG( basefolder + os.path.split( raw.replace(a,"*"))[1] , 16 )
                        infiles= infiles.replace("_ACESCG_", "_sRGB_").replace(".exr",".jpg")
                        print("completed")
                except:
                    pass
       
            
                cmd = "ffmpeg -hide_banner -framerate "+ str(hou.fps()) +" -y -start_number "+str( int(start))+" -i \""+infiles+"\" \""+outfile+"\""
                
                audio = item.dataNode.evalParm("audio")
                
                if audio:
                
                    useroffset=self.parent().getAuxByNote( item.dataNode,  "audio_offset", "float") 
                    
              
                      
                    if item.dataNode.evalParm("syncaudio"):
                        
                        offset = ( useroffset ) / hou.fps()  
                          
                        cmd = "ffmpeg -v quiet -stats -hide_banner -framerate "+ str(hou.fps()) +" -y   -start_number "+str( int(start))+" -apply_trc iec61966_2_1 -i \""+infiles+"\" -itsoffset "+str(offset)+"   -i \""+audio+"\"  -c:v libx264 -flags:v \"+cgop\" -g 15 -bf 1 -coder ac \""+outfile+"\"  -c:a aac"
                    else:

     
                    
                        offset = ((item.dataNode.evalParm('range1') - useroffset ) / hou.fps() )* -1
                        duration = (item.dataNode.evalParm('range2')  - item.dataNode.evalParm('range1') ) / hou.fps() 
                        cmd = "ffmpeg -v quiet -stats -hide_banner  -t " +str(duration) +  "  -framerate "+ str(hou.fps()) +" -y   -start_number "+str( int(start))+"   -apply_trc iec61966_2_1 -i \""+infiles+"\"   -itsoffset "+str(offset)+" -i \""+audio+"\"  -shortest   -c:v libx264 -flags:v \"+cgop\" -g 15 -bf 1 -coder ac  \""+outfile+"\" -c:a aac"
     
                  
                print("Executing:")
                print(cmd)
                print(" ")
                #run ffmpeg and print out stdout lines
                p = subprocess.call(cmd,  stdout=subprocess.PIPE)
                try:
                    for line in iter(p.stdout.readline, b''):
                        print('>>> {}'.format(line.rstrip()))
                except:
                    pass
                print("Done: "+outfile)
                if shiftPressed:
                    os.system(outfile)
                 
                #note: action above is performed as well to generate the imageseq for the mp4    
        
         
        if action == cmd_renderToMp4:
            for item in selTracks:   
            
                #rewrite houdini frame number in filename $F<n> to ffmpeg's  %0<n>d 
                for rop in item.getRops():
                    print("------baking: '"+item.dataNode.path()+"' -> '"+rop.path()+"'")
                    if not rop.isBypassed():
                        raw=  self.getOutputPath(item.dataNode, rop)
                        basefolder =  hou.expandString( os.path.split(raw)[0])+'/'
                        infiles = basefolder 
                        m = re.search('\$F(\d+)', raw)
                        a='$F'+m.group(1)
                        b='%0'+str(int(m.group(1)))+'d'
                        c='review'
                        
                        infiles =basefolder + os.path.split( raw.replace(a,b) )[1]
                        audio = item.dataNode.evalParm("audio")
                        outfile = (os.path.splitext( basefolder+"../" + os.path.split( raw.replace(a,c) )[1])[0]+".mp4").replace("_ACESCG", "")
                        
                        try:
                            if hou.getenv("ocio")!=None:
                                import jdb
                                #reload(jdb)
                                print("ACEScg to sRGB...")
                                jdb.ACEScg_to_sRBG( basefolder + os.path.split( raw.replace(a,"*"))[1] , 16 )
                                infiles= infiles.replace("_ACESCG_", "_sRGB_").replace(".exr",".jpg")
                                print("completed")
                        except:
                            pass
                            
                        cmd = "ffmpeg  -v quiet -stats -hide_banner -framerate "+ str(hou.fps()) +" -y   -start_number "+str( int(item.dataNode.evalParm('range1')))+" -apply_trc iec61966_2_1 -i \""+infiles+"\" -c:v libx264 -flags:v \"+cgop\" -g 15 -bf 1 -coder ac  \""+outfile+"\""
                        print(cmd)
                        if audio:
                            if item.dataNode.evalParm("syncaudio"):
                                cmd = "ffmpeg -v quiet -stats -hide_banner -framerate "+ str(hou.fps()) +"  -y -start_number "+str( int(item.dataNode.evalParm('range1')))+" -apply_trc iec61966_2_1 -i \""+infiles+"\"   -i \""+audio+"\"  -c:v libx264 -flags:v \"+cgop\" -g 15 -bf 1 -coder ac \""+outfile+"\"  -c:a aac"
                            else:
                                offset = (item.dataNode.evalParm('range1') / hou.fps() )* -1
                                cmd = "ffmpeg -v quiet -stats -hide_banner -framerate "+ str(hou.fps()) +" -y   -start_number "+str( int(item.dataNode.evalParm('range1')))+" -apply_trc iec61966_2_1 -i \""+infiles+"\"   -itsoffset "+str(offset)+" -i \""+audio+"\"  -c:v libx264 -flags:v \"+cgop\" -g 15 -bf 1 -coder ac   \""+outfile+"\" -c:a aac"
           
                            
                        
                        print("Executing:")
                        print(cmd)
                        print(" ")
                        #run ffmpeg and print out stdout lines
                        p = subprocess.call(cmd,  stdout=subprocess.PIPE)
                        try:
                            for line in iter(p.stdout.readline, b''):
                                print('>>> {}'.format(line.rstrip()))
                        except:
                            pass
                        print("Done: "+outfile)
                        
                        if shiftPressed:
                            os.system(outfile)
                    
                    else:
                        print("ROP '"+rop.path()+"' has been skipped, bypass flag was set.")
                    print("------")
        
                    
        if action == cmd_playflip:
        
            for item in selTracks:
                path =  self.getPreviewPath(item.dataNode)
                if path:
                    path=hou.expandString(path)
                    
                    
                    #rewrite houdini frame number in filename $F<n> to ffmpeg's  %0<n>d 
                    raw=  self.getPreviewPath(item.dataNode)
                    print(raw)
                    basefolder =  hou.expandString( os.path.split(raw)[0])+'/'
                    m = re.search('\$F(\d+)', raw)
                    a='$F'+m.group(1)
                    b='%0'+str(int(m.group(1)))+'d'
                    c='review'
                    
                    outfile =  (os.path.splitext( basefolder + os.path.split( raw.replace(a,c) )[1])[0]+".mp4")
                    
                    
                    print(outfile)
                    os.startfile(outfile )    
                    
        #Explore FLIPBOOK output for selected tracks           
        if action == cmd_renderFlipExplore:
            for item in selTracks:   
                path =  self.getPreviewPath(item.dataNode)
                if path:
                    path=hou.expandString(os.path.split(path)[0])
                    self.parent().openFolder( path )
        
        #prep all ROPs from all selected tracks        
        if action == cmd_renderSelected or action ==  cmd_prepSelected:

            for item in selTracks: 

                nb_render=item.parent().getAuxByNote( item.dataNode,  "bundle_render", "op")
                nb_no_render=item.parent().getAuxByNote( item.dataNode,  "bundle_no_render", "op")

                if len(nb_render)>0:
                    nb=hou.nodeBundle( nb_render[0] )
               
                    if nb:
                        print("Enabled for render: "+nb_render[0])
                        for itemx in nb.nodes():
                            itemx.setDisplayFlag(True)
                    
                if len(nb_no_render)>0:
                    nb=hou.nodeBundle( nb_no_render[0] )
                    print("Disabled for render: "+nb_no_render[0])
                    for itemx in nb.nodes():
                        itemx.setDisplayFlag(False)   

                if not item.prepROP(item.dataNode, action == cmd_prepSelected):
                    break
                

     
        #render all rops of all selected tracks        
        if action == cmd_renderSelected:
            if hou.hipFile.hasUnsavedChanges() and  QtWidgets.QApplication.keyboardModifiers() != QtCore.Qt.ShiftModifier:  
                hou.hipFile.saveAsBackup()
                
            for item in selTracks: 
                item.prepROP(item.dataNode)
                for rop in item.getRops():
                    if not rop.isBypassed():
                    
      
                            
                        rop.render()

                       
                        
                        print("Done! Track: "+ item.dataNode.path() +" - ROP: "+rop.path())
                    else:
                        print("skipped: " + rop.path())
              
        #submit to deadline          
        if action == cmd_submitDeadline:
            hou.hipFile.saveAsBackup()
            
            
            #if hou.sessionModuleSource()!="":
            #    if not hou.ui.displayConfirmation("Overwrite the current hip file?" ): 
            #        return False
                    
            print("saving backup + current HIP")
                        
            for item in selTracks:       
                dlnode= hou.node( item.dataNode.evalParm("deadline"))
                if dlnode:
                
                 
                    if item.prepROP(item.dataNode):
     
                        #prep deadline node for submission
                        dlnode.parm("dl_job_name").set(hou.expandString('$HIPNAME/'+self.parent().currentSequence.name()+"/"+item.dataNode.name() ))
                        if len(item.dataNode.name().split("_"))==4:
                            dlnode.parm("dl_job_name").set((item.dataNode.name() +" "+ item.dataNode.evalParm("version") + item.dataNode.evalParm("meta")).replace("  "," ") )    
                        
                        dlnode.parm("dl_submit_scene").set(True)
                        
                        dlnode.parm("dl_priority").set(50)
                        dlnode.parm("dl_submit_suspended").set(False)
                           
                        if QtWidgets.QApplication.keyboardModifiers() == QtCore.Qt.ShiftModifier:
                            print("******* High Prio JOB *********")
                            dlnode.parm("dl_priority").set(75)
                                        
                        if QtWidgets.QApplication.keyboardModifiers() == QtCore.Qt.AltModifier:
                            print("******* High Prio JOB *********")
                            dlnode.parm("dl_submit_suspended").set(True)
                            
                            
                        #requires save, make backup as well 
                        #hou.hipFile.saveAsBackup() #save is done below
                        
                        #lock switch to current track
                        tmp = self.parent().currentSequence.isTemplateFlagSet()
                        tmp2=self.parent().currentSequence.evalParm('inputoverride')
                        
                        #reset camera 2d zooming/panning is not expressions or anims are set:
                        cam=hou.node(item.dataNode.evalParm("camera"))
                        if cam and  len(cam.parm("winx").keyframes())==0  and  len(cam.parm("winy").keyframes())==0 and  len(cam.parm("winsizex").keyframes())==0 and  len(cam.parm("winsizey").keyframes())==0:
                            cam.parm("winx").set(0);
                            cam.parm("winy").set(0);
                            cam.parm("winsizex").set(1);
                            cam.parm("winsizey").set(1);
                        
                            
                        nb_render=item.parent().getAuxByNote( item.dataNode,  "bundle_render", "op")
                        nb_no_render=item.parent().getAuxByNote( item.dataNode,  "bundle_no_render", "op")

                        if len(nb_render)>0:
                            nb=hou.nodeBundle( nb_render[0] )
               
                            if nb:
                                print("Enabled for render: "+nb_render[0])
                                for itemx in nb.nodes():
                                    itemx.setDisplayFlag(True)
                    
                        if len(nb_no_render)>0:
                            nb=hou.nodeBundle( nb_no_render[0] )
                            print("Disabled for render: "+nb_no_render[0])
                            for itemx in nb.nodes():
                                itemx.setDisplayFlag(False)   
                            
                        item.forceThisTrack(True)  
                
                        if not dlnode.isBypassed():
                            hou.hipFile.save(None,False)
                            dlnode.parm("dl_Submit").pressButton()
                        else:
                            hou.ui.displayMessage("Aborting: Deadline Node "+dlnode.path()+" is Disabled")
                            
                        #unlock switch
                        self.parent().currentSequence.setTemplateFlag(tmp)
                        self.parent().currentSequence.parm('inputoverride').set(tmp2)
                        
                        
                else:
                    self.parent().HandleError("Warning: No deadline ROP found for: " + item.dataNode.path(),1)    
         
        #Explore render output            
        if action == cmd_exploreOutput:

            #check ROPs
            rops=self.getRops()
            if len(rops)==0:
                self.parent().HandleError("Aborting: Empty 'Rop(s)' in:\n" + self.dataNode.path(),0)
                return False
            
            #get paths for all rops
            wrn=True
            for rop in rops:
                path =  self.getOutputPath( self.dataNode , rop, True)
                if path:
                    path=os.path.split(path)[0]
                    self.parent().openFolder( path )
                    wrn=False
            if wrn:
                print("Output path not available yet (missing token values?)")
                    
        #assing current Take        
        if action == cmd_curtake:
            self.SetInMainTake(self.dataNode.parm("take") , hou.takes.currentTake().name() )
            
        #assign root take
        if action == cmd_deftake:
            self.SetInMainTake(self.dataNode.parm("take") , ""  )
            if self.dataNode.evalParm("active") and not self.parent().currentSequence.isTemplateFlagSet() and not self.parent().currentSequence.isBypassed():
                hou.takes.setCurrentTake( hou.takes.rootTake() )
        
        #upgrade all tracks to current PS version        
        if action == cmd_upgrade:
            for item in self.parent().tracks: 
                item.upgradeTrack()
        
    def GetRecOutputs(self,nodes,col=[]):
        for n in nodes:
            for item in n.outputs():
                col.append(item)
            col=self.GetRecOutputs(n.outputs(),col)               
        return col
    
    
    #parse all {} tokens in filename            
    def parseTokens(self, path, tokens):
        for token in tokens:
            if token[1]=='':
                r=[m.start() for m in re.finditer('(?='+token[0]+'})', path)]
                for pos in reversed(r) :
                    path = path[:pos-1] + path[pos:]
        
            path=path.replace(token[0] , token[1])
        
        path=path.replace('{' , '')
        path=path.replace('}' , '')
        return path
    
        
    #make preview / flipbook
    def makeFlipbook(self, start, end, filename = '', mplay = True, audio ='', syncaudio = True):
     
        if mplay:
            filename=''
         
        scene  = toolutils.sceneViewer()
        flipbook_options = scene.flipbookSettings().stash()
        
        #override current flipbook settings for track
        flipbook_options.frameRange( (start, end) )
        flipbook_options.output(filename)
        flipbook_options.outputToMPlay(mplay)
        flipbook_options.audioFilename(audio) 
        
        #use camera resoltion if available
        if scene.curViewport().camera():
            flipbook_options.useResolution(True)
            flipbook_options.resolution((scene.curViewport().camera().evalParm('resx'), scene.curViewport().camera().evalParm('resy') ))
            flipbook_options.cropOutMaskOverlay(True)
            
        
        #handle audio
        flipbook_options.audioFrameStart(0)
        if syncaudio:
            flipbook_options.audioFrameStart(start)
        
      
        scene.flipbook(scene.curViewport(), flipbook_options)
        
    
    #set a param in the root take if current take is not root
    def SetInMainTake(self, parm, val):
        ctake=hou.takes.currentTake()
        hou.takes.setCurrentTake(hou.takes.rootTake() ) 
        parm.set(val)
        hou.takes.setCurrentTake(ctake)

    #return all ROP nodes for a track    
    def getRops(self, trackNode = False):
      
        if not trackNode:
            trackNode = self.dataNode  
     
        rops=[]    
        for item in list( trackNode.parm('rop').evalAsNodes()):
            #add filtering here
           

            rops.append(item)

        return rops
    
    #Returns output path for flipbook    
    def getPreviewPath(self, trackNode=False, validate=False, rop=False ):
    
        if not trackNode:
            trackNode=self.dataNode
    
        #validate, return False on fail    
        if validate:
            check=True
            
            if not  hou.node(trackNode.evalParm("camera")):
                check=False
            
            if not trackNode.evalParm("previewoutput"):
                check=False
            
            if not check:
                return False
        
        #parse tokens        
        tokens=[]
        if hou.node(trackNode.evalParm("camera")):
            tokens.append(['camera', hou.node(trackNode.evalParm("camera")).name() ])
        
        tokens.append(['meta', trackNode.evalParm("meta") ])
        tokens.append(['version', trackNode.evalParm("version") ])
        
        try:
            if self.parent().currentSequence:
                tokens.append(['sequence', self.parent().currentSequence.name() ] )
        except:
            pass
        tokens.append(['track', trackNode.name() ] )
        
        take = trackNode.evalParm("take")
        if take == '':
            take = hou.takes.rootTake().name()
        
        tokens.append(['take', take] )
            
        try:
            for item in ProSequencerPlugins.psCustomTokens(trackNode):
                tokens.append(item)
        except:
            pass
  
  
        if rop:
            tokens.append(['rop', rop.name() ] )

                        
        #this should be it
        path = self.parseTokens(trackNode.parm("previewoutput").unexpandedString(), tokens)
    
        if hou.getenv("ocio")!=None and False:
            if "_$F" in path:
                path=path.replace("_$F", "_ACESCG_$F")
            elif ".exr" in path:
                path=path.replace(".jpg", "_ACESCG.jpg")

        return path
        
        
    def getOutputFolder(self):
         os.path.dirname(self.getOutputPath())

    #returns render output path       
    def getOutputPath(self, trackNode=False, rop=False, validate = False, passName=""):
    
        skipCamCheck=False
           
     
        if not trackNode:
            trackNode=self.dataNode
              
        if validate:
            check=True
             
            if rop!=False:
                if rop.type().name()=='filmboxfbx' or rop.type().name()=='alembic':
                    skipCamCheck = True    
                
            if not  hou.node(trackNode.evalParm("camera")) and skipCamCheck==False:
                check=False
            
            if len(self.getRops(trackNode))==0:
                check=False
                
            if not trackNode.evalParm("renderoutput"):
                check=False
            
            if not check:
                return False
                
        tokens=[]
        if hou.node(trackNode.evalParm("camera")):
            tokens.append(['camera', hou.node(trackNode.evalParm("camera")).name() ])
        
        tokens.append(['meta', trackNode.evalParm("meta") ])
        tokens.append(['version', trackNode.evalParm("version") ])
         
        try: 
            if self.parent().currentSequence:
                tokens.append(['sequence', self.parent().currentSequence.name() ] )
        except:
            pass
    
        tokens.append(['track', trackNode.name() ] )
        
        take = trackNode.evalParm("take")
        if take == '':
            take = hou.takes.rootTake().name()
        
        tokens.append(['take', take] )
        
        try:
            for item in ProSequencerPlugins.psCustomTokens(trackNode):
                tokens.append(item)
        except:
            pass
            
        if rop:
            tokens.append(['rop', rop.name() ] )

        raw=trackNode.parm("renderoutput").unexpandedString()
        
        if passName:
            raw=raw.replace("$", passName+"_$")       

        path = self.parseTokens(raw , tokens)
    
        if hou.expandString("$OCIO")!='':
            if rop!=False:
                if not (rop.type().name()=='filmboxfbx' or rop.type().name()=='alembic'):
                    if "_$F" in path:
                        path=path.replace("_$F", "_ACESCG_$F")
                    elif ".exr" in path:
                        path-path.replace(".exr", "_ACESCG.exr")
        
        return path
    
    def upgradeTrack(self):
    
        src=self.dataNode
        
         
         
        switch = self.parent().currentSequence
        
        trg=self.parent().createTrackNode("tmp")
        
        n=src.name()
        src.setName("backup_"+n, True)    
    
        trg.setName(n)  
        trg.setPosition([src.position()[0]-0.5, src.position()[1]-0.5] )
        for item in src.parms():
            pname=item.name()
            trg.setColor(src.color())
            trg.bypass(src.isBypassed())
            
            try:
                trg.parm(pname).set( item.eval() )
            except:
                print("failed copy: "+pname)
        
        trg.setInput(0, src.inputs()[0])        
             
        for i, item in enumerate((switch.inputs())):            
            if item == src:
                switch.setInput(i,trg)
        
            
    #load all of track's ROPs with all relevant data to render a track        
    def prepROP(self, trackNode, goto=False):
      
        rops=self.getRops(trackNode)

        if len(rops)==0:
    
            self.parent().HandleError("Aborting: Empty 'Rop(s)' in: " + trackNode.path(),1)
            return False
         
        #validate
        for rop in rops:
            if not self.getOutputPath( trackNode, rop, True):
                self.parent().HandleError("Aborting: check 'Camera', 'Rop(s)' and 'Render Ouput' in:\n" + trackNode.path(),0)
                print("invalid")
                return False
        rop_index = 0        

        issue=""

        for rop in rops:
     
            try:    
                if rop.parm("RS_overrideCameraRes").eval()==1:
                    issue=issue+" " +rop.name()+": RS_overrideCameraRes set\n"
            except:
                pass


        if issue!="":
            print(issue)
            if not hou.ui.displayMessage( issue+"\nContinue?", buttons=("Yes", "No")) == 0:
                return False
     

        for rop in rops:
     
            self.forceThisTrack() 
         
            if goto:
                self.parent().gotoNode(rop, rop.name()+" ready to render track")
            #ctake=hou.takes.currentTake()
            hou.takes.setCurrentTake(hou.takes.rootTake() )
         
            try:
                 
                if rop.parm("vm_picture").eval()[:1]!='/' or  tracknode.evalParm('renderoutput')[:5]!='{jdb}':
                    rop.parm("vm_picture").deleteAllKeyframes()
                    tmp=self.getOutputPath( trackNode, rop )
                    rop.parm("vm_picture").set(tmp )
                else:
                    tmp = self.getOutputPath( trackNode, rop).replace("E:/Projects","/mnt/CloudFarm")
            
                    rop.parm("vm_picture").deleteAllKeyframes()
                    rop.parm("vm_picture").set(tmp)                    
                        
                        
            except:
     
                pass
            
            try:
                for i in range(0, rop.evalParm("vm_cryptolayers")):
                    try:
                        cn=rop.evalParm("vm_cryptolayername"+str(i+1))
                        rop.parm("vm_cryptolayeroutput"+str(i+1)).deleteAllKeyframes()
                        rop.parm("vm_cryptolayeroutput"+str(i+1)).set( self.getOutputPath( trackNode, rop, False, cn ) )
                    except:
                        pass
            except:
                pass
                
                
           
            try:
                cmid=["node","material","object","custom"]
                for i in range(0, rop.evalParm("RS_aov")):
                    if rop.evalParm("RS_aovID_"+str(i+1))==41:
                        cn=rop.evalParm("RS_aovSuffix_"+str(i+1))
                        cn="cryptomatte_"+ cmid[ rop.evalParm("RS_aovCryptomatteType_"+str(i+1))]  
                        rop.parm("RS_aovSuffix_"+str(i+1)).set("")
                        rop.parm("RS_aovCustomPrefix_"+str(i+1)).deleteAllKeyframes()
                        rop.parm("RS_aovCustomPrefix_"+str(i+1)).set( self.getOutputPath( trackNode, rop, False, cn ) )    
                        
                        rop.parm("RS_aovSuffix_"+str(i+1)).deleteAllKeyframes()
                        rop.parm("RS_aovSuffix_"+str(i+1)).set( '' )    
                        
                        cmid=cmid+1
            except:
                pass
                        
            try: 
                for i in range(0, rop.evalParm("vm_numaux")):
                    try:
                        cn=rop.evalParm("vm_channel_plane"+str(i+1))
                        rop.parm("vm_filename_plane"+str(i+1)).deleteAllKeyframes()
                        rop.parm("vm_filename_plane"+str(i+1)).set( self.getOutputPath( trackNode, rop, False, cn ) )
                    except:
                        pass
            except:
                pass
                

            try:
                if rop.parm("RS_archive_enable").eval()==True:
                
                    if rop.parm("RS_archive_file").eval()[:1]!='/' :
                        rop.parm("RS_archive_file").deleteAllKeyframes()
                        tmp=self.getOutputPath( trackNode, rop )
                        basefolder = os.path.dirname(tmp)+"/rs/" + os.path.basename(tmp).replace('.exr' , '.rs')
                        rop.parm("RS_archive_file").set(basefolder )
                    else:
                        tmp = os.path.splitext( self.getOutputPath( trackNode, rop).replace("E:/Projects","/mnt/CloudFarm").replace("/Dropbox/CloudFarm",'')  )[0]+".rs" 
                        tmp = os.path.dirname(tmp)+"/rs/"+os.path.basename(tmp)
                        rop.parm("RS_archive_file").deleteAllKeyframes()
                        rop.parm("RS_archive_file").set(tmp)                    
            except:
                pass
       

            try:
                rop.parm("RS_outputFileNamePrefix").deleteAllKeyframes()
      
                rop.parm("RS_outputFileNamePrefix").set( self.getOutputPath( trackNode, rop ) )
            except:
                pass
                 
                 
                
            try:    
                rop.parm("wr_picture").deleteAllKeyframes()
                rop.parm("wr_picture").set( self.getOutputPath( trackNode, rop ) )
            except:
                pass
                
            try:    
           
                
                if rop.parm("sopoutput").eval()[:1]!='/' :
                    rop.parm("sopoutput").deleteAllKeyframes()
                    tmp=self.getOutputPath( trackNode, rop )
                    rop.parm("sopoutput").set(tmp )
                else:
                    tmp = self.getOutputPath( trackNode, rop).replace("E:/Projects","/mnt/CloudFarm")
          
                    rop.parm("sopoutput").deleteAllKeyframes()
                    rop.parm("sopoutput").set(tmp)        
                    
                    
            except:
                pass
                
            try:
                rop.parm("picture").deleteAllKeyframes()
                rop.parm("picture").set( self.getOutputPath( trackNode, rop ) )
            except:
                pass
                
            try:
                rop.parm("filename").deleteAllKeyframes()
                rop.parm("filename").set( self.getOutputPath( trackNode, rop ) )
            except:
                pass    
                
            try:
                rop.parm("ri_display").deleteAllKeyframes()
                rop.parm("ri_display").set( self.getOutputPath( trackNode, rop ) )
            except:
                pass
            
            try:
                rop.parm("RS_renderCamera").deleteAllKeyframes()
                rop.parm("RS_renderCamera").set( trackNode.evalParm("camera") )
            except:
                pass
                
            try:    
                rop.parm("camera").deleteAllKeyframes()
                rop.parm("camera").set( trackNode.evalParm("camera") )
            except:
                pass
                
                
            try:    
                rop.parm("startnode").deleteAllKeyframes()
                rop.parm("startnode").set(trackNode.parm("auxop"+str(rop_index+1)).evalAsNode().path() )
                trackNode.parm("auxop"+str(rop_index+1)).evalAsNode().setDisplayFlag(True)
                
            except:
                try:
                    rop.parm("startnode").deleteAllKeyframes()
                    rop.parm("startnode").set( trackNode.parm("auxop1").evalAsNode().path() )
                except:
                    pass
                
            try:    
                rop.parm("root").deleteAllKeyframes()
                rop.parm("root").set(trackNode.parm("auxop"+str(rop_index+1)).evalAsNode().path() )
            except:
                try:
                    rop.parm("root").deleteAllKeyframes()
                    rop.parm("root").set( trackNode.parm("auxop1").evalAsNode().path() )
                except:
                    pass    
                
            
            inpoint=trackNode.evalParm("range1")
            outpoint=trackNode.evalParm("range2")

            
            if self.parent().getAuxByNote( trackNode,  "render_start", "float", returnNone=True):
                inpoint = self.parent().getAuxByNote( trackNode,  "render_start", "float")
                
            if self.parent().getAuxByNote( trackNode,  "render_end", "float", returnNone=True):
                outpoint = self.parent().getAuxByNote( trackNode,  "render_end", "float")

            if  rop.type().name()=="filmboxfbx":
                inpoint=-100
                outpoint=4000



            rop.parm("f1").deleteAllKeyframes()
            rop.parm("f1").set( inpoint )
             
            rop.parm("f2").deleteAllKeyframes()
            rop.parm("f2").set(outpoint )
            
            try:
                if (trackNode.parm('notefloat1').eval()=='single_frame' and trackNode.parm('auxfloat1').eval()!=0) or (trackNode.parm('notefloat2').eval()=='single_frame' and trackNode.parm('auxfloat2').eval()!=0):
                    rop.parm("f2").deleteAllKeyframes()
                    rop.parm("f2").set( trackNode.evalParm("range1") )
            except:
                pass
        
            
            rop.parm("take").deleteAllKeyframes() 
            if not trackNode.evalParm("take"):
                rop.parm("take").set( hou.takes.rootTake().name() )
            else:
                rop.parm("take").set( trackNode.evalParm("take") )
            if not rop.parm("trange").isLocked():
                rop.parm("trange").set(1)
            
            #hou.takes.setCurrentTake( ctake )
            
            
            if rop.type().name() == "filmboxfbx":
                #rop.parm('sopoutput').set(  os.path.splitext(rop.evalParm('sopoutput'))[0]+".fbx"   )

                tmp=rop.parm('sopoutput').rawValue().rsplit('$F', 1)
                if len(tmp)>0:
                    try:
                        rop.parm('sopoutput').set(  rop.parm('sopoutput').rawValue().replace("$F"+re.findall(r'\d+',tmp[1])[0] , "SingleFile"    )  )
                    except:
                        pass
                rop.parm('sopoutput').set(  os.path.splitext(rop.evalParm('sopoutput'))[0]+".fbx"   )   
                #rop.parm('sopoutput').set(  os.path.splitext(rop.evalParm('sopoutput'))[0]+".fbx"   )
                    
            if rop.type().name() == "alembic":
            
                tmp=rop.parm('filename').rawValue().rsplit('$F', 1)
                if len(tmp)>1:
                    rop.parm('filename').set(  rop.parm('filename').rawValue().replace("$F"+re.findall(r'\d+',tmp[1])[0] , "SingleFile"    )  )
                
                rop.parm('filename').set(  os.path.splitext(rop.evalParm('filename'))[0]+".abc"   )   
                    
            rop_index = rop_index + 1
            print("prepped: "+rop.name())
  
        return True 
        
        

    #Enable/disbale track    
    def SetEnabled(self, state=True):            
        self.trackEnabled = state
        
        if not state:
            self.style['background-color']='#222'
            self.style['color']='#777'
        else:
            self.style['background-color']=self.defaultStyle['background-color']
            self.style['color']=self.defaultStyle['color']
        self.SetStyle()
    
        
    def UpdateActiveIndicator(self):
    
        cnode = self.parent().currentSequence.inputs()[self.parent().currentSequence.evalParm("input")]
    
        for item in self.parent().tracks:
            try:
                item.SetActiveIndicator(item.dataNode == cnode)
            except:
                pass
                        
                    
        
    #set active indicator
    def SetActiveIndicator(self, state, external=False):
        if not self.selected:
            if state:
                if self.trackEnabled:
                    self.style['background-color']='#b36600'
                else:
                    self.style['background-color']='#333'
            else:
                if self.trackEnabled:
                    self.style['background-color']=self.defaultStyle['background-color']
                else:
                    self.style['background-color']='#222'
        
            self.SetStyle()
        
    #Select/Deselect a track    
    def SetSelected(self, state, external=False):
        cnode = self.parent().currentSequence.inputs()[self.parent().currentSequence.evalParm("input")]
        
        self.selected=state 
        
 
        if state:
            if  QtWidgets.QApplication.keyboardModifiers() != QtCore.Qt.ControlModifier:
                self.parent().lastSelected=self
            if self.trackEnabled:
                if (self.dataNode != cnode):
                    self.style['background-color']='#888'
                else:
                    self.style['background-color']='#d38855'
            else:
                self.style['background-color']='#333'
        else:
            if self.trackEnabled:
                #self.style['background-color']=self.defaultStyle['background-color']
                pass
            else:
                 self.style['background-color']='#222'
          
        
        self.SetStyle()
  
        if external == False and QtWidgets.QApplication.keyboardModifiers() != QtCore.Qt.ControlModifier:
 
            for item in self.parent().tracks:
                if (item!=self):
                    item.SetSelected(False, True)
                    
        
        self.UpdateActiveIndicator()   
            
    #    
    def GetInpoint(self):
        return self.inpoint
    #    
    def GetOutpoint(self):
        return self.outpoint

    #updates size and position based on in/out points, sets label, etc. Call this when you're done changing a tracks meta data.
    def Update(self):
        self.resize( QtCore.QSize( self.parent().frameToScreen( self.outpoint+1) - self.parent().frameToScreen( self.inpoint) , self.parent().getTrackHeight() ) )
        
        index= self.parent().tracks.index(self)
        
        self.move(QtCore.QPoint( self.parent().frameToScreen(self.inpoint) , self.parent().idToScreen( index )))
        self.UpdateLabel()
        self.UpdateActiveIndicator()
            
    
    # turn self.stlye dict into CSS string and apply    
    def SetStyle(self):
 
        css='QPushButton { border: 1px solid #333; margin: 0px; padding: 0px; '
            
        for k, v in self.style.items():
            css +=k+': '+v+'; '
            
        css += '}'    
        
        self.setStyleSheet(css)
        
    #update track labels according to all it's meta data    
    def UpdateLabel(self):
        if (self.trackName == "navbar"):
            return False
        id=self.parent().tracks.index(self)
      
        tn = self.trackName
        if self.dataNode!=None:
            cam=self.dataNode.node( self.dataNode.evalParm("camera"))
            if cam:
                #tn += ":"+cam.name()
                pass
        self.setText(   "("+str(self.inpoint)+") "+str(id)+":" + tn +"  (" + str(self.outpoint)+")" )     
 
    #
    def SetTrackName(self, name):
    
        self.trackName=name 
        self.UpdateLabel() 
  
        
    #geven a frame it will return the closed snapping item's frame within range.    
    def FindSnap(self, frame, frame2=False):
    
 
        #convert pixel amount to frames to get s snapping distance that's always around geiven amount of pixels at all zoomlevels
        tresh=max(1,self.parent().PixelsToFrames(15))
        
        
        #collect points of interest for snapping.  (all in/outpoints, current time, animation range)
        poi=[]
        poi.append(int(hou.playbar.timelineRange()[0]))
        poi.append(int(hou.playbar.timelineRange()[1]))
        poi.append(hou.frame())

        for item in self.parent().tracks:
            if item!=self:
                poi.append(item.GetInpoint())
                poi.append(item.GetOutpoint()+1)
        
        #find closest poi
        if frame2 != False:
        
            snap1 = min(poi, key=lambda x:abs(x-frame) )
            snap2 = min(poi, key=lambda x:abs(x-frame2) )
            
            diff=0
            
            
            if (abs(snap1-frame) < abs(snap2-frame2)):    #use snap for inpoint
                diff=snap1-frame
                snap2=frame2+diff
                                
            else:   # use snap for outpoint
                diff=snap2-frame2
                snap1 = frame+diff
  
            #check if snap distance is within treshhold range, if not ignore all snapping
            if ((abs(frame-snap1)>tresh) and (abs(frame2-snap2)>tresh)):
                snap1=frame
                snap2=frame2
                
            return snap1,snap2
        
        snap = min(poi, key=lambda x:abs(x-frame))
        
        #check if snap distance is within treshhold range, if not ignore all snapping
        if (abs(frame-snap)>tresh):
            snap=frame
        
        return snap
    
    
    #set inpoint and make sure it's valid
    def SetInpoint(self, val, rel=False, diff = 0):
        
        tmp=self.inpoint
    
        if rel:
            val = self.inpoint + val
    
        if val < self.outpoint:
            tmp = val
        else:
            tmp= self.outpoint - 1
    
        self.inpoint=int(tmp)
        
        if QtWidgets.QApplication.keyboardModifiers() == QtCore.Qt.ShiftModifier:      
            self.inpoint=self.FindSnap(tmp)
        
        self.parent().updateAudio(self.dataNode)
        
         
    
    #set Outpoint ad make sure it's valid            
    def SetOutpoint(self, val, rel=False, diff=0):
    
        tmp=self.outpoint 
      
        if rel:
            val = self.outpoint + val
            
        if val > self.inpoint:
            tmp=val
        else:
            tmp = self.inpoint + 1
        
        self.outpoint = int(tmp)     
        
        if QtWidgets.QApplication.keyboardModifiers() == QtCore.Qt.ShiftModifier:   
            self.outpoint = int(self.FindSnap(tmp))    
       
    
    #set track in/outpoints between two values, order doesn't matter. if values are equal nothing will happens        
    def SetInOutpoint(self, val1, val2, rel=False, diff=0):
    
        tmp_in=self.inpoint
        tmp_out=self.outpoint
     
        if val1 > val2:
            val1, val2 = val2, val1
    
        if val2 != val1 or rel:
        
            if rel:
                val2 = self.outpoint + val2
                val1 = self.inpoint + val1
            
            tmp_out=val2
            tmp_in=val1
        
        self.inpoint, self.outpoint  = int(tmp_in), int(tmp_out)
        
        if QtWidgets.QApplication.keyboardModifiers() == QtCore.Qt.ShiftModifier:
            self.inpoint, self.outpoint  = self.FindSnap(tmp_in, tmp_out)
    
        self.parent().updateAudio(self.dataNode)
            
    def mouseDoubleClickEvent(self, event):
       
        #double click to select track node in network editor
        
        if event.button() == QtCore.Qt.LeftButton:
          
            if QtWidgets.QApplication.keyboardModifiers() == QtCore.Qt.NoModifier:
                self.parent().gotoNode(self.dataNode)
         
            if QtWidgets.QApplication.keyboardModifiers() == QtCore.Qt.ControlModifier:
                viewer=toolutils.sceneViewer()
                cam = hou.node( self.dataNode.evalParm("camera") )    
                if cam:
                    viewer.curViewport().setCamera(cam)    
           
            if QtWidgets.QApplication.keyboardModifiers() == QtCore.Qt.AltModifier:
                cam = hou.node( self.dataNode.evalParm("camera") )    
                if cam:
                    try:
                        editor = hou.ui.paneTabOfType(hou.paneTabType.NetworkEditor)
                        editor.setCurrentNode(cam)
                        cam.setSelected(True, clear_all_selected=True)
                        p=cam.position()
                        editor.setVisibleBounds(hou.BoundingRect(hou.Vector2(p[0]-2.5,p[1]-2.5), hou.Vector2(p[0]+2.5,p[1]+2.5) ), 0.1, 0,  True)
                    except:
                        pass          
                    
    #handle mouse button events            
    def mousePressEvent(self, event):
     
        if True:
            self.__mousePressPos = None
            self.__mouseMovePos = None
            self.drag=self.dragType.No 
            globalPos = event.globalPos()
              
            localpos = event.pos()  #globalPos - self.pos() 
        
            self.oldInpoint=self.inpoint
            self.oldOutpoint=self.outpoint
            
           
             
            #LEFT 
            if event.button() == QtCore.Qt.LeftButton or event.button() == QtCore.Qt.RightButton or event.button() == QtCore.Qt.MiddleButton   :
                self.__mousePressPos = event.globalPos()
                self.__mouseMovePos = event.globalPos()
    
                    
                if self.parent().lastSelected!=None and QtWidgets.QApplication.keyboardModifiers() == QtCore.Qt.ShiftModifier:
                
                    col=[]
                    start=False
          
                    for item in self.parent().tracks:
                        
                        if item==self.parent().lastSelected or start:
                           
                            start=True
                            col.append(item)
                            if item==self:
                                start=False
                                break
                    if start==False:
                        for i in col:
                            i.SetSelected(True,True)
                    
                            pass
                          
                        
                
                if not self.selected and not QtWidgets.QApplication.keyboardModifiers() == QtCore.Qt.ControlModifier and not   QtWidgets.QApplication.keyboardModifiers() == QtCore.Qt.ShiftModifier:    
                    self.SetSelected(True)   
                
                if QtWidgets.QApplication.keyboardModifiers() == QtCore.Qt.ControlModifier:
                    self.SetSelected(not self.selected)  
                    
            if event.button() == QtCore.Qt.LeftButton:
                    
                #assume center drag
                self.style['text-align']='center'
                
                #override drag to left/right when it's near in/out handles
                if (localpos.x()   < ( 12 * hou.ui.globalScaleFactor() )):
                    self.style['text-align']='left'
    
                if (localpos.x()  > self.width()-(12 * hou.ui.globalScaleFactor())):
                    self.style['text-align']='right'
                    
                self.SetStyle()    
                
                
            #MIDDLE
            with hou.undos.disabler():
                if QtWidgets.QApplication.keyboardModifiers() != QtCore.Qt.ShiftModifier:
                    if event.button() == QtCore.Qt.MiddleButton and not self.parent().currentSequence.isTemplateFlagSet():
                        if hou.ui.displayMessage("Sequencer is currently in Automatic Mode.\nDo you want to enable Manual Mode?", buttons=("Yes", "No")) == 0:
                            self.parent().currentSequence.setTemplateFlag(True)
                
                    if event.button() == QtCore.Qt.MiddleButton and self.parent().currentSequence.isTemplateFlagSet():
                    
                        cnode = self.parent().currentSequence.inputs()[self.parent().currentSequence.evalParm("input")]
            
                        if (self.dataNode == cnode):
                            #hou.playbar.setPlaybackRange(self.GetInpoint(), self.GetOutpoint()  )     
                            pass
                    
                    
                        self.forceThisTrack()         
                

                        if QtWidgets.QApplication.keyboardModifiers() == QtCore.Qt.ControlModifier:
                            start=1000000
                            end=-1
            
                            for itemt in [self]: 
                                start=min(start,itemt.dataNode.parm("range1").eval())
                                end=max(end,itemt.dataNode.parm("range2").eval())
            
                            crange=hou.playbar.frameRange()                
                
                            needUpdate=False
                            if crange[0]>start:
                                crange[0]=start
                                needUpdate=True
                
                            if crange[1]<end:
                                crange[1]=end
                                needUpdate=True
            
                            if needUpdate:
                                hou.playbar.setFrameRange(crange[0], crange[1])
                
                
                
                            hou.playbar.setPlaybackRange(start,end)

                            self.parent().SyncNavBar()
                        super().mousePressEvent(event)
        
     

    def toggleNetworkBoxContent(self):
        with hou.undos.disabler():
            tracknames=[]
            for item in self.parent().tracks:
                tracknames.append(item.dataNode.name())
            
            for nb in hou.node("/obj").networkBoxes():
                if nb.comment()[:3].lower()=="ps:":
                    if self.dataNode.name() in nb.comment():
                        for nbn in nb.items():
                            try:
                                if nbn.name()[:1]!="_":
                                    nbn.setDisplayFlag(True)
                            except:
                                pass                    
                    else:
                        for nbn in nb.items():
                            try:
                                if nbn.name()[:1]!="_":
                                    nbn.setDisplayFlag(False)
                            except:
                                pass
                
                if nb.comment()[:4].lower()=="psf:":
                    if  nb.comment().split(":")[1] in self.dataNode.name():
                        for nbn in nb.items():
                            try:
                                if nbn.name()[:1]!="_":
                                    nbn.setDisplayFlag(True)
                            except:
                                pass                    
                    else:
                        for nbn in nb.items():
                            try:
                                if nbn.name()[:1]!="_":
                                    nbn.setDisplayFlag(False)
                            except:
                                pass                
    
    def useTrackBundles(self,   manualMode):
   
       
        doNodeBundle=False
        for bundle in hou.nodeBundles():
            if bundle.containsNode(self.dataNode):
                doNodeBundle=True
                    
        
        if doNodeBundle:
            with hou.undos.disabler():
                for bundle in hou.nodeBundles():
                    if not bundle.containsNode(self.dataNode):
                        for node in bundle.nodes():
                            if node.parm('sequencerTime')==None :
                                node.setDisplayFlag(False)
                    
         
                for bundle in hou.nodeBundles():
                    if bundle.containsNode(self.dataNode) or not manualMode:
                        for node in bundle.nodes():
                            if  node.parm('sequencerTime')==None:
                               node.setDisplayFlag(True)   
                                
    def forceThisTrack(self,skipcam=False):
   
        self.toggleNetworkBoxContent()
                                    
        #self.useTrackBundles(self.parent().currentSequence.isTemplateFlagSet())
        self.useTrackBundles(True)
      
        #inhouse stuff
        try:
            jdb.setRVCam( hou.node(self.dataNode.parm("camera").eval()) )
        except:
            pass
        
        try:   
            if self.parent().currentSequence.isTemplateFlagSet() or True:
                
                i=0
                
                for item in self.parent().tracks:
                
                
                    if item.dataNode == self.dataNode:
                        
                    
                        ctake=hou.takes.currentTake()
                        if ctake!=hou.takes.rootTake():
                            hou.takes.setCurrentTake(hou.takes.rootTake() )   
    
                        self.parent().currentSequence.parm("inputoverride").set(i)
                        item.UpdateActiveIndicator()
                        
                        if ctake!=hou.takes.currentTake():
                            hou.takes.setCurrentTake(ctake)
    
                        if not skipcam and  self.parent().currentSequence.evalParm('camswitcher'):
                            self.setThisCam()
                            
                        self.setThisTake()
                        #self.prepROP(self.dataNode)
                        
                        script=self.parent().currentSequence.evalParm("callback")
                        if script.startswith("plugin:"):
                            plug= script.split(":")[1]
                            customData=[] 
                              
                            if (ProSequencerPlugins!=None):
                                try:
                                    customData = ProSequencerPlugins.psCustomContext()
                           
                                    for cust_item in customData:
                                      
                                        if cust_item[0]==plug:
                                    
                                            cam = item.dataNode.evalParm("camera")
                                            render = "" #item.getOutputPath(item.dataNode)
                                            preview = "" #item.getPreviewPath(item.dataNode)
                                            version = item.dataNode.evalParm("version")
                                            track = item.dataNode.path()
                       
                                            cust_item[1]([cam, render, preview, version, track, self.parent(), QtWidgets.QApplication.keyboardModifiers() == QtCore.Qt.ShiftModifier, self, QtWidgets.QApplication.keyboardModifiers() == QtCore.Qt.ControlModifier ])     
                                except:
                                    print("Issue with ProSequencer Plugin")
                                    pass

                        
                        else:
                            try:
                                
                                exec(script)
                            except:
                                print("Error in callback")
                                pass
                     
                    i += 1
        except:
            pass
        
    def setThisCam(self):
    
        viewer=toolutils.sceneViewer()
        cam = hou.node(self.dataNode.evalParm("camera"))
        if not cam:
            viewer.curViewport().useDefaultCamera() 
        
        elif cam and viewer.curViewport().camera()!=cam :
            viewer.curViewport().setCamera(cam)
        
            
            
    
    def setThisAnimlayer(self):
        
        anim = hou.node(self.dataNode.evalParm("animlayer"))

        if anim:
            take=hou.takes.findTake(takeName)
            
            if take==None:
                take=hou.takes.rootTake()
            
            if hou.takes.currentTake() != take:
                hou.takes.setCurrentTake(take)        
            
    def setThisTake(self):
        
        takeName = self.dataNode.evalParm("take")

        take=hou.takes.findTake(takeName)
        
        if take==None:
            take=hou.takes.rootTake()
        
        if hou.takes.currentTake() != take:
            hou.takes.setCurrentTake(take)

                
    #handle mouse move events, all drag action happens here        
    def mouseMoveEvent(self, event):
        with hou.undos.disabler():

   
            modified=False
            
            globalPos = event.globalPos()
            localpos = event.pos()   
         
            self.style['border-left'] = self.defaultStyle['border-left']
            self.style['border-right'] = self.defaultStyle['border-right'] 
            
            if (self.drag==self.dragType.No):
            
                self.outpoint_old=self.outpoint
                self.inpoint_old=self.inpoint
                try:
                
                    self.userOffset = self.parent().getAuxByNote(self.dataNode, "user_offset", "float", returnNone=True ) 
                except:
                    self.userOffset = None
                #assume center drag
                if (event.buttons() == QtCore.Qt.LeftButton or event.buttons() == QtCore.Qt.MiddleButton ):
                    self.drag=self.dragType.Center
                
                #override drag to left/right when it's near in/out handles
                if (localpos.x()   < ( 12 * hou.ui.globalScaleFactor() )):
                    self.style['border-left']='5px solid white'
     
                    
                    if (event.buttons() == QtCore.Qt.LeftButton ):
                        self.drag=self.dragType.Left
                        self.style['text-align']='left'
                        
                if (localpos.x()   > self.width()-(12 * hou.ui.globalScaleFactor())):
                    self.style['border-right']='5px solid white'
                    
                    if (event.buttons() == QtCore.Qt.LeftButton ):
                        self.drag=self.dragType.Right
                        self.style['text-align']='right'
            
            if event.buttons() == QtCore.Qt.MiddleButton and QtWidgets.QApplication.keyboardModifiers() == QtCore.Qt.ShiftModifier:
                currPos = self.mapToGlobal(self.pos())
                diff = globalPos - self.__mousePressPos

                if self.userOffset!=None:
                    parm=self.parent().getAuxByNote(self.dataNode, "user_offset", "float", returnParm=True ) 
                    parm.set( self.userOffset + diff.x() )


            #Handle LEFT mousebutton actions        
            if event.buttons() == QtCore.Qt.LeftButton:
               
                #get mouse move distance as a QPoint vector
                currPos = self.mapToGlobal(self.pos())
                diff = globalPos - self.__mousePressPos
                
                
                if self.drag==self.dragType.Left:
                    self.style['border-left']='5px solid white'
                    self.style['text-align']='left'
                    self.reldiff=self.inpoint
                    #self.SetInpoint(self.parent().screenToFrame(globalPos.x()))
                    self.SetInpoint(  self.inpoint_old + self.parent().PixelsToFrames(diff.x(), True  ), False, diff.x() )
                    modified=True                
                    
                  
                    #relative drag other selected tracks as well.
                    if self.trackName!="navbar":
                        for item in self.parent().tracks:
                            if (item!=self):
                                if item.selected:
                                    if QtWidgets.QApplication.keyboardModifiers() != QtCore.Qt.AltModifier:
                                        item.SetInpoint((self.inpoint -  self.reldiff), True)
                                    elif (item.GetOutpoint() == self.reldiff):
                                        item.SetOutpoint((self.inpoint -  self.reldiff), True)
                                    item.Update()
            
                if self.drag==self.dragType.Right:
                    self.style['border-right']='5px solid white'
                    self.style['text-align']='right'
                    
                    self.reldiff=self.outpoint
                    self.SetOutpoint( self.outpoint_old + self.parent().PixelsToFrames(diff.x(), True  ), False, diff.x()  )
                    modified=True
                    
                    #relative drag other selected tracks as well.
                    if self.trackName!="navbar":
                        for item in self.parent().tracks:
                            if (item!=self):
                                if item.selected:
                                    if QtWidgets.QApplication.keyboardModifiers() != QtCore.Qt.AltModifier:
                                        item.SetOutpoint((self.outpoint -  self.reldiff), True)
                                    elif (item.GetInpoint() == self.reldiff ):
                                        item.SetInpoint((self.outpoint - self.reldiff), True)
                                    
                                    item.Update()
    
                
                if self.drag==self.dragType.Center:
                    self.style['text-align']='center'
                    
                    if not QtWidgets.QApplication.keyboardModifiers() == QtCore.Qt.AltModifier:
                        self.reldiff=self.inpoint
                        self.SetInOutpoint(  self.inpoint_old + self.parent().PixelsToFrames(diff.x(), True), self.outpoint_old + self.parent().PixelsToFrames(diff.x(),True), False, diff.x() )
                        modified=True
                        
                        #relative drag other selected tracks as well.
                        if self.trackName!="navbar":
                            for item in self.parent().tracks:
                                if (item!=self):
                                    if item.selected:
                                        item.SetInOutpoint( (self.inpoint - self.reldiff), (self.inpoint - self.reldiff),     True)
                                        item.Update()
                    else:
                        #alt drag to re-order tracks
                        offset = int(diff.y()/self.parent().getTrackHeight())
                        if offset!=0:
                        
                            self.__mousePressPos.setY(globalPos.y())
                            diff = globalPos - self.__mousePressPos
                        
                            #drag (multple) up and check for ceiling limit
                            if (offset<0):
                                stop=True
                                      
                                for item in self.parent().tracks:
                                    if item.selected:
                                        stop = stop & (self.parent().tracks.index(item) != 0 ) 
                                
                                if stop:    
                                    for item in (self.parent().tracks):
                                        if item.selected:
                                            lpos=self.parent().tracks.index(item)
                                            b=self.parent().tracks.pop(lpos)
                                            self.parent().tracks.insert( lpos+offset,b)
                            #drag (multiple down and check fro floro limit                
                            if (offset>0):
                                stop=True
                                      
                                for item in self.parent().tracks:
                                    if item.selected:
                                        stop = stop & (self.parent().tracks.index(item) != len(self.parent().tracks)-1 ) 
                                
                                if stop:    
                                    for item in reversed(self.parent().tracks):
                                        if item.selected:
                                            lpos=self.parent().tracks.index(item)
                                            b=self.parent().tracks.pop(lpos)
                                            self.parent().tracks.insert( lpos+offset,b)
                        
                            
                            #update trackposition on re-order
                            if offset!=0:
                                self.parent().positionTracks()
                                modified=True
                                
                
                
                
            
                #Update visuals for new in/out points
                if modified:
                    self.Update()
                    self.parent().needsSave=True
                    self.parent().SaveSequence()
    
          
                self.__mouseMovePos = globalPos
            
            self.SetStyle()
        
        super().mouseMoveEvent(event)
    
    def leaveEvent(self, event):
        # self.factor controls background brightness - 80 is dark
        self.style['border-left'] = self.defaultStyle['border-left'] 
        self.style['border-right'] = self.defaultStyle['border-right']
        self.style['text-align']=self.defaultStyle['text-align']
        self.SetStyle()
 
        
    #event for mousebutton release        
    def mouseReleaseEvent(self, event):
      
        self.drag=self.dragType.No
        self.style['text-align']='left'
        self.SetStyle() 
       
        if self.oldInpoint!=self.inpoint or self.oldOutpoint!=self.outpoint:
            with hou.undos.disabler():
                if self.dataNode!=None:
                    self.dataNode.parm("range1").set(self.oldInpoint)
                    self.dataNode.parm("range2").set(self.oldOutpoint)
            
            with hou.undos.group("Undo track adjustment"):
                if self.dataNode!=None:
                    self.dataNode.parm("range1").set(self.inpoint)
                    self.dataNode.parm("range2").set(self.outpoint)

        
        
        if self.__mousePressPos is not None:
            moved = event.globalPos() - self.__mousePressPos 
            if moved.manhattanLength() > 3:
                event.ignore()
                return
       
         
        
        
        
        
        if QtWidgets.QApplication.keyboardModifiers() != QtCore.Qt.ControlModifier and (event.button() == QtCore.Qt.LeftButton or not self.selected ):
            #self.SetSelected(True) 
            pass
            
        super().mouseReleaseEvent(event)
         
        
def clicked():
    pass
     

#Override/extend the Track class into a navigation track by altering a few of it's methods.  in/outpoints are limted from 0..100(%) of current global animation range 
class PsNav(PsTrack):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)  
        self.inpoint=0
        self.outpoint=100
        self.outpoint_old=100
        self.inpoint=0
        self.inpoint_old=0
        self.defaultStyle = {'background-color': '#555', 'color': '#ddd', 'border-right' : '5px solid #b98620','border-left' : '5px solid #b98620', 'text-align' : 'center' }
        self.style = self.defaultStyle.copy()
        self.SetTrackName("navbar")
        self.Update() 
        self.SetStyle()
        
    #    
    def Update(self):
        self.resize( QtCore.QSize( self.parent().PercentToScreen( self.outpoint) - self.parent().PercentToScreen( self.inpoint) , 13 * hou.ui.globalScaleFactor()) )
        self.move(QtCore.QPoint( self.parent().PercentToScreen(self.inpoint) , 4 * hou.ui.globalScaleFactor() ))
    
    #sync navbar with main timeline
    def Sync(self):
    
        shiftPressed=QtWidgets.QApplication.keyboardModifiers() == QtCore.Qt.ShiftModifier
    
        if shiftPressed:
            start=1000000
            end=-1
            
            for itemt in self.parent().tracks: 
 
                start=min(start,itemt.dataNode.parm("range1").eval())
                
                end=max(end,itemt.dataNode.parm("range2").eval())
            
            end=end+100
            crange=hou.playbar.frameRange()                
                
            needUpdate=False
            if crange[0]>start:
                crange[0]=start
                needUpdate=True
                
            if crange[1]<end:
                crange[1]=end
                needUpdate=True
            
            if needUpdate:
                hou.playbar.setFrameRange(crange[0], crange[1])
                
                
                
            hou.playbar.setPlaybackRange(start,end)

        
    
        start = hou.playbar.timelineRange()[0]
        end = hou.playbar.timelineRange()[1]   
        start2 = hou.playbar.playbackRange()[0]
        end2 = hou.playbar.playbackRange()[1]
        r =  end - start
        p1=((start2-start)/r) * 100
        p2=((end2)/r) * 100
        self.inpoint = max(0,p1)
        self.outpoint = min(p2,100)
        self.UpdateRange()
        
    
    #refreshes everything when the navbar is changed    
    def UpdateRange(self):
        start=hou.playbar.timelineRange()[0]
        end = hou.playbar.timelineRange()[1]
       
        l =  end -start
        self.parent().range_start =start + ((self.inpoint/100.0) * l) 
        self.parent().range_end = end - (((100-self.outpoint) / 100.0) * l )
        self.parent().outputPlaybarEvent()
        self.parent().positionTracks()
       
        
    #set inpoint and make sure it's valid
    def SetInpoint(self, val, rel=False, diff = 0):
        val=self.parent().PixelsToPercentage(diff)
        self.inpoint = self.inpoint_old + val 
        self.inpoint = max(0, self.inpoint)       
        self.inpoint = min(self.inpoint, self.outpoint-2)       
        self.UpdateRange()    
        
    #set Outpoint ad make sure it's valid            
    def SetOutpoint(self, val, rel=False, diff=0):
        val=self.parent().PixelsToPercentage(diff)
        self.outpoint = self.outpoint_old + val 
        self.outpoint = min(100, self.outpoint)            
        self.outpoint = max(self.inpoint+2, self.outpoint)    
        self.UpdateRange()
    
    #set track in/outpoints between two values       
    def SetInOutpoint(self, val1, val2, rel=False, diff = 0):
        val=self.parent().PixelsToPercentage(diff)
        diff=abs(self.outpoint - self.inpoint )
        self.inpoint = self.inpoint_old + val    
        self.outpoint = self.outpoint_old + val 
        
        if self.inpoint<0:
            self.inpoint=0
            self.outpoint=diff
            
        if self.outpoint>100:
            self.inpoint=100-diff
            self.outpoint=100
        
        self.UpdateRange()
        
    def SetSelected(self, state):
        pass
         
#main ProSequencer Class, holds everything    
class ProSequencer(QtWidgets.QWidget):

    #constructior
    def __init__(self, paneTab):
        QtWidgets.QWidget.__init__(self)
        self.paneTab = paneTab
        self.setAcceptDrops(True)
        self.currentSequence = None
        # menu bar
        #self.menu_bar = QtWidgets.QMenuBar(self)
        self.tracks=[]
        self.current_track = None
        self.needsSave=False 
        self.SetPaneLabel("None")
        self.focus = False
        self.currentAudio=None
        self.lastSelected=None
        self.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self.on_context_menu)

        #Do housekeeping playbar event across multiple ProSequencer panels
       
    
        self.navBar = PsNav(self)
        self.range_start = hou.playbar.timelineRange()[0]
        self.range_end = hou.playbar.timelineRange()[1]
        self.navBar.Sync()
        #self.createTrackNode("mynode", hou.node('/obj/ProSequencerData/switch1') )
        w= 60 * hou.ui.globalScaleFactor()
        pos=3 
 
        self.button_sync=QtWidgets.QPushButton(self) 
        self.button_sync.resize( QtCore.QSize( w , 15 * hou.ui.globalScaleFactor()) )
        self.button_sync.move(QtCore.QPoint(4 * hou.ui.globalScaleFactor(),pos * hou.ui.globalScaleFactor() ))
        self.button_sync.setStyleSheet("QPushButton {padding: 0; font-size: "+str(int(12 * hou.ui.globalScaleFactor()))+"px}")
        self.button_sync.setText("Home") 
        self.button_sync.clicked.connect(self.SyncNavBar)
        pos += 40
        
        self.scrubhead=QtWidgets.QPushButton(self) 
        
        self.outputPlaybarEvent()
        
    def setEvents(self):
        hou.playbar.clearEventCallbacks()
 
        validEvents=[]
        for item in list( (x for x in hou.ui.paneTabs() if "ProSequencer" in x.name() )):
            ps=item.activeInterfaceRootWidget()
            if ps:
                validEvents.append(ps.outputPlaybarEvent)
            
            
        for pitem in hou.playbar.eventCallbacks():
      
            if pitem.im_class.__name__ == "ProSequencer":
                if not pitem in validEvents:
                    hou.playbar.removeEventCallback(pitem)
                  
        
        if not self.outputPlaybarEvent in hou.playbar.eventCallbacks():          
          
            hou.playbar.addEventCallback(self.outputPlaybarEvent)
                
    
    #        
    def SyncNavBar(self):
        self.navBar.Sync()
    
    #    
    def dragEnterEvent(self, event):
        event.acceptProposedAction()

    
    def keyReleaseEvent(self, event):
        if event.key()==90:
            self.LoadSequence(self.currentSequence)
        
    def on_context_menu(self, point):
        with hou.undos.disabler():
            self.popMenu = QtWidgets.QMenu(self)         
            self.popMenu.addSeparator()
    
            options=[]
            self.popMenu.addSeparator()
            
              
            node_type = hou.nodeType(hou.sopNodeTypeCategory(), "switch")
            for item in node_type.instances():
                if next((x for x in item.parms() if x.name() == "timeOverride"), False):
                    if self.currentSequence==None or item.path()!=self.currentSequence.path():
                        options.append([item, self.popMenu.addAction('Load "'+item.path()+'"' ),"load"])
                        
                      
            
            options.append([ False , self.popMenu.addAction('Add new Sequence'),"newseq"])

            if self.currentSequence != None:
                options.append([ False , self.popMenu.addAction('Add new Track'),"newtrack"])    
            
          
            try:
                if self.currentSequence != None and self.currentSequence.inputs()[0].parm('notefile1_2')!=None:
                    if  self.currentSequence.inputs()[0].parm('notefile1_2').eval()=="json":
                        options.append([ False , self.popMenu.addAction('Export JSON'),"exportjson"])          
            except:
                pass
                    
            action = self.popMenu.exec_(self.mapToGlobal(point))
    
            for item in options:
                if item[1]==action:
                    node=item[0]
                    
                    if (item[2]=="exportjson"):
                        print("exporting")
                     
                        seq=hou.node('/obj/Sequences/edit')


                        out={}
                        out["sequence"]=self.currentSequence.name()
                        out["fps"]=hou.fps()
                        
                        tr=[]
                        for tr_item in self.currentSequence.inputs():
                            tr.append({
                            "camera":tr_item.parm('camera').evalAsNode().name(),
                            "camera_parent": tr_item.parm('camera').evalAsNode().parent().name(),
                            "in":int(tr_item.evalParm('range1')),
                            "out":int(tr_item.evalParm('range2'))
                            }
                            )
                            
                           
                        out["tracks"]=tr
                        
                      
                        
                        with open(self.currentSequence.inputs()[0].evalParm('auxfile1'), 'w') as outfile:
                            json.dump(out, outfile, sort_keys=True, indent=4)
                     
                     
                    if (item[2]=="newseq"):
                        
                        tnode = hou.node("/obj/Sequences")
                        if not tnode:
                            tnode=hou.node("/obj").createNode("null")
                            tnode.setName("Sequences", True)
                            for pitem in tnode.children(): pitem.destroy()
                        
                        s=tnode.createNode("switch")
                        s.setName("sequence001", True)
                        
                        self.createSequenceNode( "sequence" , s)
                        self.LoadSequence(s)
                        
                        t=tnode.createNode("null")
                        t.setName("Track001", True)
                        s.setInput(0, t)
                        t.moveToGoodPosition()
                        s.moveToGoodPosition()
                    
                        node=s
                    
                    if (item[2]=="load" or item[2]=="newseq"):
                      
                        #check is there is already a pane using this sequence, if so switch to it and ignore drop
                        for pitem in hou.ui.paneTabs():
                      
                            if pitem.name() ==  "ProSequencer_" +  node.path().replace("/","_"):  
                                pitem.setIsCurrentTab()
                                return False
               
                        #if not then then load/create new sequence
                        if node.parm("timeOverride"):
                            self.LoadSequence(node)
                        else:
                            self.createSequenceNode( "sequence" , node)
                            self.LoadSequence(node)
     
                    if (item[2]=="newtrack"):
                        s = self.currentSequence
                        if (s != None):
                            with hou.undos.group("Add Track"):  
                                t=self.currentSequence.parent().createNode("null")
                                t.setName("Track001", True)
                                s.setInput(len(self.currentSequence.inputs()), t)
                                t.moveToGoodPosition()
                                
        
    #Handle drop events on pane    
    def dropEvent(self, event, **kwargs ):
        ctake=hou.takes.currentTake()
        hou.takes.setCurrentTake(hou.takes.rootTake() )   
        
        parts=event.mimeData().text().split('\t')
  
        for part in parts:
            node=hou.node(part)
          
            if node:
                if node.type().name()=='switch':
                
                    #check is there is already a pane using this sequence, if so switch to it and ignore drop
                    for item in hou.ui.paneTabs():
                        if item.name() ==  "ProSequencer_" + node.path().replace("/","_"):  
                            item.setIsCurrentTab()
                            hou.takes.setCurrentTake( ctake )
                            return False
                
                    #if not then then load/create new sequence
                    if node.parm("timeOverride"):
                        self.LoadSequence(node)
                    else:
                        self.createSequenceNode( "sequence" , node)
                        self.LoadSequence(node)
                
                
                #init switcher        
                elif node.type().name()=='switcher'  and self.currentSequence :
                    node.parm("camswitch").setExpression('ch("'+self.currentSequence.path()+'/input")', hou.exprLanguage.Hscript)
  
                    self.updateDependends()     
                
                #init thorugh cam                
                elif node.type().name() == 'cam':
                
                    #create switch node if none active
                    if self.currentSequence == None:
                   
                        shots=hou.node("/obj/shots")
                        
                        if not shots:
                            shots = hou.node("/obj").createNode("null")
                            shots.setName("Sequences")
                            
                            for item in shots.children():
                                item.destroy()
                                
                        seq=shots.createNode("switch")
                        seq.moveToGoodPosition()
                        self.createSequenceNode( "sequence" , seq)
                        seq.setName("Sequence",True )
                        self.LoadSequence(seq)
                    
                    #add tracks for cam to sequence     
                    else:
 
                        allow=True
                        
                        for item in self.tracks:
                            if item.dataNode.parm("camera").evalAsNode() == node:
                                allow=False    
                                print("cam already in sequence")
                            
                        if allow:    
                            new=self.currentSequence.parent().createNode("null")
                            new.setName(node.name(), True )
                            new.moveToGoodPosition()
                            self.currentSequence.setInput(len(self.currentSequence.inputs()), new)
                            new.parm("camera").set(node.path())
                                                    
                            range=self.getKeyframeRange(node)
                            
                            if range[0]!=range[1]:
                                new.parm("range1").deleteAllKeyframes()
                                new.parm("range2").deleteAllKeyframes()
                                new.parm("range1").set(range[0])
                                new.parm("range2").set(range[1])
                                self.LoadSequence(self.currentSequence)
                                
                                
                                
                #init through null            
                elif node.type().name() == 'null':
                    print("adding null")
                    #create switch node if none active
                    if self.currentSequence == None:
                   
                        shots=hou.node("/obj/shots")
                        
                        if not shots:
                            shots = hou.node("/obj").createNode("null")
                            shots.setName("Sequences", True)
                            
                            for item in shots.children():
                                item.destroy()
                                
                        seq=shots.createNode("switch")
                        seq.moveToGoodPosition()
                        self.createSequenceNode( "sequence" , seq)
                        seq.setName("Sequence",True )
                        self.LoadSequence(seq)
                    
                    #add tracks for cam to sequence     
                    else:
                      
                        allow=True
                        
                        for item in self.tracks:
                            try:
                                if item.dataNode.parm("auxop1").evalAsNode() == node:
                                    allow=False    
                            except:
                                print("skipping: " + node.name())
                                pass
                            
                        if allow:    
                            new=self.currentSequence.parent().createNode("null")
                            
                            self.createTrackNode( "convert", new)
                            
                            new.setName(node.name(), True )
                            new.moveToGoodPosition()
                            self.currentSequence.setInput(len(self.currentSequence.inputs()), new)
 
                            
                            
                            new.parm("auxop").set(1)
                            new.parm("auxop1").set(node.path())
                            new.parm("auxfloat").set(1)
                            
                            
                            new.parm("auxfloat1").set(int(not "." in node.name()))
                            
                            new.parm("notefloat1").set("single_frame")
                            
                            
                            if hou.node("/out/To_Unity_FBX")!=None:
                                new.parm("rop").set("/out/To_Unity_FBX")

                                
                            new.parm("renderoutput").set("{YHMP_root}/Unity/{YHMP_project}/Assets/Scenes/{YHMP_house}/fbx/{YHMP_object}.fbx")
                            
                                                    
                            range=self.getKeyframeRange(node)
                            
                            if range[0]!=range[1]:
                                new.parm("range1").deleteAllKeyframes()
                                new.parm("range2").deleteAllKeyframes()
                                new.parm("range1").set(range[0])
                                new.parm("range2").set(range[1])
                                self.LoadSequence(self.currentSequence)

                else:
                    pass
                    #new=self.currentSequence.parent().createNode("null")
                    #new.setName("track_for_"+node.name(), True )
                    #new.moveToGoodPosition()
                    #self.currentSequence.setInput(len(self.currentSequence.inputs()), new)
                    #new.setInput(0, node)
                 
                        
        
        hou.takes.setCurrentTake( ctake )
        
        event.accept()
        return True
        
   
    #Update nodes that are referencing the main sequence node
    def updateDependends(self):    
        if self.currentSequence:
            for item in self.currentSequence.dependents():
                if item.type().name()=="switcher":
                              
                    for i, input in enumerate(item.inputs()):
                        item.setInput(i, None)
                    
                    
                    for i, track in enumerate(self.tracks):
                        try:
                            cam = hou.node( track.dataNode.evalParm("camera") )
                            item.setInput(i, cam , 0)
                        except:
                            print("failed to connect camera from track "+str(i)+" on '"+item.path()+"'")

                 
    #save sequence to current sequence    
    def SaveSequence(self):
 
        hou.session.ps_last_take_time=-1
        
        ctake=hou.takes.currentTake()
        if hou.takes.rootTake()!=ctake:
            hou.takes.setCurrentTake(hou.takes.rootTake())  
        
        #save track to data nodes
        for item in self.tracks:
        
            if item.dataNode:
                #avoid triggering updates in the node tree when nothing has been changed
                if item.dataNode.evalParm("range1")!=item.inpoint:
                    item.dataNode.parm("range1").set(item.inpoint)
                    item.dataNode.parm("range1").deleteAllKeyframes()
                    item.dataNode.parm("range1").set(item.inpoint)
                    
                    
                if item.dataNode.evalParm("range2")!=item.outpoint:
                    item.dataNode.parm("range2").deleteAllKeyframes()
                    item.dataNode.parm("range2").set(item.outpoint)
            #check is number of nodes and order still matched.        
            skip=self.ValidateOrder()
            
            #set correct order in sequence node is required
            if not skip:       
                for i, item in enumerate(self.tracks):
                    self.currentSequence.setInput(i, item.dataNode, 0)
                
            #update dependend switches
            self.updateDependends()
            
        self.needsSave=False
        if ctake!=hou.takes.currentTake():
            hou.takes.setCurrentTake( ctake )

    #return last and firstkey of any property on a node.
    def getKeyframeRange(self, node):
        first=1000000
        last=-1000000
        for item in node.parms():
            for key in item.keyframes():
                if key.expression()!='lock(1)':
                
                    if key.frame()>last or last==-1000000:
                            last=key.frame() 
                    if key.frame()<first or first==1000000:
                            first=key.frame()       

        if last==-1000000 or first==1000000:
            return [0,0]

        if last==-1000000 and first!=1000000:
            return [first,first]
        
        if last!=-1000000 and first==1000000:
            return [last,last]
                        
        return [first,last]
    
    def gotoNode(self, node, message = False ):

        nodeContext = node.path().split('/')[1]
        
        ptab = None
        for item in hou.ui.paneTabs():
            if item.type() == hou.paneTabType.NetworkEditor:
                 if nodeContext == item.currentNode().path().split('/')[1]:
                    ptab = item
                    break
        if ptab == None:
            ptab = hou.ui.paneTabOfType(hou.paneTabType.NetworkEditor)
        
        if ptab == None:
            return False
                    
        ptab.setIsCurrentTab()
        ptab.setCurrentNode(node)
        node.setSelected(True, clear_all_selected=True)
        
        p=node.position()
        ptab.setVisibleBounds(hou.BoundingRect(hou.Vector2(p[0]-2.5,p[1]-2.5), hou.Vector2(p[0]+2.5,p[1]+2.5) ), 0.1, 0,  True)
        
        if message:
            ptab.flashMessage( None, "ROP set to track", 2)
            
    def mouseDoubleClickEvent(self, event):
        #double click to select track node in network editor
       
        #LEFT
        if event.button() == QtCore.Qt.LeftButton:
            if QtWidgets.QApplication.keyboardModifiers() == QtCore.Qt.NoModifier:
                if self.currentSequence:
                    self.gotoNode(self.currentSequence)
                    
                    
                
    #discard all tracks in  sequence   
    def UnloadSequence(self):
        for item in self.tracks:
           item.setParent(None)
           del item
        self.tracks[:]=[]
        self.currentSequence = None
        self.SetPaneLabel("None")
        pane = self.paneTab
        pane.setName("ProSequencer_None")
    
    #
    def SetPaneLabel(self,label):
            pane = self.paneTab
            

            pane.setLabel("PS:"+label)
            
            if label!="None":
                pane.setName("ProSequencer_" +  label.replace("/","_"))
            
            
    #load a sequence into the panel    
    def LoadSequence(self, seqNode ):
 
        if not seqNode:
            return False

        #check if node is valid (eg. not deleted)
        try:
            tmp=seqNode.name()
        except:
            return False
            
        stat=True 
        #simple check if it's a valid node by verifying specific proSequencer parameter presence.
        if seqNode.parm("timeOverride"):    
            self.UnloadSequence()
            self.currentSequence = seqNode 
            self.SetPaneLabel(seqNode.path())
            for i, item in enumerate((seqNode.inputs())):
            
                    if item.type().name()=='null':
                        track = self.AddTrack(i)
                        stat = stat & self.LoadTrack(track, item) 
                    
                    
            #add/update event handler to update sequencer panel if something relevant changed to the sequence switch node
            seqNode.removeAllEventCallbacks() 
            seqNode.addEventCallback( (hou.nodeEventType.NameChanged, hou.nodeEventType.BeingDeleted, hou.nodeEventType.FlagChanged, hou.nodeEventType.AppearanceChanged, hou.nodeEventType.InputRewired) , self.OnSeqNodeChange)
         
            self.updateLastSequence()    
            
  
            
        return stat           
    
     
    #when something on a track node changes brute-force reload the whole sequence.. could use some optimisation
    def OnTrackNodeChange(self, node, event_type, **kwargs):
       
        skip=True
         
        
        if event_type== hou.nodeEventType.ParmTupleChanged:
            if kwargs.get('parm_tuple'):
          
                if  kwargs.get('parm_tuple')[0].name()=='camera':
                    #skip=False
                    pass
                if  (kwargs.get('parm_tuple')[0].name()=='range1' or kwargs.get('parm_tuple')[0].name()=='range2') and not self.focus:
                    skip=False
                    
                if  kwargs.get('parm_tuple')[0].name()=='audio' or  kwargs.get('parm_tuple')[0].name()=='syncaudio':
   
                    self.updateAudio(node)
        
        
        #filter out events that need a refresh of the sequencer panel
        if kwargs.get('change_type')  == hou.appearanceChangeType.Color:
            skip=False
        
        if event_type == hou.nodeEventType.FlagChanged:
            skip=False
            
            
        if event_type == hou.nodeEventType.NameChanged:
            skip=False  
            
        if event_type == hou.nodeEventType.BeingDeleted:
            skip=False  
        
        if not skip:
            self.LoadSequence(self.currentSequence)
            pass
    #        
    def leaveEvent(self, event):
        self.focus=False
    #
    def enterEvent(self, event):
        self.focus=True 
     
    #cross system explore folder 
    def openFolder(self, path):
    
        if os.path.isdir(path):
    
            if platform.system() == "Windows":
                os.startfile(path)
            elif platform.system() == "Darwin":
                subprocess.Popen(["open", path])
            else:
                subprocess.Popen(["xdg-open", path])
        else:
            print("Folder does not exist (yet). Output folders are usually created at rendertime")
     
    
    #Check if order of tracks matches input order on sequence node        
    def ValidateOrder(self):
        if self.currentSequence!=None:
            skip=len(self.tracks) == len(self.currentSequence.inputs() )
            if skip:
                for i, item in enumerate((self.currentSequence.inputs())):            
                    if item != self.tracks[i].dataNode:
                        skip=False 
            return skip
        return True   
    
    #when something on a sequence node changes brute-force reload the whole sequence.. could use some optimisation
    def OnSeqNodeChange(self, node, event_type, **kwargs):
           
        if event_type == hou.nodeEventType.BeingDeleted:
        
            #self.UnloadSequence()
            return False
        try:
            skip= self.ValidateOrder()
            
            if node==self.currentSequence:
                if kwargs.get('parm_tuple') and not self.ValidateOrder():
                    skip=False
                    
                if event_type == hou.nodeEventType.FlagChanged:
                    node.cook(True)
                    self.outputPlaybarEvent()
                        
                if event_type == hou.nodeEventType.NameChanged:
                    skip=False        
                 
                if not skip and  QtWidgets.QApplication.keyboardModifiers() != QtCore.Qt.AltModifier: 
                    self.LoadSequence(self.currentSequence)     
                    pass
        except AssertionError as error:
            print(error)
                
    #Load meta data from a tracknode in to a track object in the sequencer     
    def LoadTrack(self, track, trackNode):
    
        if not trackNode.parm("psversion"):
            self.createTrackNode( "convert", trackNode)
    
         
        if trackNode.parm("psversion"):
            track.SetInOutpoint(trackNode.evalParm('range1') ,trackNode.evalParm('range2'))
            track.SetTrackName(trackNode.name())
            track.dataNode = trackNode 

            c=trackNode.color()
            track.defaultStyle['border-right'] = '5px solid rgb(' + str(int(c.rgb()[0] * 255)) + ',' + str(int(c.rgb()[1] * 255))+ ','+ str(int(c.rgb()[2] * 255))+')'
            track.defaultStyle['border-left'] = '5px solid rgb(' + str(int(c.rgb()[0] * 255)) + ',' + str(int(c.rgb()[1] * 255))+ ','+ str(int(c.rgb()[2] * 255))+')'
         
            track.style=track.defaultStyle.copy()
            track.SetStyle()
            
            track.SetEnabled(not trackNode.isBypassed())
            
            #add/update event handler to update sequencer panel if something relevant changed to the track nodes
            trackNode.removeAllEventCallbacks() 
            trackNode.addEventCallback( (hou.nodeEventType.NameChanged, hou.nodeEventType.BeingDeleted, hou.nodeEventType.FlagChanged, hou.nodeEventType.AppearanceChanged,hou.nodeEventType.ParmTupleChanged ) , self.OnTrackNodeChange)
            track.Update()
            return True
        return False
    
    #Adds a track with given id. Returns false if Id is not unique
    def AddTrack(self,id):
       
        track = PsTrack(self)
        track.show()   #for when tracks are added from a callback 
        self.tracks.append(track)

        return track 

                    
    #Handle playbar events     
    def outputPlaybarEvent(self, event_type = "", frame = hou.frame()):
    
                          
        try:
    
            frame = hou.frame()   #fix for some wierdness where frame is sometimes incorrectly set to 1 by callback       
            
            if self.currentSequence != None:
                frame = self.currentSequence.evalParm("timeOverride")    
            
            if hasattr(self , 'scrubhead'):
                self.scrubhead.resize( QtCore.QSize( max(3, self.FramesToPixels(1))   , 800 * hou.ui.globalScaleFactor()) )
                self.scrubhead.move(QtCore.QPoint(self.frameToScreen(frame),17 * hou.ui.globalScaleFactor() ))
                self.scrubhead.setStyleSheet("QPushButton {border: none; background: rgba(185,134,32 ,10%); border-left: 1px solid rgba(185,134,32,50%); border-right: 1px solid rgba(185,134,32,50%)}")
      
            if self.currentSequence!=None :
                
                #do camera switching when enabled
                if self.currentSequence.evalParm('camswitcher') and self.isActive() and not self.currentSequence.isBypassed() :
                 
                    viewer=toolutils.sceneViewer() 
                    
                
    
                    if viewer.curViewport().camera()!=None:
                        cam = hou.node(self.currentSequence.inputs()[self.currentSequence.evalParm("input")].evalParm("camera"))    
                           
                            
                        if cam and viewer.curViewport().camera()!=cam:
                            if self.currentSequence.evalParm("input")<=len(self.tracks):
                                self.tracks[self.currentSequence.evalParm("input")].toggleNetworkBoxContent()
                                self.tracks[self.currentSequence.evalParm("input")].useTrackBundles(True)
                                
                                
                            viewer.curViewport().setCamera(cam)
                            pass
                            
                        
                
                #handle take switching
                if self.isActive() and not self.currentSequence.isBypassed() :
    
                    takeName = self.currentSequence.inputs()[self.currentSequence.evalParm("input")].evalParm("take")
                    take=hou.takes.findTake(takeName)
               
                    if take==None or (not self.currentSequence.inputs()[self.currentSequence.evalParm("input")].evalParm("onTrack")):
                        take=hou.takes.rootTake()
                    
                    if hou.takes.currentTake() != take and  self.getSessionVar("ps_last_take_time", -1) != hou.frame() and not self.currentSequence.isTemplateFlagSet() :
                        hou.takes.setCurrentTake(take)
                        hou.session.ps_last_take_time=hou.frame()
                
                #handle audio mixing
    
                if self.isActive() and not self.currentSequence.isBypassed() :
                    self.updateAudio( self.currentSequence.inputs()[self.currentSequence.evalParm("input")] )
                
                #update active indicator
                    if self.tracks[0]!=None:
                        self.tracks[0].UpdateActiveIndicator()
                
        except:
            self.currentSequence=None
            print("Error handling time event")
            print(sys.exc_info()[0])
            pass 
   
    def getAuxByNote(self, trackNode, note, type, returnNone=False, returnArray=False, returnParm=False):
        if type=="op":
                out=[]
                for index in range(0, trackNode.evalParm("auxop")):
                        if trackNode.parm("noteobj"+str(index+1)).eval()==note:
                                foundnodes=trackNode.parm("auxop"+str(index+1)).evalAsNodes()
                                if "/" not in trackNode.parm("auxop"+str(index+1)).eval():
                                    foundnodes=trackNode.parm("auxop"+str(index+1)).eval().split()
                                for itemx in foundnodes:
                                    out.append(itemx)
                if len(out)>0:
                    return out
                    
                if returnNone:
                    return None
                return []      
                
        if type=="float":
                out=[]
                for index in range(0, trackNode.evalParm("auxfloat")):
                        if trackNode.parm("notefloat"+str(index+1)).eval()==note:
                                out.append(trackNode.parm("auxfloat"+str(index+1)).eval())
                                if not returnArray:
                                    if returnParm:
                                        return trackNode.parm("auxfloat"+str(index+1))
                                    return trackNode.parm("auxfloat"+str(index+1)).eval()

                
                if returnArray:
                    return out
                                
                if returnNone:
                    return None                                
                return 0                   
            
    #Updates audio for current track        
    def updateAudio(self, tnode ):
        try:
            tnode =  self.currentSequence.inputs()[self.currentSequence.evalParm("input")]

            if tnode and not self.currentSequence.evalParm("noaudio"):
                file = tnode.evalParm("audio") 
                if  self.currentAudio != file:
                    self.currentAudio = file
 
                    hou.audio.setAudioFileName( file )   
                    hou.audio.useAudioFile() 
                    hou.audio.useTimeLineMode() 
            
                offset=self.getAuxByNote( tnode, "audio_offset", "float")                
                
                if file:    
                    if  tnode.evalParm("syncaudio"):
                        hou.audio.setAudioFrame(tnode.evalParm("range1") +offset )
                    else:
                        hou.audio.setAudioFrame(0 + offset)  
                    
                    
                if not file:
                    hou.audio.setAudioFileName( "" )
        except:
            pass
                
    #Convertes a length in pixels to a lenght in frames. Has option to round output to integer frame numbers  
    def FramesToPixels(self, frame ):
        
        gsf = hou.ui.globalScaleFactor()
    
        #pixels
        seq_width = self.width() 

        #frames
        seq_frames =  self.range_end - self.range_start  
        
        #pixel to frame multiplier  (so pixel * ftp = frame nr)
        ptf = (seq_width * 1.0) / (seq_frames*1.0) 
             
        return( int(frame * ptf)) 
        
        
    #Convertes a length in pixels to a lenght in frames. Has option to round output to integer frame numbers  
    def PixelsToFrames(self, pixel, wholeFrames=False):
        
        gsf = hou.ui.globalScaleFactor()
    
        #pixelshou.ui.globalScaleFactor()
        seq_width = self.width() 

        #frames
        seq_frames =  self.range_end - self.range_start  
        
        #pixel to frame multiplier  (so pixel * ftp = frame nr)
        ptf =   (seq_frames*1.0) / (seq_width * 1.0)
  
        if wholeFrames:
            return( int(pixel* ptf)) 
            
        return( (pixel* ptf))   
    
    #converts a length of pixels into a percentage    
    def PixelsToPercentage(self, pixel, wholeFrames=False):
        
        gsf = hou.ui.globalScaleFactor()
    
        #pixels
        seq_width = self.width() 

        #frames
        seq_frames =  100
        
        #pixel to frame multiplier  (so pixel * ftp = frame nr)
        ptf =   (seq_frames*1.0) / (seq_width * 1.0)
  
        if wholeFrames:
            return( int(pixel* ptf)) 
            
        return( (pixel* ptf))      
    
    #Translate a pixel position in the panel to a frame number, always returns integer frames
    def screenToFrame(self, pixel):
        
        gsf = hou.ui.globalScaleFactor()
    
        #pixels
        ui_left=80 * gsf   #margin in left sife for buttons etc
        seq_width = self.width() - ui_left 

        #frames
        seq_frames =  self.range_end - self.range_start  
       
        
        #pixel to frame multiplier  (so pixel * ftp = frame nr)
        ptf =   seq_frames / seq_width
  
        return( int(((pixel - ui_left) * ptf) + self.range_start)   )  
    
    #Translate a pixel position in the panel to a frame number, always returns integer frames
    def ScreenToPercentage(self, pixel):
        
        gsf = hou.ui.globalScaleFactor()
    
        #pixels
        ui_left=80 * gsf   #margin in left sife for buttons etc
        seq_width = self.width() - ui_left 

        #frames
        seq_frames =  100
       
        
        #pixel to frame multiplier  (so pixel * ftp = frame nr)
        ptf =   seq_frames / seq_width
  
        return( (((pixel - ui_left) * ptf))   )  
        
        
    #Translate a percoent to a pixel position in the panel.     
    def PercentToScreen(self, frame):
        
        gsf = hou.ui.globalScaleFactor()
    
        #pixels
        ui_left=80 * gsf   #margin in left sife for buttons etc
        seq_width = self.width() - ui_left 

        
        #frame to pixel multiplier  (so frame * ftp = pixel pos)
        ftp = seq_width / 100

        return ( (frame * ftp) + ui_left )  
        
        
    #Translate a frame to a pixel position in the panel. Always return integer pixels    
    def frameToScreen(self, frame):
        
        gsf = hou.ui.globalScaleFactor()
    
        #pixels
        ui_left=80 * gsf   #margin in left sife for buttons etc
        seq_width = self.width() - ui_left 

        #frames
        seq_frames =  self.range_end - self.range_start  
        
        
        #frame to pixel multiplier  (so frame * ftp = pixel pos)
        ftp = seq_width / seq_frames

        return (math.floor((((frame -  self.range_start) * ftp) + ui_left)))    
   
    #Returns the height of a single track    
    def getTrackHeight(self):
        return (20 * hou.ui.globalScaleFactor() )
        
    #Returns y-position in panel for a given track number (so track 0 is on top, 1 below that, etc)   
    def idToScreen(self, id):
        return (16 * hou.ui.globalScaleFactor() + self.getTrackHeight() * id  ) + 20
    
    #Updates all track size/positions.     
    def positionTracks(self):
        self.navBar.Update()
        self.outputPlaybarEvent()
        for item in self.tracks:
             item.Update()
    
    #
    def isActive(self):
         if self.currentSequence!=None:
            return self.getSessionVar("ps_last_active") == self.currentSequence.path()
         else:
            return False
    
    #Return last use sequencer from the session
    def getLastSequencer(self):
        return hou.node( self.getSessionVar("ps_last_active") )
    
    #REturn a var from the session    
    def  getSessionVar(self, varname, default = None):
        if not hasattr(hou.session, varname):
            return default
        else:
            return getattr(hou.session, varname)   
             
    #store last active sequencer is session         
    def updateLastSequence(self):
        try:
            if self.currentSequence!=None:
                hou.session.ps_last_active = self.currentSequence.path()
            else:
                hou.session.ps_last_active = None
        except:
            hou.session.ps_last_active = None    
    # This method is called immediately before the widget is shown
    def showEvent(self, event):
 
        if self.currentSequence == None:
            node = hou.node( self.getSessionVar("ps_last_active") )
       
            if node:
                found = False
                for item in hou.ui.paneTabs():
                    if  self.paneTab.name() != "ProSequencer_" + node.path().replace("/","_") and item.name() ==  "ProSequencer_" +  node.path().replace("/","_"): 
                        found = True
                if not found:
                    self.LoadSequence(node)
            else:
                self.SetPaneLabel("None")
                pane = self.paneTab
                pane.setName("ProSequencer_None")
        
                
        self.setEvents()                
                
        self.updateLastSequence()   

    #print soft errors  levels:   0=error, 1=warning, 2=info, 3=debug
    def HandleError(self, msg, level = 0):
        if level<1:
            print(msg)
        
        
    #if closed and was active then set last_active to None    
    def closeEvent(self, event):
        if self.currentSequence!=None:
            if self.getSessionVar("ps_last_active" ) == self.currentSequence.path():
                #hou.session.ps_last_active = None
                pass
   
    # This method is called after the widget is hidden
    def hideEvent(self, event):
        pass
            
    # Called when the widget's dimensions change
    def resizeEvent(self, event):
        # Store the new size so it can be drawn to the screen later on
        self.positionTracks()
    
    # Deselect everything with click in pane    
    def mousePressEvent(self, event):
        self.updateLastSequence()    
        if event.button() == QtCore.Qt.LeftButton:
            try:
                for item in self.tracks:
                    item.SetSelected(False)
            except:
                pass
                
    def mouseMoveEvent(self, event):
        if event.buttons() == QtCore.Qt.NoButton:
            #QtWidgets.QApplication.restoreOverrideCursor()
            pass
       
    #event for mousebutton release        
    #def mouseReleaseEvent(self, event):
    
    #
    def paintEvent(self, event):
        painter = QtGui.QPainter(self).fillRect(0, 0, self.width(), self.height(), hou.qt.getColor("BackColor"))
    
          
    #
    def createTrackNode(self, trackName, convert=False):
        if True:    
            # Code for /obj/ProSequencerData/null4
            hou_node=None 
            
            if not convert:
                hou_node = self.currentSequence.parent().createNode("null", trackName , run_init_scripts=False, load_contents=True, exact_type_name=True)
            else:
                hou_node=convert
                
            hou_node.bypass(False)
            hou_node.setDisplayFlag(False)
            hou_node.hide(False)
            hou_node.setHighlightFlag(False)
            hou_node.setHardLocked(False)
            hou_node.setSoftLocked(False)
            hou_node.setSelectableTemplateFlag(False)
            hou_node.setSelected(True)
            hou_node.setRenderFlag(False)
            hou_node.setTemplateFlag(False)
            hou_node.setUnloadFlag(False)
            
            
            hou_parm_template_group = hou.ParmTemplateGroup()
            # Code for parameter template
            hou_parm_template = hou.ToggleParmTemplate("copyinput", "Copy Input (Note: Input will be still cooked if disabled)", default_value=True)
            hou_parm_template.hide(True)
            hou_parm_template_group.append(hou_parm_template)
            # Code for parameter template
            hou_parm_template = hou.ToggleParmTemplate("cacheinput", "Cache Input", default_value=False)
            hou_parm_template.hide(True)
            hou_parm_template_group.append(hou_parm_template)
            # Code for parameter template
            hou_parm_template = hou.StringParmTemplate("psversion", "versioninfo", 1, default_value=(["ps_2.1.0.0"]), naming_scheme=hou.parmNamingScheme.Base1, string_type=hou.stringParmType.Regular, menu_items=([]), menu_labels=([]), icon_names=([]), item_generator_script="", item_generator_script_language=hou.scriptLanguage.Python, menu_type=hou.menuType.Normal)
            hou_parm_template.hide(True)
            hou_parm_template_group.append(hou_parm_template)
            # Code for parameter template
            hou_parm_template = hou.SeparatorParmTemplate("sepparm2")
            hou_parm_template_group.append(hou_parm_template)
            # Code for parameter template
            hou_parm_template = hou.FolderParmTemplate("folder2", "Basic", folder_type=hou.folderType.Tabs, default_value=0, ends_tab_group=False)
            hou_parm_template.setTags({"group_type": "simple"})
            # Code for parameter template
            hou_parm_template2 = hou.FloatParmTemplate("range", "Range", 2, default_value=([1, 50]), min=0, max=10, min_is_strict=False, max_is_strict=False, look=hou.parmLook.Regular, naming_scheme=hou.parmNamingScheme.Base1)
            hou_parm_template.addParmTemplate(hou_parm_template2)
            # Code for parameter template
            hou_parm_template2 = hou.SeparatorParmTemplate("sepparm3")
            hou_parm_template.addParmTemplate(hou_parm_template2)
            # Code for parameter template
            hou_parm_template2 = hou.StringParmTemplate("camera", "Camera", 1, default_value=([""]), naming_scheme=hou.parmNamingScheme.Base1, string_type=hou.stringParmType.NodeReference, menu_items=([]), menu_labels=([]), icon_names=([]), item_generator_script="", item_generator_script_language=hou.scriptLanguage.Python, menu_type=hou.menuType.Normal)
            hou_parm_template2.setScriptCallback("hou.pwd().parm(\"camera\").set( (hou.node(hou.pwd().evalParm(\"camera\"))  or hou.node(\"/obj\") ).path() if hou.pwd().evalParm(\"camera\") != \"\" else \"\"  )")
            hou_parm_template2.setScriptCallbackLanguage(hou.scriptLanguage.Python)
            hou_parm_template2.setTags({"opfilter": "!!OBJ/CAMERA!!", "oprelative": "/obj", "script_callback": "hou.pwd().parm(\"camera\").set( (hou.node(hou.pwd().evalParm(\"camera\"))  or hou.node(\"/obj\") ).path() if hou.pwd().evalParm(\"camera\") != \"\" else \"\"  )", "script_callback_language": "python"})
            hou_parm_template.addParmTemplate(hou_parm_template2)
            # Code for parameter template
            hou_parm_template2 = hou.StringParmTemplate("rop", "ROP(s)", 1, default_value=([""]), naming_scheme=hou.parmNamingScheme.Base1, string_type=hou.stringParmType.NodeReferenceList, menu_items=([]), menu_labels=([]), icon_names=([]), item_generator_script="", item_generator_script_language=hou.scriptLanguage.Python, menu_type=hou.menuType.Normal)
            hou_parm_template2.setScriptCallbackLanguage(hou.scriptLanguage.Python)
            hou_parm_template2.setTags({"opfilter": "!!ROP!!", "oprelative": "", "script_callback": "", "script_callback_language": "python"})
            hou_parm_template.addParmTemplate(hou_parm_template2)
            # Code for parameter template
            hou_parm_template2 = hou.StringParmTemplate("deadline", "Deadline", 1, default_value=([""]), naming_scheme=hou.parmNamingScheme.Base1, string_type=hou.stringParmType.NodeReference, menu_items=([]), menu_labels=([]), icon_names=([]), item_generator_script="", item_generator_script_language=hou.scriptLanguage.Python, menu_type=hou.menuType.Normal)
            hou_parm_template2.setHelp("This DeadLine node is used for submitting a track to Deadline for rendering. Make sure the above ROP(s) and wired into it ")
            hou_parm_template2.setScriptCallback("hou.pwd().parm(\"deadline\").set( (hou.node(hou.pwd().evalParm(\"deadline\"))  or hou.node(\"/out\") ).path() if hou.pwd().evalParm(\"deadline\") != \"\" else \"\"  )")
            hou_parm_template2.setScriptCallbackLanguage(hou.scriptLanguage.Python)
            hou_parm_template2.setTags({"opfilter": "!!ROP!!", "oprelative": "/out", "script_callback": "hou.pwd().parm(\"deadline\").set( (hou.node(hou.pwd().evalParm(\"deadline\"))  or hou.node(\"/out\") ).path() if hou.pwd().evalParm(\"deadline\") != \"\" else \"\"  )", "script_callback_language": "python"})
            hou_parm_template.addParmTemplate(hou_parm_template2)
            # Code for parameter template
            hou_parm_template2 = hou.SeparatorParmTemplate("sepparm")
            hou_parm_template.addParmTemplate(hou_parm_template2)
            # Code for parameter template
            hou_parm_template2 = hou.StringParmTemplate("version", "Version", 1, default_value=([""]), naming_scheme=hou.parmNamingScheme.Base1, string_type=hou.stringParmType.Regular, menu_items=([]), menu_labels=([]), icon_names=([]), item_generator_script="", item_generator_script_language=hou.scriptLanguage.Python, menu_type=hou.menuType.Normal)
            hou_parm_template2.setJoinWithNext(True)
            hou_parm_template2.setHelp("You can use this value as a {version} token in both render and preview outputs ")
            hou_parm_template.addParmTemplate(hou_parm_template2)
            # Code for parameter template
            hou_parm_template2 = hou.StringParmTemplate("meta", "Meta Data", 1, default_value=([""]), naming_scheme=hou.parmNamingScheme.Base1, string_type=hou.stringParmType.Regular, menu_items=([]), menu_labels=([]), icon_names=([]), item_generator_script="", item_generator_script_language=hou.scriptLanguage.Python, menu_type=hou.menuType.Normal)
            hou_parm_template2.setHelp("You can use this value as a {meta} token in both render and preview outputs ")
            hou_parm_template.addParmTemplate(hou_parm_template2)
            # Code for parameter template
            hou_parm_template2 = hou.SeparatorParmTemplate("sepparm4")
            hou_parm_template.addParmTemplate(hou_parm_template2)
            # Code for parameter template
            hou_parm_template2 = hou.StringParmTemplate("renderoutput", "Render Output", 1, default_value=([""]), naming_scheme=hou.parmNamingScheme.Base1, string_type=hou.stringParmType.Regular, menu_items=([]), menu_labels=([]), icon_names=([]), item_generator_script="", item_generator_script_language=hou.scriptLanguage.Python, menu_type=hou.menuType.Normal)
            hou_parm_template2.setHelp("\n Available tokens:\n {camera}\n {rop}\n {meta}\n {version}\n {take}\n {sequence}\n {track}\n \n You can add 1 single extra character of choice iafter the '{' in the token placeholder, this will omly be included in the output if the token is not empty:\n example:  {_meta}   \n \n If you have an FBX or Alembix ROP the node set in the first 'auxOp' in the 'User Data' tab will be use as root for export. \n")
            hou_parm_template.addParmTemplate(hou_parm_template2)
            # Code for parameter template
            hou_parm_template2 = hou.StringParmTemplate("previewoutput", "Flipbook Output", 1, default_value=([""]), naming_scheme=hou.parmNamingScheme.Base1, string_type=hou.stringParmType.Regular, menu_items=([]), menu_labels=([]), icon_names=([]), item_generator_script="", item_generator_script_language=hou.scriptLanguage.Python, menu_type=hou.menuType.Normal)
            hou_parm_template2.setHelp("\n Available tokens:\n {camera}\n {meta}\n {version}\n {take}\n {sequence}\n {track}\n \n You can add 1 single extra character of choice iafter the '{' in the token placeholder, this will omly be included in the output if the token is not empty:\n example:  {_meta}   \n \n If Ffmpeg is installed you can automatically create MP4 files using a track's context menu. \n")
            hou_parm_template.addParmTemplate(hou_parm_template2)
            hou_parm_template_group.append(hou_parm_template)
            # Code for parameter template
            hou_parm_template = hou.FolderParmTemplate("folder2_1", "Advanced", folder_type=hou.folderType.Tabs, default_value=0, ends_tab_group=False)
            # Code for parameter template
            hou_parm_template2 = hou.FloatParmTemplate("sequencerTime", "Sequencer Time", 1, default_value=([0]), min=0, max=500, min_is_strict=False, max_is_strict=False, look=hou.parmLook.Regular, naming_scheme=hou.parmNamingScheme.Base1)
            hou_parm_template2.setHelp("This is the Time the track is using internally. Normally it will be looking at the connected SequenceNode's 'Sequencer Time' or fallback to global time.")
            hou_parm_template.addParmTemplate(hou_parm_template2)
            # Code for parameter template
            hou_parm_template2 = hou.SeparatorParmTemplate("sepparm5")
            hou_parm_template.addParmTemplate(hou_parm_template2)
            # Code for parameter template
            hou_parm_template2 = hou.StringParmTemplate("audio", "Audio", 1, default_value=([""]), naming_scheme=hou.parmNamingScheme.Base1, string_type=hou.stringParmType.FileReference, menu_items=([]), menu_labels=([]), icon_names=([]), item_generator_script="", item_generator_script_language=hou.scriptLanguage.Python, menu_type=hou.menuType.StringReplace)
            hou_parm_template2.setTags({"filechooser_mode": "read"})
            hou_parm_template.addParmTemplate(hou_parm_template2)
            # Code for parameter template
            hou_parm_template2 = hou.ToggleParmTemplate("syncaudio", "Sync to Inpoint", default_value=True)
            hou_parm_template2.setHelp("Audio start will be matched to inpoint of track.")
            hou_parm_template.addParmTemplate(hou_parm_template2)
            # Code for parameter template
            hou_parm_template2 = hou.SeparatorParmTemplate("sepparm6")
            hou_parm_template.addParmTemplate(hou_parm_template2)
            # Code for parameter template
            hou_parm_template2 = hou.StringParmTemplate("take", "Take", 1, default_value=([""]), naming_scheme=hou.parmNamingScheme.Base1, string_type=hou.stringParmType.Regular, menu_items=([]), menu_labels=([]), icon_names=([]), item_generator_script="", item_generator_script_language=hou.scriptLanguage.Python, menu_type=hou.menuType.Normal)
            hou_parm_template2.setHelp("The name of the Take to activate when this track is active. Can be set using track's context menu as well. Leave empty to use Main take.")
            hou_parm_template.addParmTemplate(hou_parm_template2)
            # Code for parameter template
            hou_parm_template2 = hou.StringParmTemplate("animlayer", "Anim Layer", 1, default_value=([""]), naming_scheme=hou.parmNamingScheme.Base1, string_type=hou.stringParmType.NodeReference, menu_items=([]), menu_labels=([]), icon_names=([]), item_generator_script="", item_generator_script_language=hou.scriptLanguage.Python, menu_type=hou.menuType.Normal)
            hou_parm_template2.setTags({"opfilter": "!!CHOP!!", "oprelative": "/obj"})
            hou_parm_template.addParmTemplate(hou_parm_template2)
            hou_parm_template_group.append(hou_parm_template)
            # Code for parameter template
            hou_parm_template = hou.FolderParmTemplate("folder2_2", "Track Ouput Data", folder_type=hou.folderType.Tabs, default_value=0, ends_tab_group=False)
            hou_parm_template.setTags({"group_type": "simple"})
            # Code for parameter template
            hou_parm_template2 = hou.FloatParmTemplate("duration", "Duration", 1, default_value=([0]), min=0, max=100, min_is_strict=False, max_is_strict=False, look=hou.parmLook.Regular, naming_scheme=hou.parmNamingScheme.Base1)
            hou_parm_template.addParmTemplate(hou_parm_template2)
            # Code for parameter template
            hou_parm_template2 = hou.IntParmTemplate("active", "Active", 1, default_value=([0]), min=0, max=1, min_is_strict=True, max_is_strict=True, naming_scheme=hou.parmNamingScheme.Base1, menu_items=([]), menu_labels=([]), icon_names=([]), item_generator_script="", item_generator_script_language=hou.scriptLanguage.Python, menu_type=hou.menuType.Normal, menu_use_token=False)
            hou_parm_template.addParmTemplate(hou_parm_template2)
            # Code for parameter template
            hou_parm_template2 = hou.IntParmTemplate("beforeInpoint", "Before Inpoint", 1, default_value=([0]), min=0, max=1, min_is_strict=True, max_is_strict=True, naming_scheme=hou.parmNamingScheme.Base1, menu_items=([]), menu_labels=([]), icon_names=([]), item_generator_script="", item_generator_script_language=hou.scriptLanguage.Python, menu_type=hou.menuType.Normal, menu_use_token=False)
            hou_parm_template.addParmTemplate(hou_parm_template2)
            # Code for parameter template
            hou_parm_template2 = hou.IntParmTemplate("onInpoint", "On Inpoint", 1, default_value=([0]), min=0, max=1, min_is_strict=True, max_is_strict=True, naming_scheme=hou.parmNamingScheme.Base1, menu_items=([]), menu_labels=([]), icon_names=([]), item_generator_script="", item_generator_script_language=hou.scriptLanguage.Python, menu_type=hou.menuType.Normal, menu_use_token=False)
            hou_parm_template.addParmTemplate(hou_parm_template2)
            # Code for parameter template
            hou_parm_template2 = hou.IntParmTemplate("onTrack", "On Track", 1, default_value=([0]), min=0, max=1, min_is_strict=True, max_is_strict=True, naming_scheme=hou.parmNamingScheme.Base1, menu_items=([]), menu_labels=([]), icon_names=([]), item_generator_script="", item_generator_script_language=hou.scriptLanguage.Python, menu_type=hou.menuType.Normal, menu_use_token=False)
            hou_parm_template.addParmTemplate(hou_parm_template2)
            # Code for parameter template
            hou_parm_template2 = hou.IntParmTemplate("onOutpoint", "On Outpoint", 1, default_value=([0]), min=0, max=1, min_is_strict=True, max_is_strict=True, naming_scheme=hou.parmNamingScheme.Base1, menu_items=([]), menu_labels=([]), icon_names=([]), item_generator_script="", item_generator_script_language=hou.scriptLanguage.Python, menu_type=hou.menuType.Normal, menu_use_token=False)
            hou_parm_template.addParmTemplate(hou_parm_template2)
            # Code for parameter template
            hou_parm_template2 = hou.IntParmTemplate("afterOutpoint", "After Outpoint", 1, default_value=([0]), min=0, max=1, min_is_strict=True, max_is_strict=True, naming_scheme=hou.parmNamingScheme.Base1, menu_items=([]), menu_labels=([]), icon_names=([]), item_generator_script="", item_generator_script_language=hou.scriptLanguage.Python, menu_type=hou.menuType.Normal, menu_use_token=False)
            hou_parm_template.addParmTemplate(hou_parm_template2)
            # Code for parameter template
            hou_parm_template2 = hou.FloatParmTemplate("localtime", "Local Time", 1, default_value=([0]), min=0, max=100, min_is_strict=False, max_is_strict=False, look=hou.parmLook.Regular, naming_scheme=hou.parmNamingScheme.Base1)
            hou_parm_template.addParmTemplate(hou_parm_template2)
            # Code for parameter template
            hou_parm_template2 = hou.FloatParmTemplate("completed", "Completed", 1, default_value=([0]), min=0, max=1, min_is_strict=True, max_is_strict=True, look=hou.parmLook.Regular, naming_scheme=hou.parmNamingScheme.Base1)
            hou_parm_template.addParmTemplate(hou_parm_template2)
            # Code for parameter template
            hou_parm_template2 = hou.RampParmTemplate("cramp", "Completed Ramp", hou.rampParmType.Float, default_value=2, default_basis=None, color_type=None)
            hou_parm_template2.setTags({"rampshowcontrolsdefault": "0"})
            hou_parm_template.addParmTemplate(hou_parm_template2)
            hou_parm_template_group.append(hou_parm_template)
            # Code for parameter template
            hou_parm_template = hou.FolderParmTemplate("folder2_3", "User Data", folder_type=hou.folderType.Tabs, default_value=0, ends_tab_group=False)
            # Code for parameter template
            hou_parm_template2 = hou.FolderParmTemplate("auxfloat", "Aux Floats", folder_type=hou.folderType.MultiparmBlock, default_value=0, ends_tab_group=False)
            # Code for parameter template
            hou_parm_template3 = hou.FloatParmTemplate("auxfloat#", "Aux Float #", 1, default_value=([0]), min=-100, max=100, min_is_strict=False, max_is_strict=False, look=hou.parmLook.Regular, naming_scheme=hou.parmNamingScheme.Base1)
            hou_parm_template3.setJoinWithNext(True)
            hou_parm_template2.addParmTemplate(hou_parm_template3)
            # Code for parameter template
            hou_parm_template3 = hou.StringParmTemplate("notefloat#", "Note", 1, default_value=([""]), naming_scheme=hou.parmNamingScheme.Base1, string_type=hou.stringParmType.Regular, menu_items=([]), menu_labels=([]), icon_names=([]), item_generator_script="", item_generator_script_language=hou.scriptLanguage.Python, menu_type=hou.menuType.Normal)
            hou_parm_template2.addParmTemplate(hou_parm_template3)
            hou_parm_template.addParmTemplate(hou_parm_template2)
            # Code for parameter template
            hou_parm_template2 = hou.FolderParmTemplate("auxop", "Aux Ops", folder_type=hou.folderType.MultiparmBlock, default_value=0, ends_tab_group=False)
            # Code for parameter template
            hou_parm_template3 = hou.StringParmTemplate("auxop#", "Aux Op #", 1, default_value=([""]), naming_scheme=hou.parmNamingScheme.Base1, string_type=hou.stringParmType.NodeReference, menu_items=([]), menu_labels=([]), icon_names=([]), item_generator_script="", item_generator_script_language=hou.scriptLanguage.Python, menu_type=hou.menuType.Normal)
            hou_parm_template3.setJoinWithNext(True)
            hou_parm_template3.setTags({"oprelative": "/obj"})
            hou_parm_template2.addParmTemplate(hou_parm_template3)
            # Code for parameter template
            hou_parm_template3 = hou.StringParmTemplate("noteobj#", "note", 1, default_value=([""]), naming_scheme=hou.parmNamingScheme.Base1, string_type=hou.stringParmType.Regular, menu_items=([]), menu_labels=([]), icon_names=([]), item_generator_script="", item_generator_script_language=hou.scriptLanguage.Python, menu_type=hou.menuType.Normal)
            hou_parm_template2.addParmTemplate(hou_parm_template3)
            hou_parm_template.addParmTemplate(hou_parm_template2)
            # Code for parameter template
            hou_parm_template2 = hou.FolderParmTemplate("auxfiles", "Aux Files", folder_type=hou.folderType.MultiparmBlock, default_value=0, ends_tab_group=False)
            # Code for parameter template
            hou_parm_template3 = hou.StringParmTemplate("auxfile#", "Aux File #", 1, default_value=([""]), naming_scheme=hou.parmNamingScheme.Base1, string_type=hou.stringParmType.FileReference, menu_items=([]), menu_labels=([]), icon_names=([]), item_generator_script="", item_generator_script_language=hou.scriptLanguage.Python, menu_type=hou.menuType.StringReplace)
            hou_parm_template3.setJoinWithNext(True)
            hou_parm_template3.setTags({"filechooser_mode": "read", "oprelative": "/obj", "script_callback": ""})
            hou_parm_template2.addParmTemplate(hou_parm_template3)
            # Code for parameter template
            hou_parm_template3 = hou.StringParmTemplate("notefile#_2", "note", 1, default_value=([""]), naming_scheme=hou.parmNamingScheme.Base1, string_type=hou.stringParmType.Regular, menu_items=([]), menu_labels=([]), icon_names=([]), item_generator_script="", item_generator_script_language=hou.scriptLanguage.Python, menu_type=hou.menuType.Normal)
            hou_parm_template2.addParmTemplate(hou_parm_template3)
            hou_parm_template.addParmTemplate(hou_parm_template2)
            hou_parm_template_group.append(hou_parm_template)
            hou_node.setParmTemplateGroup(hou_parm_template_group)
            # Code for /obj/Sequences/Track001/copyinput parm 
             
           
       
            
            hou_parm = hou_node.parm("copyinput")
            hou_parm.lock(False)
            hou_parm.set(1)
            hou_parm.setAutoscope(False)
            
            
            # Code for /obj/Sequences/Track001/cacheinput parm 
             
                 
            hou_parm = hou_node.parm("cacheinput")
            hou_parm.lock(False)
            hou_parm.set(0)
            hou_parm.setAutoscope(False)
            
            
            # Code for /obj/Sequences/Track001/psversion parm 
             
                 
            hou_parm = hou_node.parm("psversion")
            hou_parm.lock(False)
            hou_parm.set("ps_2.1.0.0")
            hou_parm.setAutoscope(False)
            
            
            # Code for /obj/Sequences/Track001/folder21 parm 
             
                 
            hou_parm = hou_node.parm("folder21")
            hou_parm.lock(False)
            hou_parm.set(0)
            hou_parm.setAutoscope(False)
            
            
            # Code for /obj/Sequences/Track001/range parm tuple
             
                 
            hou_parm_tuple = hou_node.parmTuple("range")
            hou_parm_tuple.lock((False, False))
            hou_parm_tuple.set((0, 100))
            hou_parm_tuple.setAutoscope((False, False))
            
            
            # Code for /obj/Sequences/Track001/camera parm 
             
                 
            hou_parm = hou_node.parm("camera")
            hou_parm.lock(False)
            hou_parm.set("")
            hou_parm.setAutoscope(False)
            
            
            # Code for /obj/Sequences/Track001/rop parm 
             
                 
            hou_parm = hou_node.parm("rop")
            hou_parm.lock(False)
            hou_parm.set("")
            hou_parm.setAutoscope(False)
            
            
            # Code for /obj/Sequences/Track001/deadline parm 
             
                 
            hou_parm = hou_node.parm("deadline")
            hou_parm.lock(False)
            hou_parm.set("")
            hou_parm.setAutoscope(False)
            
            
            # Code for /obj/Sequences/Track001/version parm 
             
                 
            hou_parm = hou_node.parm("version")
            hou_parm.lock(False)
            hou_parm.set("v01")
            hou_parm.setAutoscope(False)
            
            
            # Code for /obj/Sequences/Track001/meta parm 
             
                 
            hou_parm = hou_node.parm("meta")
            hou_parm.lock(False)
            hou_parm.set("")
            hou_parm.setAutoscope(False)
            
            
                 
            # parm: renderoutput parm 
            hou_parm = hou_node.parm("renderoutput")
            hou_parm.lock(False)
            hou_parm.set( hou.getenv("PS_RENDER_OUTPUT" , "$HIP/render/{camera}{_meta}{_version}/{camera}{_meta}{_version}_$F6.exr" ).replace('<$>','$') )
            hou_parm.setAutoscope(False)
           
            # parm: renderoutput parm 
            hou_parm = hou_node.parm("previewoutput")
            hou_parm.lock(False)
            hou_parm.set( hou.getenv("PS_PREVIEW_OUTPUT" , "$HIP/previews/{camera}{_meta}{_version}/{camera}{_meta}{_version}_$F6.jpg" ).replace('<$>','$') )
            hou_parm.setAutoscope(False)        
            
            # Code for /obj/Sequences/Track001/sequencerTime parm 
             
                 
            hou_parm = hou_node.parm("sequencerTime")
          
            hou_parm.setAutoscope(True)
            hou_parm.setExpression("if len(hou.pwd().outputs())==0:\n    return hou.frame()\n\nfor item in (item for item in hou.pwd().outputs()[0].parms() if item.name()==\"timeOverride\"):\n    return item.eval()\nreturn 0", hou.exprLanguage.Python)
            hou_parm.lock(True)
            
            # Code for /obj/Sequences/Track001/audio parm 
             
                 
            hou_parm = hou_node.parm("audio")
            hou_parm.lock(False)
            hou_parm.set("")
            hou_parm.setAutoscope(False)
            
            
            # Code for /obj/Sequences/Track001/syncaudio parm 
             
                 
            hou_parm = hou_node.parm("syncaudio")
            hou_parm.lock(False)
            hou_parm.set(1)
            hou_parm.setAutoscope(False)
            
            
            # Code for /obj/Sequences/Track001/take parm 
             
                 
            hou_parm = hou_node.parm("take")
            hou_parm.lock(False)
            hou_parm.set("")
            hou_parm.setAutoscope(False)
            
            
            # Code for /obj/Sequences/Track001/animlayer parm 
             
                 
            hou_parm = hou_node.parm("animlayer")
            hou_parm.lock(False)
            hou_parm.set("")
            hou_parm.setAutoscope(False)
            
            
            # Code for /obj/Sequences/Track001/duration parm 
             
                 
            hou_parm = hou_node.parm("duration")
            hou_parm.set(100)
            hou_parm.setAutoscope(False)
            hou_parm.setExpression("abs(ch(\"range1\") - ch(\"range2\"))", hou.exprLanguage.Hscript)
            hou_parm.lock(True)
            
            # Code for /obj/Sequences/Track001/active parm 
             
                 
            hou_parm = hou_node.parm("active")
            hou_parm.set(0)
            hou_parm.setAutoscope(False)
            hou_parm.setExpression("if len(hou.pwd().outputs())==0:\n    return 0;\n\nfor item in (item for item in hou.pwd().outputs()[0].parms() if item.name()==\"timeOverride\"):\n    return hou.pwd().outputs()[0].inputs()[hou.pwd().outputs()[0].evalParm(\"input\")] == hou.pwd()", hou.exprLanguage.Python)
            hou_parm.lock(True)
            
            # Code for /obj/Sequences/Track001/beforeInpoint parm 
            hou_parm = hou_node.parm("beforeInpoint")
            hou_parm.set(0)
            hou_parm.setAutoscope(False)
            hou_parm.setExpression("ch(\"sequencerTime\") < ch(\"range1\")", hou.exprLanguage.Hscript)
     
            hou_parm.lock(True)
            
            # Code for /obj/Sequences/Track001/onInpoint parm 
             
                 
            hou_parm = hou_node.parm("onInpoint")
            hou_parm.set(0)
            hou_parm.setAutoscope(False)
            hou_parm.setExpression("ch(\"sequencerTime\") == ch(\"range1\")", hou.exprLanguage.Hscript)
             
            hou_parm.lock(True)
            
            # Code for /obj/Sequences/Track001/onTrack parm 
             
                 
            hou_parm = hou_node.parm("onTrack")
            hou_parm.set(0)
            hou_parm.setAutoscope(False)
            hou_parm.setExpression("ch(\"sequencerTime\") >= ch(\"range1\") && ch(\"sequencerTime\") <= ch(\"range2\")", hou.exprLanguage.Hscript)
     
            
            hou_parm.lock(True)
            
            # Code for /obj/Sequences/Track001/onOutpoint parm 
             
                 
            hou_parm = hou_node.parm("onOutpoint")
            hou_parm.set(0)
            hou_parm.setAutoscope(False)
            hou_parm.setExpression("ch(\"sequencerTime\") == ch(\"range2\")", hou.exprLanguage.Hscript)
           
            hou_parm.lock(True)
            
            # Code for /obj/Sequences/Track001/afterOutpoint parm 
             
                 
            hou_parm = hou_node.parm("afterOutpoint")
            hou_parm.set(1)
            hou_parm.setAutoscope(False)
            hou_parm.lock(True)
            
            # Code for /obj/Sequences/Track001/localtime parm 
             
                 
            hou_parm = hou_node.parm("localtime")
            hou_parm.set(104)
            hou_parm.setAutoscope(False)
            hou_parm.setExpression("$FF-ch('range1')", hou.exprLanguage.Hscript)
            hou_parm.lock(True)
            
            # Code for /obj/Sequences/Track001/completed parm 
             
                 
            hou_parm = hou_node.parm("completed")
            hou_parm.set(1)
            hou_parm.setAutoscope(False)
            hou_parm.setExpression("hou.pwd().parmTuple(\"cramp\").evalAsRamps()[0].lookup(min(1,(max(0,hou.pwd().evalParm(\"sequencerTime\") - hou.pwd().evalParm(\"range1\"))) / hou.pwd().evalParm(\"duration\")))", hou.exprLanguage.Python)
            hou_parm.lock(True)
            
            # Code for /obj/Sequences/Track001/cramp parm 
                    
            
            hou_node.setExpressionLanguage(hou.exprLanguage.Hscript)
            
            hou_node.setUserData("nodeshape", "rect")
            if hasattr(hou_node, "syncNodeVersionIfNeeded"):
                hou_node.syncNodeVersionIfNeeded("17.0.463")
            
            return hou_node
        
        def createSequenceNode2(self, seqName, convert=False):
            # Code for /obj/ProSequencerData/switch1
            hou_node = None
            
            # Code for /obj/null1/switch2
            hou_node = convert
            
            hou_parm_template_group = hou.ParmTemplateGroup()
            # Code for parameter template
            hou_parm_template = hou.IntParmTemplate("input", "Select Input", 1, default_value=([0]), min=0, max=10, min_is_strict=True, max_is_strict=False, naming_scheme=hou.parmNamingScheme.Base1, menu_items=([]), menu_labels=([]), icon_names=([]), item_generator_script="", item_generator_script_language=hou.scriptLanguage.Python, menu_type=hou.menuType.Normal)
            hou_parm_template_group.append(hou_parm_template)
            
            # Code for parameter template
            hou_parm_template = hou.IntParmTemplate("inputoverride", "Manual Input", 1, default_value=([0]), min=0, max=10, min_is_strict=True, max_is_strict=False, naming_scheme=hou.parmNamingScheme.Base1, menu_items=([]), menu_labels=([]), icon_names=([]), item_generator_script="", item_generator_script_language=hou.scriptLanguage.Python, menu_type=hou.menuType.Normal)
            hou_parm_template_group.append(hou_parm_template)
            
            
            # Code for parameter template
            hou_parm_template = hou.FloatParmTemplate("timeOverride", "Sequencer Time", 1, default_value=([0]), default_expression=(["$F"]), default_expression_language=([hou.scriptLanguage.Hscript]), min=0, max=10, min_is_strict=False, max_is_strict=False, look=hou.parmLook.Regular, naming_scheme=hou.parmNamingScheme.Base1)
            hou_parm_template_group.append(hou_parm_template)
            
            # Code for parameter template
            hou_parm_template = hou.StringParmTemplate("activetrack", "Active Track", 1, default_value=([""]), naming_scheme=hou.parmNamingScheme.Base1, string_type=hou.stringParmType.NodeReference, menu_items=([]), menu_labels=([]), icon_names=([]), item_generator_script="", item_generator_script_language=hou.scriptLanguage.Python, menu_type=hou.menuType.Normal)
            hou_parm_template.setTags({"oprelative": "."})
            hou_parm_template_group.append(hou_parm_template)
    
            # Code for parameter template
            hou_parm_template = hou.ToggleParmTemplate("camswitcher", "Use for viewport camera switching", default_value=False)
            hou_parm_template_group.append(hou_parm_template)
            
            hou_parm_template = hou.ToggleParmTemplate("noaudio", "Disable audio switching", default_value=False)
            hou_parm_template_group.append(hou_parm_template) 
            
            # Code for parameter template
            hou_parm_template = hou.ToggleParmTemplate("animswitcher", "Enable AnimLayer switching", default_value=False)
            hou_parm_template_group.append(hou_parm_template)
            
            # Code for parameter template
            hou_parm_template = hou.StringParmTemplate("callback", "Callback", 1, default_value=([""]), naming_scheme=hou.parmNamingScheme.Base1, string_type=hou.stringParmType.Regular, menu_items=([]), menu_labels=([]), icon_names=([]), item_generator_script="", item_generator_script_language=hou.scriptLanguage.Python, menu_type=hou.menuType.Normal)
            hou_parm_template_group.append(hou_parm_template)
            hou_node.setParmTemplateGroup(hou_parm_template_group)
    
            
            # Code for /obj/null1/switch2/input parm 
            
            hou_parm = hou_node.parm("input")
            hou_parm.lock(False)
            hou_parm.setAutoscope(False)
            hou_parm.setExpression("outvar=0 \n\nif hou.pwd().isBypassed():\n    outvar = 0\n\nelif hou.pwd().isTemplateFlagSet():\n    outvar = min(max( 0 , hou.evalParm(\"inputoverride\")), len(hou.pwd().inputs())-1  )  \n\nelse:\n    for i, item in enumerate(  reversed(hou.pwd().inputs())):\n        if item.evalParm(\"onTrack\") and not item.isBypassed():\n            outvar=len(hou.pwd().inputs()) - i - 1\ntry:\n    anim=hou.node(hou.pwd().inputs()[outvar].evalParm(\"animlayer\"))\n    if anim and hou.pwd().evalParm(\"animswitcher\") :\n        for i, item in enumerate(anim.outputs()[0].inputs()):\n            if item==anim:\n                if anim.outputs()[0].evalParm(\"active\")!=i:\n                    anim.outputs()[0].parm(\"active\").set(i)\nexcept:\n    pass\n\nreturn outvar", hou.exprLanguage.Python)
           # Code for /obj/null1/switch2/timeOverride parm 
            hou_parm = hou_node.parm("timeOverride")
            hou_parm.lock(False)
            hou_parm.setAutoscope(False)
            hou_parm.setExpression("$F", hou.exprLanguage.Hscript)
            
            
            # Code for /obj/null1/switch2/camswitcher parm 
            hou_parm = hou_node.parm("camswitcher")
            hou_parm.lock(False)
            hou_parm.setAutoscope(False)    
            hou_node.setExpressionLanguage(hou.exprLanguage.Hscript)
            
            
            # Code for keyframe.
            hou_parm = hou_node.parm("activetrack")
            hou_parm.setExpression("import hou\nif hou.pwd().inputs():\n    return  hou.pwd().inputs()[hou.pwd().evalParm(\"input\")].path()\nelse:\n    return \"\"", hou.exprLanguage.Python)
            hou_parm.lock(True)

        
        return hou_node    
              
        
    def createSequenceNode(self, seqName, convert=False):

        hou_node=convert;
        
    
      
        
        hou_parm_template_group = hou.ParmTemplateGroup()
        # Code for parameter template
        hou_parm_template = hou.IntParmTemplate("input", "Select Input", 1, default_value=([0]), min=0, max=10, min_is_strict=True, max_is_strict=False, naming_scheme=hou.parmNamingScheme.Base1, menu_items=([]), menu_labels=([]), icon_names=([]), item_generator_script="", item_generator_script_language=hou.scriptLanguage.Python, 
        menu_type=hou.menuType.Normal, menu_use_token=False)
        hou_parm_template_group.append(hou_parm_template)
        # Code for parameter template
        hou_parm_template = hou.IntParmTemplate("inputoverride", "Manual Input", 1, default_value=([0]), min=0, max=10, min_is_strict=True, max_is_strict=False, naming_scheme=hou.parmNamingScheme.Base1, menu_items=([]), menu_labels=([]), icon_names=([]), item_generator_script="", item_generator_script_language=hou.scriptLanguage.
        Python, menu_type=hou.menuType.Normal, menu_use_token=False)
        hou_parm_template.setHelp("When the switch's template flag, the pink one, is enabled the sequencer is in manual mode. Shift-MMB on a track to switch to that track.")
        hou_parm_template_group.append(hou_parm_template)
        # Code for parameter template
        hou_parm_template = hou.FloatParmTemplate("timeOverride", "Sequencer Time", 1, default_value=([0]), default_expression=(["$F"]), default_expression_language=([hou.scriptLanguage.Hscript]), min=0, max=10, min_is_strict=False, max_is_strict=False, look=hou.parmLook.Regular, naming_scheme=hou.parmNamingScheme.Base1)
        hou_parm_template.setHelp("This is the internal time of the sequencer, normally it is set to $F. It can be any thing so you can decouple the sequencer time from the main timeline. ")
        hou_parm_template_group.append(hou_parm_template)
        # Code for parameter template
        hou_parm_template = hou.StringParmTemplate("activetrack", "Active Track", 1, default_value=([""]), naming_scheme=hou.parmNamingScheme.Base1, string_type=hou.stringParmType.NodeReference, menu_items=([]), menu_labels=([]), icon_names=([]), item_generator_script="", item_generator_script_language=hou.scriptLanguage.Python, 
        menu_type=hou.menuType.Normal)
        hou_parm_template.setHelp("You can reference this parm to get to easily get active track's path.")
        hou_parm_template.setTags({"oprelative": "."})
        hou_parm_template_group.append(hou_parm_template)
        # Code for parameter template
        hou_parm_template = hou.ToggleParmTemplate("camswitcher", "Use for viewport camera switching", default_value=False)
        hou_parm_template.setHelp("When enabled, and the viewport is looking through any camera used in any of seqeunce's tracks, it will switch the viewport the the active track's camera.")
        hou_parm_template_group.append(hou_parm_template)
        # Code for parameter template
        hou_parm_template = hou.ToggleParmTemplate("noaudio", "Disable audio switching", default_value=False)
        hou_parm_template.setHelp("If you have audio files assigned to the tracks you can use this to disable automatic switching.")
        hou_parm_template_group.append(hou_parm_template)
        # Code for parameter template
        hou_parm_template = hou.ToggleParmTemplate("animswitcher", "Enable AnimLayer switching", default_value=False)
        hou_parm_template.setHelp("When enabled, and channels are assigned to the track's 'anim layer' parm, it will set the layer to be the current layer and set it's weight to 1 and zeros out the weight of the other channels in the channel mixer.")
        hou_parm_template_group.append(hou_parm_template)
        # Code for parameter template
        hou_parm_template = hou.ToggleParmTemplate("tflag", "Label", default_value=False, default_expression='pwd().isTemplateFlagSet()', default_expression_language=hou.scriptLanguage.Python)
        hou_parm_template.hide(True)
        hou_parm_template_group.append(hou_parm_template)
        # Code for parameter template
        hou_parm_template = hou.StringParmTemplate("callback", "Callback", 1, default_value=([""]), naming_scheme=hou.parmNamingScheme.Base1, string_type=hou.stringParmType.Regular, menu_items=([]), menu_labels=([]), icon_names=([]), item_generator_script="", item_generator_script_language=hou.scriptLanguage.Python, menu_type=hou
        .menuType.Normal)
        hou_parm_template.setConditional(hou.parmCondType.DisableWhen, "{ tflag != 1 }")
        hou_parm_template.setHelp("Pyhton, called only in ManualMode when switching between tracks using the sequencer panel")
        hou_parm_template_group.append(hou_parm_template)
        hou_node.setParmTemplateGroup(hou_parm_template_group)
        # Code for /obj/Sequences/sequence001/input parm 
         
             
        hou_parm = hou_node.parm("input")
        hou_parm.lock(False)
        hou_parm.set(1)
        hou_parm.setAutoscope(False)
        hou_parm.setExpression("outvar=0 \n\nif hou.pwd().isBypassed():\n    outvar = 0\n\nelif hou.pwd().isTemplateFlagSet():\n    outvar = min(max( 0 , hou.evalParm(\"inputoverride\")), len(hou.pwd().inputs())-1  )  \n\nelse:\n    for i, item in enumerate(  reversed(hou.pwd().inputs())):\n        if item.evalParm(\"onTrack\") and not item.isBypassed():\n            outvar=len(hou.pwd().inputs()) - i - 1\n\ntry:\n    anim=hou.node(hou.pwd().inputs()[outvar].evalParm(\"animlayer\"))\n    if anim and hou.pwd().evalParm(\"animswitcher\") :\n        for i, item in enumerate(anim.outputs()[0].inputs()):\n            if item==anim:\n                if anim.outputs()[0].evalParm(\"active\")!=i:\n                    anim.outputs()[0].parm(\"active\").set(i)\n                    c=channel_editor = hou.ui.paneTabOfType(hou.paneTabType.ChannelEditor)\n                    if c!=None:\n                        tmp=c.graph().selectedKeyframes()\n                anim.outputs()[0].parm(\"weight\"+str(i)).set(1)\n            elif i>0:\n                anim.outputs()[0].parm(\"weight\"+str(i)).set(0)\n       \nexcept:\n    print(\"some error with anim layers occured\")\n\n\nreturn outvar", hou.exprLanguage.Python)
        
        
        # Code for /obj/Sequences/sequence001/inputoverride parm 
         
             
        hou_parm = hou_node.parm("inputoverride")
        hou_parm.lock(False)
        hou_parm.set(4)
        hou_parm.setAutoscope(False)
        
        
        # Code for /obj/Sequences/sequence001/timeOverride parm 
         
             
        hou_parm = hou_node.parm("timeOverride")
        hou_parm.lock(False)
        hou_parm.set(102)
        hou_parm.setAutoscope(False)
        hou_parm.setExpression("$F", hou.exprLanguage.Hscript)
        
        # Code for /obj/Sequences/sequence001/activetrack parm 
         
             
        hou_parm = hou_node.parm("activetrack")
        hou_parm.set("/obj/Sequences/Track002")
        hou_parm.setAutoscope(True)
        hou_parm.setExpression("import hou\nif hou.pwd().inputs():\n    return  hou.pwd().inputs()[hou.pwd().evalParm(\"input\")].path()\nelse:\n    return \"\"", hou.exprLanguage.Python)
        hou_parm.lock(True)
        
        # Code for /obj/Sequences/sequence001/camswitcher parm 
         
             
        hou_parm = hou_node.parm("camswitcher")
        hou_parm.lock(False)
        hou_parm.set(0)
        hou_parm.setAutoscope(False)
        
        
        # Code for /obj/Sequences/sequence001/noaudio parm 
         
             
        hou_parm = hou_node.parm("noaudio")
        hou_parm.lock(False)
        hou_parm.set(0)
        hou_parm.setAutoscope(False)
        
        
        # Code for /obj/Sequences/sequence001/animswitcher parm 
         
             
        hou_parm = hou_node.parm("animswitcher")
        hou_parm.lock(False)
        hou_parm.set(0)
        hou_parm.setAutoscope(False)
        
        
        # Code for /obj/Sequences/sequence001/tflag parm 
         
             
        hou_parm = hou_node.parm("tflag")
        hou_parm.lock(False)
        hou_parm.set(1)
        hou_parm.setAutoscope(False)
        hou_parm.setExpression("pwd().isTemplateFlagSet()", hou.exprLanguage.Python)
        
        # Code for /obj/Sequences/sequence001/callback parm 
         
             
        hou_parm = hou_node.parm("callback")
        hou_parm.lock(False)
        hou_parm.set("")
        hou_parm.setAutoscope(False)
        
        return hou_node    
         

    
