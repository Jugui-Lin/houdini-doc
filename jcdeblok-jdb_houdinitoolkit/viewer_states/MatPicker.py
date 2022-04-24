import toolutils
import hou

#hou.ui.unregisterViewerState("MatPicker")

class MatPicker(object):
    def __init__(self, scene_viewer, state_name):
        self.state_name = state_name
        self.scene_viewer = scene_viewer
        self._base_x = self._base_frame = None
        self.done=False
        i=0
        main=None
        
        self.ne=None

        #find dominant network editor        
        cursize=0
        while hou.ui.paneTabOfType(hou.paneTabType.NetworkEditor,i):
            pane =  hou.ui.paneTabOfType(hou.paneTabType.NetworkEditor,i)
            if pane.isCurrentTab():
                if pane.size()[0]*pane.size()[1]>cursize:
                    cursize=pane.size()[0]*pane.size()[1]
                    main=pane
            i=i+1
        self.ne=main
                
    def onGenerate(self, kwargs):
        self.scene_viewer.setPromptMessage(
            "Click on any prim to edit it's material"
        )

    def onExit(self, kwargs):
        self.scene_viewer.clearPromptMessage()

    def gotoMat(self, x,y):
        node= self.scene_viewer.curViewport().queryNodeAtPixel(x ,y)

        prim=self.scene_viewer.curViewport().queryPrimAtPixel( node,x,y )
        mat=None
        try:
            mat=prim.attribValue("shop_materialpath")
        except:
            pass

        if mat:
            print("Picked Material: "+mat)
            mat=hou.node(mat)
            self.ne.setCurrentNode(mat)
            mat.setSelected(True, clear_all_selected=True)
            p=mat.position()
            self.ne.setVisibleBounds(hou.BoundingRect(hou.Vector2(p[0]-5,p[1]-5), hou.Vector2(p[0]+5,p[1]+5) ), 0.1, 0,  True)
        
 
    def onMouseEvent(self, kwargs):
        device = kwargs["ui_event"].device()
        reason = kwargs["ui_event"].reason()
        if not self.done and reason==hou.uiEventReason.Start:
            self.done=True 
            x = int( device.mouseX())
            y = int(device.mouseY())
            self.gotoMat(x,y)

def createViewerStateTemplate():
    state_typename = "MatPicker"
    state_label = "MatPicker"
    state_cat = hou.objNodeTypeCategory()

    template = hou.ViewerStateTemplate(state_typename, state_label, state_cat)
    template.bindFactory(MatPicker)
    template.bindIcon("SOP_texture")

    return template
    
def dev():
    hou.ui.unregisterViewerState("MatPicker")    
    hou.ui.registerViewerState(createViewerStateTemplate())
    scene_viewer = hou.ui.paneTabOfType(hou.paneTabType.SceneViewer)
    scene_viewer.setCurrentState("MatPicker")    

#dev()    