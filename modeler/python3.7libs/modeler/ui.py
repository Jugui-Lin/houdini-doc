MODELER_VERSION = "2022"

import os
import sys
from functools import partial
import numpy
import time
import pickle

import hou
from hdefereval import executeDeferred
import objecttoolutils
import nodegraphview

import shiboken2
import PySide2.QtCore as qtc
import PySide2.QtGui as qtg
import PySide2.QtWidgets as qtw
from PySide2.QtCore import QFile
from PySide2.QtTest import QTest as qtest
from PySide2.QtUiTools import QUiLoader

qt = qtc.Qt

modeler_path = os.getenv("MODELER_PATH")
qt_app = qtw.QApplication.instance()
x_res = qtw.QDesktopWidget().screenGeometry().width()
y_res = qtw.QDesktopWidget().screenGeometry().height()

PROMPT_ONE_GEO = "Geometry object must be selected"
PROMPT_GEO_OBJECTS = "Geometry object(s) must be selected"
PROMPT_EDGES_OR_POLYGONS = "Edge(s) or polygon(s) must be selected"
PROMPT_POINTS_EDGES_POLYGONS = "Point(s), edge(s) or polygon(s) must be selected"
PROMPT_POINTS = "Point(s) must be selected"
PROMPT_EDGES = "Edge(s) must be selected"
PROMPT_POLYGONS = "Polygon(s) must be selected"
PROMPT_OBJECTS_OR_COMPONENTS = "Objects or geometry components must be selected"
PROMPT_UNSUPPORTED_CONTEXT = "Unsupported context"
PROMPT_ONE_OR_MORE_OBJECTS = "At least one geometry object must be active"

default_setup_list = [ 'principledshader::2.0', True ]

VIEWER = None
VIEWER_WIDGET = None
COPIED_GEO = None


def get_scene_viewer_mouse_widget():
    global main_widget
    mouse_widget = None
    main_widget = hou.qt.mainWindow()
    for widget in main_widget.findChildren(qtw.QWidget, "RE_Window"):
        if widget.windowTitle() == "DM_ViewLayout":
            for l in widget.findChildren(qtw.QVBoxLayout):
                if l.count()==1:
                    w = l.itemAt(0).widget()
                    if w.objectName() == "RE_GLDrawable":
                        i = int(shiboken2.getCppPointer(w)[0])
                        mouse_widget = shiboken2.wrapInstance(i, qtw.QWidget)
                        return mouse_widget
    return mouse_widget

def prompt(text, duration=5.0):
    VIEWER.setPromptMessage(text, hou.promptMessageType.Error)

def shift_cursor():
    qtg.QCursor.setPos(qtg.QCursor.pos() + qtc.QPoint(0, 1))    

def label(string):
    for i in range(len(string) - 1)[::-1]:
        if string[i].isupper() and string[i + 1].islower():
            string = string[:i] + " " + string[i:]
        if string[i].isupper() and string[i - 1].islower():
            string = string[:i] + " " + string[i:]
    return " ".join(string.split())

def key_is_modifier(key):
    return ( key in (qt.Key_Alt, qt.Key_Control, qt.Key_Shift, qt.Key_Meta) )

def show_handles(scene_viewer, value):
    for viewport in scene_viewer.viewports():
        viewport.settings().enableGuide(hou.viewportGuide.NodeHandles, value)

def show_current_geo(scene_viewer, value):
    for viewport in scene_viewer.viewports():
        viewport.settings().enableGuide(hou.viewportGuide.CurrentGeometry, value)

def inc_string(string):
    digits = "".join(c for c in string if c.isdigit())
    if digits:
        return string.split(digits)[0] + str(int(digits) + 1)
    else:
        return string + "1"

def home_selected():
    try:
        hou.ui.paneTabOfType(hou.paneTabType.NetworkEditor).homeToSelection()
    except AttributeError:
        pass

def frame_items(items):
    try:
        nodegraphview.frameItems(hou.ui.paneTabOfType(hou.paneTabType.NetworkEditor), items)
    except AttributeError:
        pass

def get_hvd(scene_viewer, absolute=False):
    hvd = scene_viewer.curViewport().viewTransform().extractRotationMatrix3().asTupleOfTuples()

    x = numpy.abs(hvd[0])
    x_max_id = x.argmax()
    x.fill(0.0)

    y = numpy.abs(hvd[1])
    y_max_id = y.argmax()
    y.fill(0.0)

    if absolute:
        x[x_max_id] = 1.0
        y[y_max_id] = 1.0
        return hou.Vector3(x), hou.Vector3(y), hou.Vector3(numpy.abs(numpy.cross(x, y)))
    else:
        x[x_max_id] = numpy.sign(hvd[0][x_max_id])
        y[y_max_id] = numpy.sign(hvd[1][y_max_id])
        return hou.Vector3(x), hou.Vector3(y), hou.Vector3(numpy.cross(x, y))

def transform_handle(node, origin, rotation, op="translate"):
    node_type = node.type().name()
    if node_type == "edit":
        handle_name = "Edit Manipulator"
    elif node_type == "xform":
        handle_name = "Transformer"
    elif node_type == "copyxform":
        handle_name = "Copy Transformer"
    elif node_type == "polyextrude::2.0":
        handle_name = "Polygon Extruder 2"
    else:
        return
    hou.hscript('omparm "{0}" {1} {2} "{3}(1) follow_selection(0) pivot({4} {5} {6}) orientation({7} {8} {9})"'.format(handle_name, node.name(), node.path(), op, origin[0], origin[1], origin[2], rotation[0], rotation[1], rotation[2]))


DEFAULT_HOTKEYS = {
    
"1":            "select_objects",
"2":            "select_points",
"3":            "select_edges",
"4":            "select_polygons",
"Left":         "walk_selection_left",
"Right":        "walk_selection_right",
"Up":           "walk_selection_up",
"Down":         "walk_selection_down",
"`":            "convert_to_loops",
"Shift+~":      "convert_to_edge_rings",
"Shift+@":      "convert_to_boundary",
"Shift+#":      "expand_selection_by_normal",
"Ctrl+Shift+@": "select_hard_edges",
".":            "grow",
",":            "shrink",
"Shift+!":      "convert_to_shells",
"Shift+F1":     "lasso_frontface",
"Shift+F2":     "lasso_backface",
"Shift+F3":     "box_frontface",
"Shift+F4":     "box_backface",
"Ctrl+F1":       "hide_others",
"Ctrl+F2":       "ghost_others",
"Ctrl+F3":       "show_all",
'5':            "node_state",
"T":            "move",
"R":            "rotate",
"E":            "scale",
"Y":            "peak",
"S":            "slide",
"D":            "relax",
"Q":            "polypen",
"Shift+Q":      "magnet",
"K":            "knife",
"L":            "loop",
"F":            "extrude",
"G":            "extend",
"Shift+T":      "thickness",
"Alt+F":        "shift",
"H":            "bridge",
"J":            "bridge_connected",
"Ctrl+D":       "duplicate",
"Shift+D":      "array",
"Shift+F":      "fill",
"B":            "bevel",
"X":            "delete",
"Shift+X":      "collapse",
"C":            "connect",
"Ctrl+C":       "copy_polygons",
"Ctrl+X":       "cut_polygons",
"Ctrl+V":       "paste_polygons",
"Ctrl+Shift+D": "subdivide",
"O":            "fix_overlaps",
"P":            "clean_edges",
"F1":           "preview_subd",
"F2":           "preview_subd_wired",
"F3":           "preview_subd_isolines",
"F4":           "viewport_subd",
"Alt+X":        "delete_node",
"Z":            "parm_slider",
"Ctrl+Space":   "align_view"

}


class HotkeyManager(qtc.QObject):
    def __init__(self):
        super(HotkeyManager, self).__init__()
        self.user_hotkeys_file_path = hou.expandString("$HOUDINI_USER_PREF_DIR") + "/config/modeler_2022_hotkeys"
        self.hotkeys = {}
    
    def eventFilter(self, obj, event):
        if event.type() == qtc.QEvent.MouseButtonPress:
            self.cancel_assignment()
            return True
        
        elif event.type() == qtc.QEvent.KeyPress:
            if event.isAutoRepeat():
                return True

            key = event.key()
            mods = event.modifiers()

            # UNSUPPORTED KEYS
            if key == qt.Key_Space and mods == qt.NoModifier:
                self.cancel_assignment()
            
            # ASSIGN VALID KEY
            elif key not in (qt.Key_Alt, qt.Key_Control, qt.Key_Shift, qt.Key_Meta):
                qt_app.removeEventFilter(self)
                
                hotkey_string = qtg.QKeySequence(int(mods) + key).toString()

                # SHORTCUT EXISTS
                if hotkey_string in self.hotkeys.keys():
                    resource_name = self.hotkeys[hotkey_string]

                    result = hou.ui.displayMessage(hotkey_string + ' assigned to  "' + resource_name + '". Overwrite it?', title="Already Assigned", buttons=("Yes", "No"), default_choice=1, close_choice=1)
    
                    if result == 0:
                        del self.hotkeys[hotkey_string]
                    else:
                        hou.qt.mainWindow().setEnabled(True)
                        prompt("Hotkey overwrite canceled!")
                        return True

                self.hotkeys[hotkey_string] = self.resource_name

                # FINISH
                qt_app.removeEventFilter(self)
                hou.qt.mainWindow().setEnabled(True)
                prompt( '"' + self.resource_name + '" assigned to ' + hotkey_string)

                self.save()

            return True

        elif event.type() in (qtc.QEvent.KeyRelease, qtc.QEvent.MouseButtonRelease, qtc.QEvent.MouseButtonDblClick, qtc.QEvent.Wheel):
            return True

        return False

    def assign(self, resource_name):
        if resource_name in ("modeler_mode", "reload", "create_at_sop_level", "sym_axis_x", "sym_axis_y", "sym_axis_z"):
            prompt("Hotkey can't be assigned to this resource!")
        else:
            self.load()
            self.resource_name = resource_name
            hou.qt.mainWindow().setEnabled(False)
            qt_app.installEventFilter(self)
            prompt('Set hotkey for "' + self.resource_name + '". Click to cancel assignment')

    def cancel_assignment(self):
        qt_app.removeEventFilter(self)
        hou.qt.mainWindow().setEnabled(True)
        prompt("Hotkey assignement canceled!")

    def reset(self):
        if not hou.ui.displayMessage("Reset All Modeler Hotkeys?", title="Reset Hotkeys", buttons=("Yes", "No"), default_choice=1, close_choice=1):
            if os.path.exists(self.user_hotkeys_file_path):
                os.remove(self.user_hotkeys_file_path)
            self.load()
            self.save()

    def load(self):
        if os.path.exists(self.user_hotkeys_file_path):
            with open(self.user_hotkeys_file_path, 'rb') as f:
                try:
                    self.hotkeys = pickle.loads(f.read())

                except:
                    os.remove(self.user_hotkeys_file_path)
                    self.hotkeys = DEFAULT_HOTKEYS.copy()
        else:
            self.hotkeys = DEFAULT_HOTKEYS.copy()

    def save(self):
        with open(self.user_hotkeys_file_path, 'wb') as f:
            f.write(pickle.dumps(self.hotkeys))

    def delete(self):
        self.load()

        hotkeys_list = list(self.hotkeys.keys())

        choices = []
        for key, value in self.hotkeys.items():
            choices.append( '[ %s ]  %s' % (key, value) )

        result = hou.ui.selectFromList(choices, title="Modeler Hotkeys List")
        if result:
            for i in result:
                del self.hotkeys[ hotkeys_list[i] ]
            self.save()

hotkey_manager = HotkeyManager()



INT = 0
FLOAT = 1
RATIO = 2
BOOL = 3

parm_slider_nodes_dict = {
    "modeler::qprimitive": ("res", INT, 1, 1, None),
    "modeler::thickness": ("offset", FLOAT, 1, None, None),
    "modeler::hose": ("divisions", INT, 1, 4, None),
    "polybridge": ("divisions", INT, 1, 1, None),
    "modeler::connect": ("divisions", INT, 1, 1, None),
    "modeler::mirror": ("offset", FLOAT, 1, None, None),
    "modeler::polygons": ("divs", INT, 1, None, None),
    "modeler::set_flow": ("avg_ratio", RATIO, 1, None, None),
    "modeler::lattice_cage": ("divs", INT, 1, 1, None),
    "modeler::clean_edges": ("dissolve_angle", 1, INT, 0, None),
    "modeler::quadrify": ("shift", INT, 1, 0, None),
    "modeler::bevel_pro": ("divisions", INT, 1, 1, None),
    "modeler::loop_cut": ("numloops", INT, 1, 1, None),
    "blast": ("negate", BOOL, None, None, None),
    "modeler::relax": ("pin_borders", BOOL, None, None, None),
    "dissolve::2.0": ("reminlinepts", BOOL, None, None, None),
    "polybevel::3.0": ("divisions", INT, 1, 1, None),
    "polysplit::2.0": ("numloops", INT, 1, 0, None),
    "polyfill": ("fillmode", INT, 1, 0, 5),
    "subdivide": ("iterations", INT, 1, 0, 5),
    "modeler::preview_subdivided": ("iterations", INT, 1, 0, 5),
    "copyxform": ("ncy", INT, 1, 2, None),
    "xform": ("scale", RATIO, 1, None, None),
    "polyextrude::2.0": ("inset", FLOAT, 1, None, None),
    "edit": ("rad", FLOAT, 1, None, None),
    "uvedit": ("rad", FLOAT, 1, None, None),
    "polyreduce::2.0": ("percentage", INT, 1, 0, 100),
    "fuse::2.0": ("tol3d", FLOAT, 1, None, None),
    "normal": ("cuspangle", INT, 59, 30, 148),
    "mountain::2.0": ("height", FLOAT, 1, None, None),
    "switch": ("input", INT, 1, 0, None),
}


class ParmSlider(qtc.QObject):
    def start(self):
        self.cur_node = VIEWER.currentNode()

        if self.cur_node.type().category() == hou.sopNodeTypeCategory():
            self.cur_node = self.cur_node.parent().displayNode()
            if not self.cur_node.isSelected():
                self.cur_node.setCurrent(True, True)

            succes = True

            if self.cur_node.type().name() == "subnet" and VIEWER.currentState() == "modeler::polypen":
                sop = self.cur_node.displayNode()
                if sop is not None:
                    if sop.type().name() == "ray":
                        self.cur_node = sop.inputs()[0]

                    elif sop.type().name() == "edit":
                        succes = False
                    
                    else:
                        self.cur_node = sop

            node_type_name = self.cur_node.type().name()
            if succes and node_type_name in parm_slider_nodes_dict:
                parm_name, self.parm_type, self.step, self.min_value, self.max_value = parm_slider_nodes_dict[node_type_name]
                
                # BOOL -> JUST TOGGLE
                if self.parm_type == BOOL:
                    self.cur_node.parm(parm_name).set(not self.cur_node.evalParm(parm_name))
                    return

                cpos = qtg.QCursor.pos()
                self.start_x = cpos.x()
                self.start_y = cpos.y()
                self.start_time = time.time()

                self.drag = False
                
                self.parm = self.cur_node.parm(parm_name)
                self.parm_start_value = self.parm.eval()

                # INT
                if self.parm_type == INT:
                    self.parm_scale = 100.0 / y_res
                
                # FLOAT
                elif self.parm_type == FLOAT:
                    self.parm_scale = 1.0 / y_res * sum(self.cur_node.geometry().boundingBox().sizevec()) / 3.0
                
                # RATIO
                else:
                    self.parm_scale = 10.0 / y_res

                hou.hscript("undoctrl off")
                qt_app.installEventFilter(self)

                return

        prompt("Wrong node!")
        self.parm = None

    def finish(self):
        # QUICK RELEASE
        if not self.drag:
            # EDGE LOOP MATCH PROFILE
            if VIEWER.currentState() == "edgeloop" and not self.cur_node.evalParm("splitloc"):
                if self.cur_node.evalParm("parallellooptoggle"):
                    flip = self.cur_node.evalParm("parallelfliptoggle")
                    if flip:
                        self.cur_node.parm("parallelfliptoggle").set(False)
                        self.cur_node.parm("parallellooptoggle").set(False)
                    else:
                        self.cur_node.parm("parallelfliptoggle").set(True)
                else:
                    self.cur_node.parm("parallellooptoggle").set(True)


                shift_cursor()

            hou.hscript("undoctrl on")
            qt_app.removeEventFilter(self)
            return False

        v = self.parm.eval()
        if isinstance(v, int):
            v1 = v + 1
        else: 
            v1 = v + 0.0000001

        with hou.RedrawBlock() as rb:
            with hou.undos.disabler():
                self.parm.set(v1)

            hou.hscript("undoctrl on")
            self.parm.set(v)

        qt_app.removeEventFilter(self)

        if self.cur_node.userData("__preview_subd__") is not None:
            preview_subd_ef.iterations = self.cur_node.evalParm("iterations")

    def eventFilter(self, obj, event):
        if event.type() == qtc.QEvent.MouseMove:
            if self.drag:
                if not self.cur_node.needsToCook():
                    cur_value = self.parm.eval()
                    
                    if self.horizontal_movement:
                        delta = self.start_x - event.globalX()
                    else:
                        delta = self.start_y - event.globalY()

                    # INT
                    if self.parm_type == INT:
                        new_value = -int( self.parm_scale * delta ) * self.step + self.parm_start_value
                        
                        if self.max_value is not None:
                            new_value = min(new_value, self.max_value)
                        
                        if self.min_value is not None:
                            new_value = max(new_value, self.min_value)
                        
                        if cur_value != new_value:
                            self.parm.set(new_value)

                    # FLOAT
                    elif self.parm_type == FLOAT:
                        new_value = -( self.parm_scale * delta ) + self.parm_start_value
                        
                        if self.max_value is not None:
                            new_value = min(new_value, self.max_value)
                        
                        if self.min_value is not None:
                            new_value = max(new_value, self.min_value)

                        if cur_value != new_value:
                            self.parm.set(new_value)

                    # RATIO
                    else:
                        new_value = -( self.parm_scale * delta ) + self.parm_start_value
                        if cur_value != new_value:
                            self.parm.set(new_value)
            else:
                delta_h = self.start_x - event.globalX()
                delta_v = self.start_y - event.globalY()

                if abs(delta_h) > hou.ui.scaledSize(4):
                    self.start_x = event.globalX()
                    self.horizontal_movement = True
                    self.drag = True

                elif abs(delta_v) > hou.ui.scaledSize(4):
                    self.start_y = event.globalY()
                    self.horizontal_movement = False
                    self.drag = True

            return True
    
        elif event.type() == qtc.QEvent.KeyRelease and not event.isAutoRepeat():
            self.finish()
            return True
        
        elif event.type() in (qtc.QEvent.KeyPress, qtc.QEvent.KeyRelease, qtc.QEvent.Wheel):
            return True
        
        elif event.type() == qtc.QEvent.MouseButtonRelease:
            self.finish()

        return False

parm_slider = ParmSlider()


class AlignView(qtc.QObject):
    pre_align_camera = None

    def eventFilter(self, obj, event):
        if event.type() == qtc.QEvent.MouseButtonPress and event.button() == qt.LeftButton and VIEWER.currentState().endswith("view"):
            self.finish()

        return False

    def start(self):
        self.align_viewport = VIEWER.curViewport()
        self.align_viewport_name = self.align_viewport.name()

        # WRONG VIEWPORT TYPE
        if self.align_viewport.type() != hou.geometryViewportType.Perspective:
            prompt("Can't align this viewport")

        # ALREADY ALIGNED
        elif self.pre_align_camera is not None:
            self.finish()

        # START
        else:
            hvd = self.align_viewport.viewTransform().extractRotationMatrix3().asTupleOfTuples()
            view_right = hou.Vector3(hvd[0])
            view_top = hou.Vector3(hvd[1])
            view_depth = hou.Vector3(hvd[2])
            x = numpy.abs(hvd[0])
            x_max_id = x.argmax()
            x.fill(0.0)
            y = numpy.abs(hvd[1])
            y_max_id = y.argmax()
            y.fill(0.0)
            x[x_max_id] = 1.0
            y[y_max_id] = 1.0
            view_h_abs = hou.Vector3(x)
            view_v_abs = hou.Vector3(y)
            view_d_abs = hou.Vector3(numpy.abs(numpy.cross(x, y)))
            x[x_max_id] = numpy.sign(hvd[0][x_max_id])
            y[y_max_id] = numpy.sign(hvd[1][y_max_id])
            view_h = hou.Vector3(x)
            view_v = hou.Vector3(y)
            view_d = hou.Vector3(numpy.cross(x, y))
            x = view_h[0], view_v[0], view_d[0]
            y = view_h[1], view_v[1], view_d[1]
            z = view_h[2], view_v[2], view_d[2]
            mat = hou.Matrix3((x, y, z))
            
            cam = self.align_viewport.defaultCamera()
            self.pre_align_camera = cam.stash()
            cam.setRotation(mat)
            
            if not cam.isOrthographic():
                orthowidth = hou.Vector3(cam.translation()).distanceTo(hou.Vector3(cam.pivot()))
                cam.setOrthoWidth(orthowidth)
                cam.setPerspective(False)
            
            # MODIFY GRID
            m = self.align_viewport.viewTransform()
            m1 = hou.hmath.buildTranslate(m.extractTranslates()).inverted()
            
            self.pre_align_rf_xform = VIEWER.referencePlane().transform()
            VIEWER.referencePlane().setTransform(m * m1)
            hou.ui.waitUntil(lambda: True)
            VIEWER_WIDGET.installEventFilter(self)
        
    def finish(self):
        VIEWER_WIDGET.removeEventFilter(self)

        # FOR CORRECT MODELER FINISH
        if self.pre_align_camera is not None:
            cam = self.align_viewport.defaultCamera()   
            self.pre_align_camera.setPivot(cam.pivot())                   
            self.pre_align_camera.setTranslation(cam.translation())               
            self.align_viewport.setDefaultCamera(self.pre_align_camera)
            self.pre_align_camera = None

            VIEWER.referencePlane().setTransform(self.pre_align_rf_xform)

align_view = AlignView()


class ViewBarEventFilter(qtc.QObject):
    def post_focus(self):
        hou.qt.mainWindow().activateWindow()
        VIEWER_WIDGET.activateWindow()
        VIEWER_WIDGET.setFocus()

    def eventFilter(self, obj, event):
        if event.type() == qtc.QEvent.Leave:
            executeDeferred(self.post_focus)

        elif event.type() == qtc.QEvent.Enter:
            executeDeferred(modeler.update_viewbar_pos)
        
        return False
        
viewbar_ef = ViewBarEventFilter()


class Symmetry():
    origin = hou.Vector3(0, 0, 0)    
    direction = None 

    def resym_full(self, keep=True):
        sop = modeler.get_sop(set_current=False)
        if sop is not None:
            obj = modeler.ancestor_object(sop)

            if self.direction is not None:
                with hou.undos.group("Modeler: Ressymetry Full"):
                    sl = sop.createOutputNode("modeler::mirror")            
                    sl.parmTuple("origin").set( self.origin )
                    sl.parmTuple("dir").set( self.direction )
                    sl.parm("keep").set(keep)
                    modeler.activate_sop_with_select_state(sl)

                if keep:
                    self.force_instance_removal(sop)
                else:
                    self.update_instance_node(sop)

            else:
                prompt("Symmetry axis must be active")
        else:
            prompt(PROMPT_ONE_GEO)
    
    def resym_half(self):
        self.resym_full(False)

    def toggle_instance(self):
        sop = modeler.get_sop(set_current=False)
        if sop is not None:
            obj = modeler.ancestor_object(sop)
            
            instance_node = self.instance_node(sop)
            if instance_node is not None:
                with hou.undos.disabler():
                    instance_node.destroy()
                    prompt("Symmetry instance node removed")
            else:    
                if self.direction is not None:
                    with hou.undos.disabler():
                        obj_path = obj.path()

                        instance_node = hou.node("/obj").createNode("modeler::instance")
                        instance_node.parm("instancepath").set(obj_path)
                        instance_node.parm("shop_materialpath").set(obj.evalParm("shop_materialpath"))
                        instance_node.moveToGoodPosition()
                        instance_node.setSelectableInViewport(False)

                        if self.direction[0] != 0:
                            instance_node.parmTuple("s").set((-1.0, 1.0, 1.0))
                        elif self.direction[1] != 0:
                            instance_node.parmTuple("s").set((1.0, -1.0, 1.0))
                        else:
                            instance_node.parmTuple("s").set((1.0, 1.0, -1.0))

                        origin = self.origin * obj.worldTransform()
                        instance_node.parmTuple("p").set(origin)

                        r = obj.evalParmTuple("r")
                        instance_node.parmTuple("pr").set(r)

                    prompt("Symmetry instance node created")
                else:
                    prompt("Symmetry axis must be active")

        else:
            prompt(PROMPT_ONE_GEO)

    def subd_instance(self):
        sop = modeler.get_sop(set_current=False)
        if sop is not None:
            pwd = self.instance_node(sop)            
            viewportlod_parm = pwd.parm("viewportlod")
            if viewportlod_parm is None:
                with hou.RedrawBlock() as rb:
                    VIEWER.setPwd(pwd.parent())
                    pwd.setSelected(True, True)
                    modeler.run_stock_hotkey_action("h.pane.gview.increase_subd")
                    sop.setCurrent(True, True)

                on = True

            else:
                if viewportlod_parm.eval() == 5:
                    viewportlod_parm.set(0)
                    on = False
                else:
                    viewportlod_parm.set(5)
                    on = True

            settings = VIEWER.curViewport().settings()
            ds1 = settings.displaySet(hou.displaySetType.SceneObject)
            ds2 = settings.displaySet(hou.displaySetType.GhostObject)

            if on:
                ds1.setShadedMode(hou.glShadingType.Smooth)
                ds2.setShadedMode(hou.glShadingType.Smooth)
            else:
                sm = settings.displaySet(hou.displaySetType.DisplayModel).shadedMode()
                ds1.setShadedMode(sm)
                ds2.setShadedMode(sm)

            ds1.setShadingModeLocked(on)
            ds2.setShadingModeLocked(on)

    def pick_origin(self):
        sop, group, grouptype, empty = modeler.selection()
        if grouptype is not None:
            self.origin = modeler.sop_selection_center(sop, modeler.last_selection)
            prompt("Symmetry origin changed")
        else:
            prompt(PROMPT_POINTS_EDGES_POLYGONS)

    def setup_edit_sop(self, sop):
        obj = modeler.ancestor_object(sop)
        if self.direction is not None:
            sop.parmTuple("symorig").set( self.origin )
            sop.parmTuple("symaxis").set( self.direction )
            sop.setParms({ "symthreshold": 0.0001, "doreflect": True })
        else:
            sop.parm("doreflect").set(False)

    def instance_node(self, sop):
        pwd_path = modeler.ancestor_object(sop).path()
        for i in hou.nodeType(hou.objNodeTypeCategory(), "modeler::instance").instances():
            if i.evalParm("instancepath") == pwd_path:
                return i
        return None

    def force_instance_removal(self, sop):
        instance_node = self.instance_node(sop)
        if instance_node is not None:
            with hou.undos.disabler():
                instance_node.destroy()
                prompt("Symmetry instance node removed")

    def update_instance_node(self, sop):
        instance_node = self.instance_node(sop)
        if instance_node is not None:
            viewportlod = instance_node.evalParm("viewportlod")
            with hou.undos.disabler():
                with hou.RedrawBlock() as rb:
                    instance_node.destroy()
                    self.toggle_instance()
                    self.instance_node(sop).parm("viewportlod").set(viewportlod)

symmetry = Symmetry()


class SpaceEventFilter(qtc.QObject):
    def eventFilter(self, obj, event):
        if event.type() == qtc.QEvent.KeyRelease and not event.isAutoRepeat() and event.key() == qt.Key_Space:
            qt_app.removeEventFilter(self)
            VIEWER_WIDGET.installEventFilter(modeler)
            VIEWER_WIDGET.grabKeyboard()

        return False

space_ef = SpaceEventFilter()


class PreviewSubdEventFilter(qtc.QObject):
    iterations = 3

    def eventFilter(self, obj, event):
        if event.type() == qtc.QEvent.MouseButtonPress:
            if modeler.view_op > -1 or event.button() == qt.RightButton or event.modifiers() & qt.AltModifier:
                return False

            name = qt_app.widgetAt(event.globalPos()).objectName()
            
            if name not in ("parm_slider", "tumble", "pan", "zoom", "frame_selected",  "frame_all", "align_view", "ortho"):
                hou.ui.postEventCallback(self.finish)
                return True
        
        return False

    def start(self, isolines, shade_mode=hou.glShadingType.Smooth):
        pwd = VIEWER.pwd()
        if pwd.childTypeCategory() == hou.sopNodeTypeCategory() and pwd.displayNode() is not None:
            
            # FINISH FROM KEYBOARD HOTKEY
            if pwd.displayNode().userData("__preview_subd__") is not None:
                self.finish()
                return

            viewportlod_parm = pwd.parm("viewportlod")
            if viewportlod_parm is not None and viewportlod_parm.eval() == 5:
                viewportlod_parm.set(0)

        with hou.undos.disabler():
            try:
                display = pwd.displayNode()
            except:
                return

            settings = VIEWER.curViewport().settings()

            s = display.createOutputNode("modeler::preview_subdivided")
            s.setParms({ "iterations": self.iterations, "isolines": isolines })

            s.setUserData("__preview_subd__", "")
            self.pre_state = VIEWER.currentState()
            
            s.setDisplayFlag(True)
            s.setCurrent(True, True)
            VIEWER.enterCurrentNodeState()
            
            ds1 = settings.displaySet(hou.displaySetType.DisplayModel)
            ds2 = settings.displaySet(hou.displaySetType.SceneObject)
            ds3 = settings.displaySet(hou.displaySetType.GhostObject)

            self.pre_mode = ds1.shadedMode()

            ds1.setShadedMode(shade_mode)
            ds2.setShadedMode(shade_mode)
            ds3.setShadedMode(shade_mode)

            qt_app.installEventFilter(self)

    def finish(self):
        with hou.undos.disabler():
            with hou.RedrawBlock() as rb:
                viewport = VIEWER.curViewport()
                settings = viewport.settings()
                ds1 = settings.displaySet(hou.displaySetType.DisplayModel)
                ds2 = settings.displaySet(hou.displaySetType.SceneObject)
                ds3 = settings.displaySet(hou.displaySetType.GhostObject)
                ds1.setShadedMode(self.pre_mode)
                ds2.setShadedMode(self.pre_mode)
                ds3.setShadedMode(self.pre_mode)

                try:
                    sop = VIEWER.pwd().displayNode()
                    if sop.userData("__preview_subd__") is not None:
                        i = sop.inputs()[0]
                        sop.destroy()
                        i.setCurrent(True, True)
    
                except:
                    pass

                finally:

                    if self.pre_state in ("modeler::magnet", "modeler::polypen", "modeler::knife", "modeler::loop"):
                        executeDeferred( partial(VIEWER.setCurrentState, self.pre_state) )

                    qt_app.removeEventFilter(self)

preview_subd_ef = PreviewSubdEventFilter()


class RadialMenuEventFilter(qtc.QObject):
    def show(self, name):
        VIEWER_WIDGET.removeEventFilter(self)
        VIEWER_WIDGET.releaseKeyboard()
        self.viewport = VIEWER.curViewport()
        qt_app.installEventFilter(self)
        VIEWER.displayRadialMenu(name)

    def eventFilter(self, obj, event):
        # IGNORE KEY PRESS
        if event.type() == qtc.QEvent.KeyPress:
            return True
        
        # IGNORE MOUSE PRESS
        elif event.type() == qtc.QEvent.MouseButtonPress:
            return True

        # FINISH ON KEY RELEASE
        elif event.type() == qtc.QEvent.KeyRelease:
            if not event.isAutoRepeat():
                qt_app.removeEventFilter(self)
                qtest.keyClick(obj, qt.Key_Return, qt.NoModifier)
                VIEWER_WIDGET.installEventFilter(modeler)
                VIEWER_WIDGET.grabKeyboard()
            return True
        
        # FINISH ON MOUSE RELEASE (MENU CALLED FROM LAUNCHER)
        elif event.type() == qtc.QEvent.MouseButtonRelease:
            qt_app.removeEventFilter(self)
            qtest.keyClick(obj, qt.Key_Return, qt.NoModifier)
            VIEWER_WIDGET.installEventFilter(modeler)
            VIEWER_WIDGET.grabKeyboard()
            return True
        
        return False

radial_menu_ef = RadialMenuEventFilter()


class Modeler(qtc.QObject):
    toolbar_reload_callback_script = '''
import imp
import modeler.ui
import modeler.states

modeler.ui.align_view.finish()
modeler.ui.modeler.reset_shading_mode()

if modeler.ui.modeler.viewbar is not None:
    modeler.ui.VIEWER_WIDGET.removeEventFilter(modeler.ui.modeler)
    modeler.ui.modeler.viewbar.setParent(None)

modeler.ui.modeler.widget.setParent(None)

for state_name in ("modeler::magnet", "modeler::polypen", "modeler::knife", "modeler::grab_uv", "modeler::grab", "modeler::grab_peak", "modeler::grab_rotate", "modeler::grab_scale", "modeler::grab_rotate_uv", "modeler::grab_scale_uv"):
    hou.ui.unregisterViewerState(state_name)

imp.reload(modeler.ui)
imp.reload(modeler.states)

for pane_tab in hou.ui.paneTabs():
    if pane_tab.type() == hou.paneTabType.PythonPanel and pane_tab.label() == "Modeler":
        pane_tab.reloadActiveInterface()

VIEWER = hou.ui.paneTabOfType(hou.paneTabType.SceneViewer)
VIEWER_WIDGET = hou.modeler.ui.get_scene_viewer_mouse_widget()
'''


    view_op = -1
    _viewbar_convert_mode = False
    is_tablet = False
    space_pressed = False

    nodes_not_for_mmb_grab = ( "modeler::polypen", "modeler::magnet", "topobuild", "modeler::knife", "modeler::qprimitive", "polyextrude::2.0",
                               "copyxform", "xform", "modeler::shift", "modeler::array", "modeler::falloff_xform",
                               "modeler::boolean", "uvflatten::3.0", "mountain::2.0", "modeler::bevel_pro",
                               "box", "tube", "sphere", "circle", "platonic", "font", "lsystem" )

    def eventFilter(self, obj, event):
        if event.type() == qtc.QEvent.MouseMove and self.view_op > -1:

            if self.drag_started:
                return False

            else:
                if abs(event.x() - self.start_x) < hou.ui.scaledSize(8) and abs(event.y() - self.start_y) < hou.ui.scaledSize(8):
                    return True
                else:

                    # TUMBLE: DOUBLE MODE
                    if self.view_op == 0:
                        self.view_op_button = qt.LeftButton

                        # UNALIGN VIEW
                        if self.view_op == 0:
                            align_view.finish()


                    # PAN
                    elif self.view_op == 1:
                        self.view_op_button = qt.MiddleButton

                    # ZOOM
                    # elif self.view_op == 2:
                    else:
                        x_delta = (self.initial_cursor_pos.x() - qtg.QCursor.pos().x())

                        if self.cam.isOrthographic():
                            ortho_width = self.initial_ortho_width + x_delta * self.delta
                            self.cam.setOrthoWidth(max(0.2, ortho_width))
                        else:
                            new_t = self.initial_cam_t + hou.Vector3(0, 0, x_delta * self.delta)
                            self.cam.setTranslation(new_t)

                        return True


                    VIEWER_WIDGET.removeEventFilter(self)
                    qtest.keyPress(VIEWER_WIDGET, qt.Key_Alt, qt.NoModifier)
                    qtest.mousePress(VIEWER_WIDGET, self.view_op_button, qt.AltModifier, event.pos())
                    VIEWER_WIDGET.installEventFilter(self)

                    self.drag_started = True

            return True

        elif event.type() == qtc.QEvent.MouseButtonPress:
            self.is_tablet = False
            
            if event.modifiers() & qt.AltModifier:
                return False

            elif event.button() == qt.MiddleButton:
                state = VIEWER.currentState()

                if VIEWER.currentNode().type().name() == "stroke" or state == "modeler::polygons":
                    hou.ui.postEventCallback(self.polygons)
                    return True

                elif state not in self.nodes_not_for_mmb_grab:

                    self.press_pos = event.pos()
                    
                    mods = event.modifiers()
                    if mods == qt.ShiftModifier:
                        hou.modeler.states.Grab.override_command = "constraint_h_axis"
                    
                    elif mods == qt.ControlModifier:
                        hou.modeler.states.Grab.override_command = "constraint_v_axis"
                    
                    elif mods == qt.ControlModifier | qt.ShiftModifier:
                        hou.modeler.states.Grab.override_command = "constraint_plane"

                    hou.modeler.states.grab("modeler::grab")

            # LMB OR RMB PRESSED WHILE MMB ALREADY PRESSED
            elif ( (event.button() == qt.LeftButton and event.buttons() == qt.MiddleButton | qt.LeftButton) or (event.button() == qt.RightButton and event.buttons() == qt.MiddleButton | qt.RightButton) ) and event.modifiers() == qt.NoModifier:
                state = VIEWER.currentState()
                if state.startswith("modeler::grab"):
                    press_pos = event.pos()
                    if abs(press_pos.x() - self.press_pos.x()) > abs(press_pos.y() - self.press_pos.y()): 
                        VIEWER.runStateCommand("constraint_h_axis")
                    else:
                        VIEWER.runStateCommand("constraint_v_axis")
                
                elif state == "modeler::polypen":
                    VIEWER.runStateCommand("move_loop")

                return True

            # START VIEW OPERATION
            elif event.button() == qt.RightButton:
                if event.modifiers() == qt.NoModifier:
                    self.start_time = time.time()
                    self.start_x = event.x()
                    self.start_y = event.y()

                    self.drag_started = False
                    
                    viewport = VIEWER.curViewport()

                    vp_x, vp_y, _ = viewport.windowToViewportTransform().extractTranslates()
                    vp_x, vp_y = abs(vp_x), abs(vp_y)
                    vp_w, vp_h = viewport.resolutionInPixels()
                    x, y = event.x(), VIEWER_WIDGET.height() - event.y()


                    y_delta = vp_h * 0.4
                    x_delta = vp_w / 2.0

                    if ( vp_y + y_delta ) < y < (vp_y + vp_h):
                        self.view_op = 0

                    else:
                        if vp_x <= x <= vp_x + x_delta:
                            self.view_op = 1
                        
                        elif vp_x + x_delta <= x <= vp_x + vp_w:
                            self.view_op = 2

                            self.initial_cursor_pos = qtg.QCursor.pos()
                            self.cam = viewport.defaultCamera()
                            self.initial_ortho_width = self.cam.orthoWidth()
                            self.initial_cam_t = hou.Vector3(self.cam.translation())
                            self.initial_cam_p = hou.Vector3(self.cam.pivot())
                            self.delta = (self.initial_cam_t - self.initial_cam_p).length() / float(hou.ui.scaledSize(500))

                return True


        elif event.type() == qtc.QEvent.MouseButtonRelease:
            self.is_tablet = False
            if event.modifiers() & qt.AltModifier:
                return False

            # REPEAT LOOP
            if event.button() == qt.LeftButton and VIEWER.currentState() == "edgeloop" and VIEWER.currentNode().evalParm("splitloc"):
                VIEWER.runShelfTool("sop_edgeloop")

            elif event.button() == qt.MiddleButton and VIEWER.currentState().startswith("modeler::grab"):
                VIEWER.setCurrentState("select")
            
            elif self.view_op > -1:
                VIEWER_WIDGET.removeEventFilter(modeler)

                if (time.time() - self.start_time) < 0.3 and not self.drag_started:
                    VIEWER.displayRadialMenu("modeler")

                elif self.view_op in (0, 1) and self.drag_started:
                    qtest.mouseRelease(VIEWER_WIDGET, self.view_op_button, qt.AltModifier, event.pos())
                    qtest.keyRelease(VIEWER_WIDGET, qt.Key_Alt, qt.NoModifier)

                VIEWER_WIDGET.activateWindow()
                VIEWER_WIDGET.setFocus()
                VIEWER_WIDGET.installEventFilter(modeler)

                self.view_op = -1

                return True

        # PEN PRESS
        elif event.type() == qtc.QEvent.TabletPress:
            self.is_tablet = True
        
        # PEN RELEASE
        elif event.type() == qtc.QEvent.TabletRelease:
            self.is_tablet = True
        
        # DOUBLE CLICK
        elif event.type() == qtc.QEvent.MouseButtonDblClick:
            if event.button() == qt.RightButton:
                return True

            pos = event.pos()
            x = pos.x()
            y = VIEWER_WIDGET.height() - pos.y()
            cursor_node = VIEWER.curViewport().queryNodeAtPixel(x, y)
            cur_node = VIEWER.currentNode()

            is_node = VIEWER.curViewport().queryPrimAtPixel(None, x, y) is not None
            in_space = not is_node and cursor_node is None

            if is_node and cursor_node is None:
                cursor_node = cur_node

            elif cursor_node is not None and self.ancestor_object(cursor_node).type().name() == "modeler::backdrop":
                in_space = True

            # CURSOR IS IN SPACE
            if in_space:
                if VIEWER.selectionMode() == hou.selectionMode.Geometry:
                    VIEWER.setSelectionMode(hou.selectionMode.Object)
                    VIEWER.setCurrentState("select")
                    
                    prompt("Objects mode")

                elif VIEWER.selectionMode() == hou.selectionMode.Object:
                    hou.clearAllSelected()

            else:
                cat = cursor_node.type().category()

                # SOP
                if cat == hou.sopNodeTypeCategory():
                    if cur_node == cursor_node:
                        mods = event.modifiers()
                        VIEWER_WIDGET.removeEventFilter(self)
                        qtest.mouseDClick(VIEWER_WIDGET, qt.LeftButton, mods, pos)
                        if self.is_tablet:
                            qtest.mouseClick(VIEWER_WIDGET, qt.LeftButton, mods, pos)
                        VIEWER_WIDGET.installEventFilter(self)
                    
                    # CURSOR NODE IS NOT CURRENT. MAKE IT
                    elif self.ancestor_object(cursor_node).isSelectableInViewport():
                        cursor_node.setCurrent(True, True)
                        prompt(cursor_node.path())

                # OBJ
                elif cat == hou.objNodeTypeCategory() and cursor_node.isSelectableInViewport():
                    VIEWER.setCurrentState("select")
                    VIEWER.setSelectionMode(hou.selectionMode.Geometry)
                    cursor_node.setCurrent(True, True)
                    
                    prompt(cursor_node.path())

            return True
        
        # KEY PRESS
        elif event.type() == qtc.QEvent.KeyPress and hou.ui.paneTabUnderCursor() == VIEWER:
            key = event.key()
            mods = event.modifiers()
            
            # RESERVED HOTKEYS
            if key == qt.Key_Tab:
                return False

            # IGNORE AUTOREPEAT
            elif event.isAutoRepeat():
                return True


            elif key == qt.Key_Space and mods == qt.NoModifier:
                VIEWER_WIDGET.releaseKeyboard()
                VIEWER_WIDGET.removeEventFilter(self)
                qt_app.installEventFilter(space_ef)
                return False

            hotkey = qtg.QKeySequence(int(mods) + key).toString()
            try:
                resource_name = hotkey_manager.hotkeys[ hotkey ]
                
                if hou.shelves.tool(resource_name) is None:
                    rm_menu = hou.ui.radialMenu(resource_name)
                    
                    # RUN MODELER UI BUTTON RESOURCE
                    if rm_menu is None:
                        self.modeler_resource_exec(resource_name)
                    
                    # SHOW RADIAL MENU
                    else:
                        radial_menu_ef.show(resource_name)
                
                # RUN SHELF TOOL
                else:
                    VIEWER.runShelfTool(resource_name)
                
                return True

            except KeyError:


                return False
        
        # ENTER
        elif event.type() == qtc.QEvent.Enter:
            VIEWER_WIDGET.grabKeyboard()
            VIEWER_WIDGET.activateWindow()
            VIEWER_WIDGET.setFocus()
        
        # LEAVE
        elif event.type() == qtc.QEvent.Leave:
            VIEWER_WIDGET.releaseKeyboard()
            return True

        return False

    def cusp_angle_callback(self, value):
        for viewport in VIEWER.viewports():
            viewport.settings().vertexNormalCuspAngle(value)

    def mp(self, event):
        if event.button() == qt.MiddleButton:
            event.ignore()
        else:
            super(qtw.QTreeWidget, self.tree).mousePressEvent(event)

    def __init__(self):
        super(Modeler, self).__init__(None)

        # MAIN WIDGET
        self.qui_loader = QUiLoader()
        filepath = modeler_path + "/config/qt_designer/modeler_main.ui"
        self.qui_loader.setWorkingDirectory(os.path.dirname(filepath))
        ui_file = qtc.QFile(filepath)
        ui_file.open(qtc.QFile.ReadOnly)
        self.widget = self.qui_loader.load(ui_file)
        self.widget.setWindowFlags(qt.Widget)
        self.widget.setParent(hou.qt.mainWindow())
        self.widget.setContentsMargins(hou.ui.scaledSize(2), hou.ui.scaledSize(2), hou.ui.scaledSize(2), hou.ui.scaledSize(2))
        self.widget.setStyleSheet("QWidget { font-size: %dpx; background: #303030; } \
                                   QFrame {color: #606060; } \
                                   QLineEdit { border: none; border-radius: 0px; } \
                                   QToolTip { font-size: %dpx; font-weight: bold; padding: %dpx; background: #aaa999; color: #242424; border: %dpx solid #222222; } \
                                   QSlider::groove { background: #111111; border: none; height: %dpx; } \
                                   QSlider::handle { background: #111111; border: none; width: %dpx; } \
                                   QToolButton {border: none; color: #999999; } QToolButton::checked {background: #181818; } QToolButton::hover {background: #444444; }" % ( hou.ui.scaledSize(11),
                                                                                                                                                                             hou.ui.scaledSize(11),
                                                                                                                                                                             hou.ui.scaledSize(9),
                                                                                                                                                                             hou.ui.scaledSize(2),
                                                                                                                                                                             hou.ui.scaledSize(2),
                                                                                                                                                                             hou.ui.scaledSize(12)))
        opacity_slider = self.widget.findChild(qtw.QSlider, "opacity_slider")
        opacity_slider.valueChanged.connect(self.opacity_slider_callback)

        # self.widget.findChild(qtw.QSlider, "subd_slider").setStyleSheet("")

        size = qtc.QSize(hou.ui.scaledSize(28), hou.ui.scaledSize(28))
        icon_size = qtc.QSize(hou.ui.scaledSize(16), hou.ui.scaledSize(16))

        # FIND TOOLBAR BUTTONS AND CONNECT THEM TO CALLBACKS
        for button in self.widget.findChildren(qtw.QToolButton):
            button.setFixedSize(size)
            button.setIconSize(icon_size)
            button.clicked.connect(partial(self.modeler_resource_clicked_callback, button.objectName()))

        self.viewbar = None

        # SETUP WIDGET
        ui_file = qtc.QFile( modeler_path + "/config/qt_designer/modeler_setup.ui" )
        ui_file.open(qtc.QFile.ReadOnly)
        self.setup_widget = self.qui_loader.load(ui_file)
        self.setup_widget.setWindowFlags(qt.Widget)
        self.setup_widget.setParent(self.widget)
        
        self.setup_widget.setStyleSheet("QWidget { background: #282828; color: #aaaaaa; } \
                                         QGroupBox { border: 2px solid #777777; } \
                                         QLineEdit, QSpinBox { background: #020202; border: none; border-radius: %dpx; } \
                                         QToolButton { background: #333333; } \
                                         QSlider::groove { background: #111111; border: none; height: %dpx; } \
                                         QSlider::handle { background: #111111; border: none; width: %dpx; }" % (hou.ui.scaledSize(2), hou.ui.scaledSize(2), hou.ui.scaledSize(12)))
        
        self.setup_widget.setContentsMargins(hou.ui.scaledSize(10), hou.ui.scaledSize(10), hou.ui.scaledSize(10), hou.ui.scaledSize(10))
        self.setup_widget_helper = qtw.QWidget(self.setup_widget)
        self.setup_widget_helper.resize(0, 0)

        self.setup_widget.findChild(qtw.QToolButton, "youtube_channel").clicked.connect( partial(qtg.QDesktopServices.openUrl, "https://www.youtube.com/c/ModelersOfficialChannel/videos") )
        self.setup_widget.findChild(qtw.QToolButton, "open_discord").clicked.connect( partial(qtg.QDesktopServices.openUrl, "https://discord.com/channels/772396976452796437") )
        self.setup_widget.findChild(qtw.QToolButton, "join_discord").clicked.connect( partial(qtg.QDesktopServices.openUrl, "https://discord.gg/Ud7xUcQfMu") )

        # UV WIDGET
        ui_file = qtc.QFile( modeler_path + "/config/qt_designer/modeler_uv.ui" )
        ui_file.open(qtc.QFile.ReadOnly)
        self.uv_widget = self.qui_loader.load(ui_file)
        self.uv_widget.setWindowFlags(qt.Widget)
        self.uv_widget.setParent(self.widget)
        self.uv_widget.setContentsMargins(hou.ui.scaledSize(10), hou.ui.scaledSize(10), hou.ui.scaledSize(10), hou.ui.scaledSize(10))
        self.uv_widget.setStyleSheet(self.setup_widget.styleSheet())
        self.uv_widget.findChild(qtw.QToolButton, "auto_unwrap").clicked.connect(self.auto_unwrap)
        self.uv_widget.findChild(qtw.QToolButton, "flatten").clicked.connect(self.flatten)
        self.uv_widget.findChild(qtw.QToolButton, "layout").clicked.connect(self.uv_layout)
        self.uv_widget.findChild(qtw.QToolButton, "udim_export").clicked.connect(self.udim_export)
        self.uv_widget_helper = qtw.QWidget(self.uv_widget)
        self.uv_widget_helper.resize(0, 0)

        cusp_angle = self.widget.findChild(qtw.QSlider, "cusp_angle")
        cusp_angle.valueChanged.connect(self.cusp_angle_callback)

        # TAB WIDGET
        self.tab_widget = self.widget.findChild(qtw.QTabWidget, "tab_widget")
        self.tab_widget.setStyleSheet("QTabBar::tab { color: #888888; background: #151515; border: %dpx solid #111111; } QTabBar::tab:!selected { background: #151515; color: #606060; }" % hou.ui.scaledSize(1))

        # TOOLS & RADIAL MENUS TREE
        self.tree = qtw.QTreeWidget()
        self.tree.header().setStretchLastSection(True)
        self.tree.setIconSize(qtc.QSize(hou.ui.scaledSize(16), hou.ui.scaledSize(16)))
        self.tree.setIndentation(hou.ui.scaledSize(10))
        self.tree.setRootIsDecorated(False)
        self.tree.setHeaderHidden(True)
        self.tree.setHorizontalScrollBarPolicy(qt.ScrollBarAlwaysOff)
        # self.tree.setVerticalScrollBarPolicy(qt.ScrollBarAlwaysOff)
        self.tree.setDragEnabled(True)
        self.tree.itemClicked.connect(self.tree_clicked)
        self.tree.setStyleSheet( "QTreeView { border: none; padding: %dpx; outline: none; background: #202020; show-decoration-selected: 0; } \
                                  QTreeView::branch { border-image: url(none.png); } \
                                  QTreeView::item { margin-top: %dpx; } \
                                  QTreeView::item:selected { background: #333333; color: #999999; } \
                                  QTreeView::item:!selected { background: #202020; color: #999999; } \
                                  QScrollBar {background: #202020; border: none; width: %dpx; margin-top: 0dpx; margin-bottom: 0px; } \
                                  QScrollBar:handle { background: #303030; border-radius: %dpx;} \
                                  QScrollBar::add-line:vertical {border: none; background: #202020; width: 0; height: 0; } \
                                  QScrollBar::sub-line:vertical { border: none; background: #202020; width: 0; height: 0; }" % (hou.ui.scaledSize(2), hou.ui.scaledSize(2), hou.ui.scaledSize(10), hou.ui.scaledSize(5)) )

        self.tree.setVerticalScrollMode(qtw.QAbstractItemView.ScrollPerPixel)
        self.tree.setHorizontalScrollMode(qtw.QAbstractItemView.ScrollPerPixel)

        # FILTER FIELD
        self.filter_field = self.widget.findChild(qtw.QLineEdit, "filter_field")
        self.filter_field.textChanged.connect(self.filter_tree_slot)
        self.filter_field.setStyleSheet("QLineEdit { background: #111111; border: none; height: %dpx;}" % hou.ui.scaledSize(20))

        # FAVORITES SECTION
        self.favorites = qtw.QListWidget()
        self.favorites.setIconSize(qtc.QSize(hou.ui.scaledSize(16), hou.ui.scaledSize(16)))
        self.favorites.setHorizontalScrollBarPolicy(qt.ScrollBarAlwaysOff)
        self.favorites.setMovement(qtw.QListView.Free)
        self.favorites.setAcceptDrops(True)
        self.favorites.setDragEnabled(True)
        self.favorites.setDefaultDropAction(qt.MoveAction)
        self.favorites.dropEvent = self.favorites_dropEvent
        self.favorites.itemClicked.connect(self.favorites_clicked)
        self.favorites.setStyleSheet( "QListView { padding-left: %dpx; padding-top: %dpx; outline: none; background: #181818; show-decoration-selected: 0; border: none; } \
                                  QListView::branch { border-image: url(none.png); } \
                                  QListView::item:selected { background: #111111; border: none; color: #999999; } \
                                  QListView::item:!selected { background: #181818; border: none; color: #999999; } \
                                  QScrollBar {background: #181818; border: none; width: %dpx; margin-top: 0dpx; margin-bottom: 0px; } \
                                  QScrollBar:handle { background: #303030; border-radius: %dpx;} \
                                  QScrollBar::add-line:vertical {border: none; background: #202020; width: 0; height: 0; } \
                                  QScrollBar::sub-line:vertical { border: none; background: #202020; width: 0; height: 0; }" % (hou.ui.scaledSize(4), hou.ui.scaledSize(4), hou.ui.scaledSize(10), hou.ui.scaledSize(5)) )
        
        # SPLITTER
        self.splitter = qtw.QSplitter(qt.Vertical)
        self.splitter.setStyleSheet("QSplitter::handle { background: #333333; height: %dpx; }" % hou.ui.scaledSize(5))
        self.splitter.addWidget(self.favorites)
        self.splitter.addWidget(self.tree)
        self.splitter.setStretchFactor(1, 1)
        
        # ADD TABS TO TREE WIDGET
        self.tab_widget.addTab(self.splitter, "Shelf Tools")
        self.tab_widget.addTab(self.uv_widget, "UV")
        self.tab_widget.addTab(self.setup_widget, "Setup")
        
        # REGISTER FILE NAMES
        self.favorites_config_file = hou.expandString("$HOUDINI_USER_PREF_DIR") + "/modeler_2022_favorites.pref"
        self.hotkeys_file = hou.expandString("$HOUDINI_USER_PREF_DIR") + "/modeler_2022_hotkeys.pref"
        self.rm_hotkeys_file = hou.expandString("$HOUDINI_USER_PREF_DIR") + "/modeler_2022_rm_hotkeys.pref"
        self.setup_file = hou.expandString("$HOUDINI_USER_PREF_DIR") + "/modeler_2022_setup.pref"
        
        # SETUP VARIABLES AND CREATE PYTHON OBJECTS
        self.rm_icon = hou.qt.Icon("MODELER_radial_menu", hou.ui.scaledSize(20), hou.ui.scaledSize(20))
        self.hotkeys_conflicts = {}

        # REGISTER SETUP UI CONTROLS
        self.material_type = self.setup_widget.findChild(qtc.QObject, "material_type")
        self.create_at_sop_level = self.setup_widget.findChild(qtc.QObject, "create_at_sop_level")
        self.template_at_sop_level = self.setup_widget.findChild(qtc.QObject, "template_at_sop_level")
        

        for axis in ("x", "y", "z", "neg_x", "neg_y", "neg_z"):
            self.widget.findChild(qtw.QToolButton, "sym_axis_" + axis).clicked.connect(self.sym_axis_callback)

        # DO STAGES
        self.load_config_files()
        self.build_tree()
        self.build_favorites_list()

        # CONNECT SETUP UI CONTROLS
        self.material_type.textChanged.connect(self.update_setup_list_from_ui)
        self.template_at_sop_level.clicked.connect(self.update_setup_list_from_ui)
        self.setup_widget.findChild(qtw.QToolButton, "reset").clicked.connect(self.reset_setup_callback)
        self.setup_widget.findChild(qtw.QToolButton, "clear_favorites").clicked.connect(self.clear_favorites_callback)
        self.setup_widget.findChild(qtw.QToolButton, "reset_hotkeys").clicked.connect(hotkey_manager.reset)
        self.setup_widget.findChild(qtw.QToolButton, "delete_hotkeys").clicked.connect(hotkey_manager.delete)

        # FOR CORRECT SAVING SETUP ON CLOSE OR HOUDINI EXIT
        self.tree.hideEvent = self.destroy_event
        self.setup_widget_helper.hideEvent = self.destroy_event
        self.uv_widget_helper.hideEvent = self.destroy_event

        # DEFAULT TOPO STROKES
        self._topo_fuse_tol = 0.01
        self._topo_strokes_resample_length = 0.01
        self._topo_strokes_stripe_segs = 1

        # UPDATE TOPO
        if self.topo_get_src_object() is not None:
            self.widget.findChild(qtw.QToolButton, "topo_toggle").setChecked(True)

    def auto_unwrap(self):
        sop, group, grouptype, empty = self.selection()
        if grouptype == hou.geometryType.Primitives:
            with hou.undos.group("Modeler: Auto Unwrap"):
                sop = sop.createOutputNode("modeler::auto_unwrap")        
                sop.parm("group").set(group)
                self.activate_sop_with_state(sop)
        else:
            prompt(PROMPT_POLYGONS)

    def flatten(self):
        sop, group, grouptype, empty = self.selection()
        if grouptype == hou.geometryType.Primitives:
            with hou.undos.group("Modeler: Flatten"):
                sop = sop.createOutputNode("uvflatten::3.0")        
                sop.parm("group").set(group)
                self.activate_sop_with_state(sop)
        
        elif grouptype == hou.geometryType.Edges:
            with hou.undos.group("Modeler: Flatten"):
                f = sop.createOutputNode("uvflatten::3.0")        
                if sop.type().name() == "modeler::auto_unwrap" and sop.evalParm("do_output_group") and sop.evalParm("output_group_name"):
                    f.parm("seamgroup").set(sop.evalParm("output_group_name"))
                else:
                    f.parm("seamgroup").set(group)
                self.activate_sop_with_state(f)
        
        else:
            prompt(PROMPT_EDGES_OR_POLYGONS)

    def uv_layout(self):
        sop, group, grouptype, empty = self.selection()
        if grouptype == hou.geometryType.Primitives:
            with hou.undos.group("Modeler: UV Layout"):
                sop = sop.createOutputNode("uvlayout::3.0")
                sop.setParms({ "group": group, "axisalignislands": 2, "paddingboundary": True, "padding": 4, "correctareas": True })    
                self.activate_sop_with_state(sop)
        else:
            prompt(PROMPT_POLYGONS)

    def udim_export(self):
        sop = self.get_sop()
        if sop is not None:
            with hou.undos.group("Modeler: UDIM Export"):
                sop = sop.createOutputNode("modeler::udim_export")
                self.activate_sop_with_select_state(sop)
        else:
            prompt(PROMPT_ONE_GEO)

    def sym_axis_callback(self, checked):
        text = self.sender().text()

        if text == "X":
            self.widget.findChild(qtw.QToolButton, "sym_axis_y").setChecked(False)
            self.widget.findChild(qtw.QToolButton, "sym_axis_z").setChecked(False)
            self.widget.findChild(qtw.QToolButton, "sym_axis_neg_x").setChecked(False)
            self.widget.findChild(qtw.QToolButton, "sym_axis_neg_y").setChecked(False)
            self.widget.findChild(qtw.QToolButton, "sym_axis_neg_z").setChecked(False)
            symmetry.direction = hou.Vector3(1, 0, 0) if checked else None

        elif text == "Y":
            self.widget.findChild(qtw.QToolButton, "sym_axis_x").setChecked(False)
            self.widget.findChild(qtw.QToolButton, "sym_axis_z").setChecked(False)
            self.widget.findChild(qtw.QToolButton, "sym_axis_neg_x").setChecked(False)
            self.widget.findChild(qtw.QToolButton, "sym_axis_neg_y").setChecked(False)
            self.widget.findChild(qtw.QToolButton, "sym_axis_neg_z").setChecked(False)
            symmetry.direction = hou.Vector3(0, 1, 0) if checked else None

        elif text == "Z":
            self.widget.findChild(qtw.QToolButton, "sym_axis_x").setChecked(False)
            self.widget.findChild(qtw.QToolButton, "sym_axis_y").setChecked(False)
            self.widget.findChild(qtw.QToolButton, "sym_axis_neg_x").setChecked(False)
            self.widget.findChild(qtw.QToolButton, "sym_axis_neg_y").setChecked(False)
            self.widget.findChild(qtw.QToolButton, "sym_axis_neg_z").setChecked(False)
            symmetry.direction = hou.Vector3(0, 0, 1) if checked else None

        elif text == "-X":
            self.widget.findChild(qtw.QToolButton, "sym_axis_x").setChecked(False)
            self.widget.findChild(qtw.QToolButton, "sym_axis_y").setChecked(False)
            self.widget.findChild(qtw.QToolButton, "sym_axis_z").setChecked(False)
            self.widget.findChild(qtw.QToolButton, "sym_axis_neg_y").setChecked(False)
            self.widget.findChild(qtw.QToolButton, "sym_axis_neg_z").setChecked(False)
            symmetry.direction = hou.Vector3(-1, 0, 0) if checked else None

        elif text == "-Y":
            self.widget.findChild(qtw.QToolButton, "sym_axis_x").setChecked(False)
            self.widget.findChild(qtw.QToolButton, "sym_axis_y").setChecked(False)
            self.widget.findChild(qtw.QToolButton, "sym_axis_z").setChecked(False)
            self.widget.findChild(qtw.QToolButton, "sym_axis_neg_x").setChecked(False)
            self.widget.findChild(qtw.QToolButton, "sym_axis_neg_z").setChecked(False)
            symmetry.direction = hou.Vector3(0, -1, 0) if checked else None

        else:
            self.widget.findChild(qtw.QToolButton, "sym_axis_x").setChecked(False)
            self.widget.findChild(qtw.QToolButton, "sym_axis_y").setChecked(False)
            self.widget.findChild(qtw.QToolButton, "sym_axis_z").setChecked(False)
            self.widget.findChild(qtw.QToolButton, "sym_axis_neg_x").setChecked(False)
            self.widget.findChild(qtw.QToolButton, "sym_axis_neg_y").setChecked(False)
            symmetry.direction = hou.Vector3(0, 0, -1) if checked else None

    def sym_axis_menu_triggered_callback(self, text):
        self.widget.findChild(qtw.QToolButton, "sym_axis").setText(text)

        if text == "X":
            symmetry.direction = hou.Vector3(1, 0, 0)

        elif text == "Y":
            symmetry.direction = hou.Vector3(0, 1, 0)

        elif text == "Z":
            symmetry.direction = hou.Vector3(0, 0, 1)

        elif text == "-X":
            symmetry.direction = hou.Vector3(-1, 0, 0)

        elif text == "-Y":
            symmetry.direction = hou.Vector3(0, -1, 0)

        elif text == "-Z":
            symmetry.direction = hou.Vector3(0, 0, -1)

        else:
            symmetry.direction = None

    def opacity_slider_callback(self, value):
        hou.qt.mainWindow().setWindowOpacity((value + 1) / 100.0)

    def modeler_resource_exec(self, name):
        # RELOAD
        if name == "reload":
            exec(self.toolbar_reload_callback_script)
            return

        elif name == "side_by_side_layout":
            if VIEWER.viewportLayout() == hou.geometryViewportLayout.Single:
                VIEWER.setViewportLayout(hou.geometryViewportLayout.DoubleSide)
            else:
                VIEWER.setViewportLayout(hou.geometryViewportLayout.Single, 1)
                VIEWER.curViewport().changeType(hou.geometryViewportType.Perspective)

        elif name == "qlight":
            VIEWER.runShelfTool("modeler::qlight")

        elif name == "backdrop":
            VIEWER.runShelfTool("modeler::backdrop")

        elif name == "tgl_backdrop":
            instances = hou.nodeType(hou.objNodeTypeCategory(), "modeler::backdrop").instances()
            if instances:
                with hou.undos.disabler():
                    instances[0].setDisplayFlag(not instances[0].isDisplayFlagSet())
            else:
                prompt("No backdrop objects")

        elif name == "mini_ui":
            b = hou.ui.hideAllMinimizedStowbars()
            b = not b
            hou.ui.setHideAllMinimizedStowbars(b)
            hou.ui.curDesktop().shelfDock().show(not b)
    
            if self.viewbar is not None and self.viewbar.isVisible():
                executeDeferred(self.update_viewbar_pos)

        elif name == "modeler_mode":
            if self.viewbar is None:
                # VIEWBAR
                ui_file = qtc.QFile(modeler_path + "/config/qt_designer/modeler_viewbar.ui")
                ui_file.open(qtc.QFile.ReadOnly)
                self.viewbar = self.qui_loader.load(ui_file, hou.qt.mainWindow())
                self.viewbar.setWindowFlags(qt.Window|qt.FramelessWindowHint)
                self.viewbar.setWindowOpacity(0.2)
                self.viewbar.resize(hou.ui.scaledSize(800), hou.ui.scaledSize(60))
                self.viewbar.setStyleSheet("QWidget { border: none; color: black; background: none; } \
                                            QToolButton::checked { border: %dpx solid white; } \
                                            QToolTip { font-size: %dpx; font-weight: bold; padding: %dpx; background: #aaa999; color: #242424; border: %dpx solid #222222; }" % (hou.ui.scaledSize(3), hou.ui.scaledSize(11), hou.ui.scaledSize(9), hou.ui.scaledSize(2)) )
                
                self.viewbar.setAutoFillBackground(False)

                self.viewbar.setAttribute( qt.WA_PaintOnScreen, True)
                self.viewbar.setAttribute( qt.WA_TranslucentBackground, True)

                size = qtc.QSize(hou.ui.scaledSize(36), hou.ui.scaledSize(36))
                # FIND TOOLBAR BUTTONS AND CONNECT THEM TO CALLBACKS
                for button in self.viewbar.findChildren(qtw.QToolButton):
                    button.setFixedSize(size)
                    button.setIconSize(size)
                
                    if button.objectName() in ("parm_slider", "tumble", "pan", "zoom"):
                        button.pressed.connect( partial(self.modeler_resource_clicked_callback, button.objectName()))
                    else:
                        button.clicked.connect( partial(self.modeler_resource_clicked_callback, button.objectName()))

                self.viewbar.setFixedSize(hou.ui.scaledSize(36) * 30, hou.ui.scaledSize(36))

            if self.viewbar.isVisible():
                self.viewbar.hide()
                self.viewbar.removeEventFilter(viewbar_ef)

                try:
                    VIEWER_WIDGET.removeEventFilter(self)
                except:
                    pass
                
                VIEWER.setPickModifier(hou.pickModifier.Replace)

                self.reset_shading_mode()
            else:
                self.update_viewbar_pos()
                self.viewbar.show()

                if VIEWER.snappingMode() == hou.snappingMode.Multi:
                    self.viewbar.findChild(qtw.QToolButton, "multisnap").setChecked(True)

                self.viewbar.installEventFilter(viewbar_ef)

                try:
                    VIEWER_WIDGET.installEventFilter(self)
                except:
                    pass

                hotkey_manager.load()

                VIEWER.setPickModifier(hou.pickModifier.Replace)

        elif name == "convert_to_shells":
            sop, group, grouptype, empty = self.selection()

            if grouptype is not None:
                with hou.undos.group("Modeler: Convert Selection To Loops"):
                    with hou.RedrawBlock() as rb:
                        if grouptype == hou.geometryType.Primitives:
                            sel = self.last_selection
                        else:
                            sel = self.last_selection.freeze()
                            sel.convert(self.last_selection_geo, hou.geometryType.Primitives)
                            VIEWER.setPickGeometryType(hou.geometryType.Primitives)
                            hou.ui.waitUntil(lambda: True)

                        group = sel.selectionString(self.last_selection_geo, force_numeric=True)
                        tmp_sop = sop.createOutputNode("groupexpand")
                        tmp_sop.setParms({ "group": group, "outputgroup": "", "floodfill": True })
                        VIEWER.setCurrentState("select")
                        VIEWER.setCurrentGeometrySelection( hou.geometryType.Primitives, (sop,), (tmp_sop.geometry().selection(),) )
                        tmp_sop.destroy()
            
            else:
                prompt("Select one or more geometry components and try again.")            

        elif name == "convert_to_loops":
            sop, group, grouptype, empty = self.selection()

            with hou.undos.group("Modeler: Convert Selection To Loops"):
                if grouptype == hou.geometryType.Edges:
                    if self.last_selection_was_scripted:
                        g = sop.createOutputNode("groupfindpath")
                        g.setParms({ "outgroup": "__selection__", "group": group, "grouptype": 1, "pathcontroltype": 1, "operation": 1, "avoidprevious": False, "edgestyle": 1 })
                        VIEWER.setCurrentGeometrySelection(hou.geometryType.Edges, (sop,), (g.geometry().selection(),))
                        g.destroy()
                    
                    else:
                        g = sop.createOutputNode("groupfindpath")
                        g.setParms({ "outgroup": "__selection__", "group": group, "grouptype": 1, "pathcontroltype": 1, "operation": 1, "avoidprevious": False, "edgestyle": 1 })
                        self.set_sop_selection(sop, g.geometry().selection(), grouptype)
                        g.destroy()
                    
                elif grouptype == hou.geometryType.Primitives:
                    prims = self.last_selection.prims(self.last_selection_geo)
                    group = " ".join( [str(prim.number()) for prim in prims] )

                    g = sop.createOutputNode("groupfindpath")
                    g.setParms({ "outgroup": "__selection__", "group": group, "grouptype": 3, "pathcontroltype": 2, "operation": 1, "avoidprevious": False })
                    self.set_sop_selection(sop, g.geometry().selection(), grouptype)
                    g.destroy()

                elif grouptype == hou.geometryType.Points:
                    if self.last_selection.numSelected() == 1:
                        prompt("More then one point must be selected")
                    else:
                        points = self.last_selection.points(self.last_selection_geo)
                        group = " ".join( [str(point.number()) for point in points] )
                        g = sop.createOutputNode("groupfindpath")
                        g.setParms({ "outgroup": "__selection__", "group": group, "grouptype": 2, "pathcontroltype": 2, "operation": 1, "avoidprevious": False })
                        self.set_sop_selection(sop, g.geometry().selection(), grouptype)
                        g.destroy()

                else:
                    prompt(PROMPT_POINTS_EDGES_POLYGONS)
            
        elif name == "convert_to_edge_rings":
            sop, group, grouptype, empty = self.selection()
            if grouptype == hou.geometryType.Edges:
                with hou.undos.group("Modeler: Convert Selection To Edge Rings"):
                    g = sop.createOutputNode("modeler::edge_rings")
                    g.parm("group").set(group)
                    self.set_sop_selection(sop, g.geometry().selection(), grouptype)
                    g.destroy()
            else:
                prompt(PROMPT_EDGES)
        
        elif name == "convert_to_boundary":
            sop, group, grouptype, empty = self.selection()
            if grouptype is not None:
                with hou.undos.group("Modeler: Convert Selection To Boundary Edges"):
                    if grouptype == hou.geometryType.Edges:
                        grouptype = 2
                        
                    elif grouptype == hou.geometryType.Primitives:
                        grouptype = 0
                        
                    else:
                        grouptype = 1
                    
                    g = sop.createOutputNode("groupfromattribboundary")
                    g.setParms({ "useattribute": False, "group": group, "grouptype": grouptype })
                    VIEWER.setPickGeometryType(hou.geometryType.Edges)
                    VIEWER.setCurrentGeometrySelection(hou.geometryType.Edges, (sop,), (g.geometry().selection(),))
                    g.destroy()
            else:
                prompt(PROMPT_POINTS_EDGES_POLYGONS)
        
        elif name == "lasso_frontface":
            VIEWER.setPickStyle(hou.pickStyle.Lasso)
            VIEWER.setPickingVisibleGeometry(True)
        
        elif name == "lasso_backface":
            VIEWER.setPickStyle(hou.pickStyle.Lasso)
            VIEWER.setPickingVisibleGeometry(False)
        
        elif name == "box_frontface":
            VIEWER.setPickStyle(hou.pickStyle.Box)
            VIEWER.setPickingVisibleGeometry(True)
        
        elif name == "box_backface":
            VIEWER.setPickStyle(hou.pickStyle.Box)
            VIEWER.setPickingVisibleGeometry(False)

        elif name == "expand_selection_by_normal":
            sop, group, grouptype, empty = self.selection()
            if grouptype is not None:
                with hou.undos.group("Modeler: Expand Selection By Normal"):
                    sop1 = sop.createOutputNode("groupexpand")
                    
                    if grouptype == hou.geometryType.Primitives:
                        sop1.setParms({ "outputgroup": "", "group": group, "grouptype": 4, "floodfill": True, "bynormal": True, "normalangle": 15.0 })
                    
                    elif grouptype == hou.geometryType.Points:
                        sop1.setParms({ "outputgroup": "", "group": group, "grouptype": 3, "floodfill": True, "bynormal": True, "normalangle": 15.0 })

                    else:
                        sop1.setParms({ "outputgroup": "", "group": group, "grouptype": 2, "floodfill": True, "bynormal": True, "normalangle": 15.0 })

                    sel = sop1.geometry().selection()
                    if not self.last_selection_was_scripted:
                        VIEWER.setCurrentState("select")
                    
                    VIEWER.setCurrentGeometrySelection(self.last_selection.selectionType(), (sop,), (sel,))
                    sop1.destroy()
        
        elif name == "select_hard_edges":
            sop, group, grouptype, empty = self.selection()
            if grouptype == hou.geometryType.Primitives:
                with hou.undos.group("Modeler: Select Hard Edges"):
                    sop = sop.createOutputNode("modeler::group_hard_edges")
                    sop.parm("group").set(group)
                    self.activate_sop_with_state(sop)
            else:
                prompt(PROMPT_POLYGONS)

        elif name == "extrude":
            sop, group, grouptype, empty = self.selection()
            if grouptype is not None:
                with hou.undos.group("Modeler: Extrude"):
                    # POINTS
                    if grouptype == hou.geometryType.Points:
                        sop = sop.createOutputNode("modeler::extrude_points")
                        sop.parm("group").set(group)
                        sop.setHighlightFlag(True)
                        self.activate_sop_with_state(sop)

                    # FACES OR EDGES
                    else:
                        sop = sop.createOutputNode("polyextrude::2.0")
                        sop.setParms({ "group": group })
                        self.activate_sop_with_state(sop)
            else:
                prompt(PROMPT_POINTS_EDGES_POLYGONS)

        elif name == "extend":
            sop, group, grouptype, empty = self.selection()
            if grouptype in (hou.geometryType.Primitives, hou.geometryType.Edges):
                with hou.undos.group("Modeler: Extend"):
                    sop = sop.createOutputNode("polyextrude::2.0")
                    sop.setParms({ "group": group, "xformfront": True, "xformspace": 1 })
                    
                    with hou.RedrawBlock() as rb:
                        sop.setDisplayFlag(True)
                        sop.setHighlightFlag(True)
                        sop.setRenderFlag(True)
                        sop.setCurrent(True, True)
                    
                    hou.hscript('omparm "Polygon Extruder 2" extrude2 {} "rotate(1)"'.format(sop.path()))
                    VIEWER.enterCurrentNodeState()
            else:
                prompt(PROMPT_EDGES_OR_POLYGONS)
        
        elif name == "thickness":
            sop, group, grouptype, empty = self.selection()
            if grouptype == hou.geometryType.Primitives:
                with hou.undos.group("Modeler: Thickness"):
                    sop = sop.createOutputNode("modeler::thickness")
                    sop.parm("group").set(group)
                    self.activate_sop_with_state(sop)
            else:
                hou.modeler.ui.prompt(hou.modeler.ui.PROMPT_POLYGONS)
        
        elif name == "bevel":
            sop, group, grouptype, empty = self.selection()
            if grouptype is not None:
                if grouptype == hou.geometryType.Primitives:
                    grouptype = 0
                elif grouptype == hou.geometryType.Points:
                    grouptype = 1
                else:
                    grouptype = 2
                    VIEWER.setPickGeometryType(hou.geometryType.Primitives)

                with hou.undos.group("Modeler: Bevel"):
                    sop = sop.createOutputNode("polybevel::3.0")
                    sop.setParms({ "group": group, "grouptype": grouptype, "filletshape": 4, "divisions": 1 })
                    self.activate_sop_with_state(sop)
            else:
                prompt(PROMPT_POINTS_EDGES_POLYGONS)

        elif name == "bevel_pro":
            sop, group, grouptype, empty = self.selection()
            if grouptype == hou.geometryType.Edges:
                with hou.undos.group("Modeler: Bevel Pro"):
                    sop = sop.createOutputNode("modeler::bevel_pro")
                    sop.parm("group").set(group)
                    self.activate_sop_with_state(sop)
            else:
                prompt(PROMPT_EDGES)

        elif name == "shift":
            sop, group, grouptype, empty = self.selection()
            if grouptype == hou.geometryType.Primitives:
                t = self.last_selection_geo.primBoundingBox(group).center()
                with hou.undos.group("Modeler: Shift"):
                    sop = sop.createOutputNode("modeler::shift")
                    sop.setParms({ "group": group, "pivotx": t[0], "pivoty": t[1], "pivotz": t[2]})
                    self.activate_sop_with_state(sop)
            else:
                prompt(PROMPT_POLYGONS)        

        elif name == "duplicate":
            pwd = VIEWER.pwd()
            state = VIEWER.currentState()

            if state == "modeler::boolean":
                cur_node = VIEWER.currentNode()
                cur_node.parm("repeat").pressButton()

            elif pwd.childTypeCategory() == hou.objNodeTypeCategory():
                with hou.undos.group("Modeler: Duplicate"):
                    nodes = [node for node in (hou.selectedNodes() or pwd.children()) if node.type().name()  == "geo"]
                    if nodes:
                        new_nodes = hou.copyNodesTo(nodes, pwd)
                        for node in new_nodes:
                            node.moveToGoodPosition()
                        if state != "select":
                            VIEWER.enterTranslateToolState()

            else:
                sop, group, grouptype, empty = self.selection()
                if grouptype is not None:
                    with hou.undos.group("Modeler: Duplicate"):
                        if grouptype == hou.geometryType.Primitives:
                            sop = sop.createOutputNode("copyxform")
                            p = self.last_selection_geo.primBoundingBox(group).center()
                            sop.setParms({ "sourcegroup": group, "sourcegrouptype": 1, "px": p[0], "py": p[1], "pz": p[2] })
                            self.activate_sop_with_state(sop)                        
                                
                        elif grouptype == hou.geometryType.Edges:
                            d = sop.createOutputNode("dissolve")
                            d.setParms({ "group": group, "invertsel": 1, "reminlinepts": False, "bridge": 1, "boundarycurves": True })
                            p = d.createOutputNode("polypath")
                            g = p.createOutputNode("groupcreate")
                            g.parm("groupname").set("__selection__")
                            gd = sop.createOutputNode("groupdelete")
                            gd.parm("group1").set("__selection__")
                            m = g.createOutputNode("merge")
                            m.setNextInput(gd)
                            x = m.createOutputNode("xform", "transform_open_faces1")
                            x.setParms({ "group": "__selection__", "grouptype": 4 })
                            
                            with hou.RedrawBlock() as rb:
                                x.setDisplayFlag(True)
                                x.setRenderFlag(True)
                                x.setHighlightFlag(True)
                                sel = x.geometry().selection()
                                x.parmTuple("p").set(hou.modeler.ui.modeler.sop_selection_center(x, sel))
                                s = pwd.collapseIntoSubnet((d, p, g, gd, m), "duplicate_edges1")
                                s.moveToGoodPosition()
                                x.moveToGoodPosition()
                                x.setCurrent(True, True)

                            VIEWER.enterCurrentNodeState()

        elif name == "bridge":
            if VIEWER.currentState() == "topobuild":
                self.run_stock_hotkey_action("h.pane.gview.state.sop.topobuild.bridge")
            else:
                sop, group, grouptype, empty = self.selection()
                if grouptype in (hou.geometryType.Edges, hou.geometryType.Primitives) and not empty:
                    if grouptype == hou.geometryType.Edges:
                        edges = self.edges(self.last_selection_geo)
                        half = int(len(edges) / 2)
                        src = " ".join( [edge.edgeId() for edge in edges[0:half]] )
                        dst = " ".join( [edge.edgeId() for edge in edges[half:]] )
                    else:
                        prims = self.last_selection.prims(self.last_selection_geo)
                        half = int(len(prims) / 2)
                        src = " ".join([str(prim.number()) for prim in prims[0:half]])
                        dst = " ".join([str(prim.number()) for prim in prims[half:]])
                    
                    with hou.undos.group("Modeler: Bridge"):
                        sop = sop.createOutputNode("polybridge")
                        sop.setParms({ "srcgroup": src, "dstgroup" : dst })
                        self.activate_sop_with_state(sop)

                else:
                    prompt(PROMPT_EDGES_OR_POLYGONS)

        elif name == "bridge_connected":
            if VIEWER.currentState() == "topobuild":
                self.run_stock_hotkey_action("h.pane.gview.state.sop.topobuild.bridgeconnected")
            else:
                sop, group, grouptype, empty = self.selection()
                if grouptype == hou.geometryType.Edges and not empty:
                    with hou.undos.group("Modeler: Bridge Connected"):
                        sop = sop.createOutputNode("modeler::bridge_connected")
                        sop.parm("group").set(group)
                        om = self.topo_get_ref(sop.parent())
                        if om is not None:
                            sop.setInput(1, om)
                        self.activate_sop_with_select_state(sop)
                else:
                    prompt(PROMPT_EDGES)

        elif name == "freeze_transforms":
            self.freeze()

        elif name == "center_pivot":
            VIEWER.runShelfTool("object_centerpivot")

        elif name == "viewport_subd":
            sop = VIEWER.currentNode()
            if sop.type().category() != hou.sopNodeTypeCategory():
                sop = self.get_sop(set_current=False)

            if sop is not None:
                pwd = self.ancestor_object(sop)
                if pwd.evalParm("viewportlod") == 5:
                    pwd.parm("viewportlod").set(0)
                else:
                    pwd.parm("viewportlod").set(5)

        elif name == "show_all":
            hou.hscript("vieweroption -a 1 %s.%s.world" % (hou.ui.curDesktop().name(), VIEWER.name()))

        elif name == "ghost_others":
            hou.hscript("vieweroption -a 2 %s.%s.world" % (hou.ui.curDesktop().name(), VIEWER.name()))

        elif name == "hide_others":
            hou.hscript("vieweroption -a 0 %s.%s.world" % (hou.ui.curDesktop().name(), VIEWER.name()))
        
        elif name == "isolate_object":
            mask = VIEWER.curViewport().settings().visibleObjects()

            # OFF
            if len(mask) > 1:
                hou.hscript('viewdisplay -G "*"  *')

                for obj in hou.node("/obj").children():
                    if obj.isDisplayFlagSet():
                        obj.setDisplayFlag(False)
                        obj.setDisplayFlag(True)

                prompt("Isolation Off")

            # ON
            else:
                sop, objects, grouptype, empty = self.selection(activate_one_object=False)

                success = True

                if sop is None and objects is None:
                    prompt("Geometry objects must be selected.")
                    success = False

                elif sop is not None:
                    objects = [ self.ancestor_object(sop) ]

                if success:
                    mask = ""

                    # ADD BACKDROP NODES
                    for b in hou.nodeType(hou.objNodeTypeCategory(), "modeler::backdrop").instances():
                        mask += (b.path() + " ")

                    # ADD OBJECTS TO MASK
                    for obj in objects:
                        mask += ( obj.path() + " " )

                    hou.hscript('viewdisplay -G "%s"  *' % mask)

                    prompt("Isolated: " + mask)

        elif name == "isolate_polygons":
            sop, group, grouptype, empty = self.selection()

            # ON
            if grouptype == hou.geometryType.Primitives and not empty:
                sop = sop.createOutputNode("visibility")
                sop.setParms({ "group": group, "action": 0, "applyto": 1 })
                self.activate_sop_with_select_state(sop)
                self.clear_sop_selection()

            # OFF   
            elif grouptype is not None and empty:
                g = self.last_selection_geo.findPrimGroup("_3d_hidden_primitives")

                if g is None:
                    prompt("No hidden polygons!")
                else:
                    sop = sop.createOutputNode("visibility")
                    sop.parm("action").set(1)
                    self.activate_sop_with_select_state(sop)    
            else:
                prompt("Select isolate polygons or apply the tool to empty selection to unhide hidden geometry")

        elif name == "delete_node":
            sel_nodes = hou.selectedNodes()

            if len(sel_nodes) > 1:
                for node in sel_nodes:
                    node.destroy()

            elif len(sel_nodes) == 1 and sel_nodes[0].type().category() == hou.sopNodeTypeCategory() and not sel_nodes[0].isDisplayFlagSet():
                sel_nodes[0].destroy()
                home_selected()

            else:
                pwd = VIEWER.pwd()
                child_cat = pwd.childTypeCategory()
                if child_cat == hou.objNodeTypeCategory():
                    nodes = [node for node in sel_nodes if node.type().name() == "geo"]
                    if nodes:
                        pwd.deleteItems(nodes)
                        VIEWER.setCurrentState("select")

                elif child_cat == hou.sopNodeTypeCategory():
                    sop = pwd.displayNode()
                    if sop is not None:
                        cont = True
                        inputs = sop.inputs()
                        
                        if inputs:
                            if sop.type().name() == "stroke" and len(inputs) == 2:
                                sop1 = inputs[1]
                            else:
                                sop1 = inputs[0] or inputs[-1]

                            outputs = sop.outputs()
                            
                            with hou.RedrawBlock() as rb:                
                                sop1.setDisplayFlag(True)
                                sop1.setRenderFlag(True)
                                sop1.setSelected(True, True)
                                sop1.setCurrent(True)
                                VIEWER.enterViewState()

                            VIEWER.enterCurrentNodeState()

                            for output in outputs:
                                output.destroy()

                        elif len(pwd.children()) == 1:
                            result = hou.ui.displayMessage("Latest node. How to delete?", buttons=("Delete Parent", "Delete Node" , "Abort"), close_choice=2, default_choice=0)
                            if result == 0:
                                pwd.destroy()
                                cont = False
                            
                            elif result == 2:
                                cont = False

                        if cont:
                            try:
                                sop.destroy()
                            
                            except hou.ObjectWasDeleted:
                                pass

                home_selected()

        elif name == "sym_full":
            symmetry.resym_full()

        elif name == "sym_half":
            symmetry.resym_half()

        elif name == "sym_subd_instance":
            symmetry.subd_instance()

        elif name == "sym_instance":
            symmetry.toggle_instance()

        elif name == "sym_origin":
            symmetry.pick_origin()

        elif name == "sym_radial":
            symmetry.radial()

        elif name == "grow":
            self.grow_selection()

        elif name == "shrink":
            self.shrink_selection()

        elif name == "walk_selection_left":
            self.walk_selection(hou.Vector3(-1, 0, 0))

        elif name == "walk_selection_right":
            self.walk_selection(hou.Vector3(1, 0, 0))

        elif name == "walk_selection_up":
            self.walk_selection(hou.Vector3(0, 1, 0))

        elif name == "walk_selection_down":
            self.walk_selection(hou.Vector3(0, -1, 0))

        elif name == "flatten_left":
            self.flatten_left()

        elif name == "flatten_right":
            self.flatten_right()

        elif name == "flatten_up":
            self.flatten_up()

        elif name == "flatten_down":
            self.flatten_down()

        elif name == "flatten_by_normal":
            self.flatten_by_face_normal()

        elif name == "flatten_auto":
            self.flatten_auto()

        elif name == "align":
            sop, group, grouptype, empty = self.selection()
            if grouptype is not None:
                if grouptype == hou.geometryType.Primitives:
                    grouptype = 2
                elif grouptype == hou.geometryType.Points:
                    grouptype = 1
                else:
                    grouptype = 0

                with hou.undos.group("Modeler: Align"):
                    sop = sop.createOutputNode("modeler::align")
                    sop.setParms({ "group": group, "grouptype": grouptype })   
                    sop.hdaModule().pivot_from_group(sop)
                    sop.parmTuple("b").set(sop.evalParmTuple("a"))
                    self.activate_sop_with_select_state(sop)
            else:
                prompt(PROMPT_POINTS_EDGES_POLYGONS)

        elif name == "set_flow":
            sop, group, grouptype, empty = self.selection()
            if grouptype == hou.geometryType.Edges:
                with hou.undos.group("Modeler: Set Flow"):
                    sop = sop.createOutputNode("modeler::set_flow")
                    sop.parm("group").set(group)
                    self.activate_sop_with_select_state(sop)
            else:
                prompt(PROMPT_EDGES)

        elif name == "mountain":
            self.mountain()
        
        elif name == "deform":
            self.bend()

        elif name == "falloff_xform":
            self.falloff_xform()
        
        elif name == "lattice":
            self.lattice()

        elif name == "display_toggle_templates":
            guide_enabled = not VIEWER.curViewport().settings().guideEnabled(hou.viewportGuide.TemplateGeometry)
            for viewport in VIEWER.viewports():
                viewport.settings().enableGuide(hou.viewportGuide.TemplateGeometry, guide_enabled)
        
        elif name == "display_templates_shade_mode":
            shade_mode = VIEWER.curViewport().settings().displaySet(hou.displaySetType.TemplateModel).shadedMode()
            
            if shade_mode == hou.glShadingType.Smooth:
                shade_mode = hou.glShadingType.SmoothWire
            
            elif shade_mode == hou.glShadingType.SmoothWire:
                shade_mode = hou.glShadingType.Wire
            
            else:
                shade_mode = hou.glShadingType.Smooth
            
            for viewport in VIEWER.viewports():
                viewport.settings().displaySet(hou.displaySetType.TemplateModel).setShadedMode(shade_mode)

        elif name == "display_ghost_templates":
            ghost = not VIEWER.curViewport().settings().displaySet(hou.displaySetType.TemplateModel).isUsingGhostedLook()
            for viewport in VIEWER.viewports():
                viewport.settings().displaySet(hou.displaySetType.TemplateModel).useGhostedLook(ghost)

        elif name == "display_xray_display":
            xray = not VIEWER.curViewport().settings().displaySet(hou.displaySetType.DisplayModel).isUsingXRay()
            for viewport in VIEWER.viewports():
                viewport.settings().displaySet(hou.displaySetType.DisplayModel).useXRay(xray)
        
        elif name == "boolean_union":
            self.boolean(0)

        elif name == "boolean_intersect":
            self.boolean(1)

        elif name == "boolean_subtract":
            self.boolean(2)

        elif name == "separate":
            sop, group, grouptype, empty = self.selection()
            if sop is not None:
                existing_sep = None
                for ancestor in sop.inputAncestors():
                    if ancestor.type().name() == "split" and len(ancestor.inputs()) == 1:
                        existing_sep = ancestor
                        break

                pwd = self.ancestor_object(sop)

                with hou.undos.group("Modeler: Separate"):
                    if existing_sep is not None and len(existing_sep.outputs()) == 2 and existing_sep.outputs()[-1].type().name() == "null" and not existing_sep.outputs()[-1].outputs():
                        sop = sop.createOutputNode("boolean::2.0")
                        sop.parm("booleanop").set(0)
                        sop.setInput(1, existing_sep.outputs()[-1])
                        self.activate_sop_with_select_state(sop)
                        s = pwd.collapseIntoSubnet((sop,), "unseparate1")
                        s.moveToGoodPosition()

                    elif group is not None and grouptype == hou.geometryType.Primitives: 
                        new_sep = sop.createOutputNode("split", "separate1")
                        new_sep.parm("group").set(group)
                        null1 = new_sep.createOutputNode("null", "separated1")
                        null1.setPosition(new_sep.position() + hou.Vector2(-1.3, -1.3))
                        null2 = pwd.createNode("null", "rest1")
                        null2.setPosition(new_sep.position() + hou.Vector2(1.3, -1.3))
                        null2.setInput(0, new_sep, 1)
                        self.activate_sop_with_select_state(null1)

                    else:
                        prompt(PROMPT_POLYGONS)
                    
            else:
                prompt(PROMPT_ONE_GEO)

        elif name == "extract":
            nodes = [node for node in hou.selectedNodes() if node.type().name()=="geo"]
            if nodes:
                nodes_to_layout = []
                pwd_parent = nodes[0].parent()
                result = hou.ui.displayMessage("How to extract objects?", buttons=("Extract To Objects", "Extract and group with Null node", "Cancel"), default_choice=0, close_choice=2, title="Extract All Polygonal Shells")
                if result < 2:
                    parent_with_null = result == 1
                    with hou.undos.group("Modeler: Extract"):
                        with hou.RedrawBlock() as rb:
                            for pwd in nodes:
                                sop = pwd.displayNode()
                                if sop is not None:
                                    if parent_with_null:
                                        null = pwd_parent.createNode("null")
                                    
                                    name = pwd.name()
                                    xform = pwd.worldTransform()
                                    global_center = sop.geometry().boundingBox().center() * xform
                                    mat_path = pwd.evalParm("shop_materialpath")
                                    con = sop.createOutputNode("connectivity")
                                    con.parm("connecttype").set(1)
                                    blast = con.createOutputNode("blast")
                                    blast.parm("negate").set(True)
                                    prefix = "@class=="
                                    i = 0
                                    while True:
                                        blast.parm("group").set(prefix + str(i))
                                        geo = hou.Geometry(blast.geometry())
                                        geo.transform(xform)
                                        prim_count = geo.intrinsicValue("primitivecount")
                                        if prim_count == 0:
                                            break
                                        new_geo = pwd_parent.createNode("geo")
                                        if parent_with_null:
                                            new_geo.setInput(0, null)
                                        
                                        center = geo.boundingBox().center()
                                        new_geo.setParms({ "shop_materialpath": mat_path, "px": center[0], "py": center[1], "pz": center[2] })
                                        stash = new_geo.createNode("stash")
                                        stash.parm("stash").set(geo)
                                        i += 1
                                        nodes_to_layout.append(new_geo)
                                    
                                    blast.destroy()
                                    con.destroy()
                                    pwd.destroy()

                                    if parent_with_null:
                                        null.parm("childcomp").set(True)
                                        null.parmTuple("t").set(global_center)
                                        null.parm("childcomp").set(False)
                                        nodes_to_layout.append(null)
                                        null.setName(name)
                                
                            # LAYOUT
                            VIEWER.pwd().layoutChildren(nodes_to_layout)
                            frame_items(nodes_to_layout)
                            VIEWER.setCurrentState("select")

            else:
                sop, group, grouptype, empty = self.selection()
                if grouptype == hou.geometryType.Primitives and not empty:
                    with hou.undos.group("Modeler: Extract"):
                        b = sop.createOutputNode("blast")
                        b.parm("group").set(group)
                        b1 = sop.createOutputNode("blast")
                        b1.setParms({ "group": group, "negate": True })
                        geo = hou.Geometry(b1.geometry())
                        pwd = self.ancestor_object(sop)
                        geo.transform(pwd.localTransform())
                        s = b1.createOutputNode("stash")
                        s.parm("stash").set(geo)
                        obj = pwd.parent().createNode("geo", "extracted_prims1")
                        hou.moveNodesTo((s,), obj)
                        self.activate_sop_with_select_state(b)
                        b1.destroy()
                        obj.moveToGoodPosition()

        elif name == "combine":
            child_cat = VIEWER.pwd().childTypeCategory()

            with hou.undos.group("Modeler: Combine"):
                if child_cat == hou.objNodeTypeCategory():
                    objs = []
                    mat_paths = []
                    for node in hou.selectedNodes():
                        if node.type().name() == "geo":
                            objs.append(node)
                            mat_path = node.evalParm("shop_materialpath")
                            mat_paths.append(mat_path)

                    if len(objs) > 1:
                        obj = objs.pop()
                        obj.combine(objs)
                        display = obj.displayNode()
                        mat_paths.pop()
                        for i, mat_path in enumerate(mat_paths):
                            if mat_path:
                                input_sop = display.inputs()[i + 1]
                                m = input_sop.createOutputNode("material")
                                m.parm("shop_materialpath1").set(mat_path)
                                display.setInput(i + 1, m)

                        VIEWER.setCurrentState("select")
                        home_selected()

                elif child_cat == hou.sopNodeTypeCategory():
                    sop, group, grouptype, empty = self.selection()
                    if sop is not None:
                        next_pwd, next_sop = self.get_object("Select object to combine")
                        pwd = self.ancestor_object(sop)
                        if next_pwd is not None and next_pwd != pwd:
                            mat_path = pwd.evalParm("shop_materialpath")
                            next_pwd.combine([pwd])

                            if mat_path:
                                display = next_pwd.displayNode()
                                i = display.inputs()[1]
                                m = i.createOutputNode("material")
                                m.parm("shop_materialpath1").set(mat_path)
                                display.setInput(1, m)

                            VIEWER.setCurrentState("select")
                            home_selected()

        elif name == "vdb_remesh":
            sop, group, grouptype, empty = self.selection()
            if sop is not None:
                with hou.undos.group("Modeler: VDB Remesh"):
                    self.activate_sop_with_select_state( sop.createOutputNode("modeler::vdb_remesh") )

        elif name == "fix_curves":
            sop, group, grouptype, empty = self.selection()
            if grouptype == hou.geometryType.Primitives:
                with hou.undos.group("Modeler: Fix Curves"):
                    sop = sop.createOutputNode("modeler::fix_curves")
                    sop.parm("group").set(group)
                    self.activate_sop_with_state(sop)
            else:
                prompt(PROMPT_POLYGONS)

        elif name == "hose":
            sop, group, grouptype, empty = self.selection()
            if grouptype is not None and grouptype != hou.geometryType.Points:
                with hou.undos.group("Modeler: Hose"):
                    sop = sop.createOutputNode("modeler::hose")
                    sop.parm("group").set(group)
                    self.activate_sop_with_state(sop)
            else:
                prompt(PROMPT_EDGES_OR_POLYGONS)

        elif name == "array":
            sop, group, grouptype, empty = self.selection()
            if grouptype == hou.geometryType.Primitives:
                with hou.undos.group("Modeler: Array"):
                    array = sop.createOutputNode("modeler::array")
                    cplane = VIEWER.constructionPlane()
                    if cplane.isVisible():
                        xform = hou.hmath.buildRotate(90.0, 0.0, 0.0) * cplane.transform() * self.ancestor_object(sop).worldTransform().inverted()
                        t = xform.extractTranslates()
                        r = xform.extractRotates()
                        array.parmTuple("t").set(t)
                        array.parmTuple("r").set(r)
                        cplane.setIsVisible(False)
                    else:
                        try:
                            gs = VIEWER.selectGeometry("Select faces for array orientation or press Escape to use default values.", \
                                                                      geometry_types=(hou.geometryType.Primitives,), use_existing_selection=False, \
                                                                      quick_select=False, consume_selections=False, allow_other_sops=True )
                            
                            rad = gs.boundingBox().sizevec()
                            rad = (rad[0] + rad[1] + rad[2]) / 3.0
                            sel1 = gs.selections()[0]
                            sop1 = gs.nodes()[0]
                            normal, center = self.get_selection_normal_and_center(sop1, sel1, sop1.geometry())
                            xform = self.ancestor_object(sop1).worldTransform()
                            normal_global = normal * xform.inverted().transposed()
                            center_global = center * xform
                            xform = hou.Vector3(0.0, 1.0, 0.0).matrixToRotateTo(normal_global) * hou.hmath.buildTranslate(center_global)
                            xform *= self.ancestor_object(sop).worldTransform().inverted()
                            t = xform.extractTranslates()
                            r = xform.extractRotates()
                            array.parmTuple("t").set(t)
                            array.parmTuple("r").set(r)
                            array.parm("rad").set(rad)

                        except:
                            VIEWER.setPickGeometryType(grouptype)

                    array.parm("group").set(group)
                    self.activate_sop_with_state(array)

        elif name == "mirror":
            sop, group, grouptype, empty = self.selection()
            if grouptype == hou.geometryType.Primitives:
                result = hou.ui.displayMessage("Get origin and direction by:", buttons=("Edge", "2 points", "H", "V", "X", "Y", "Z", "Cancel"), default_choice=7, close_choice=7, title="Mirror")
                
                xform = self.ancestor_object(sop).worldTransform()
                
                origin = None
                direction = None

                # EDGE
                if result == 0:
                    edges = self.pick_component(hou.geometryType.Edges, "Select edge")
                    if edges:
                        edge = edges[0]
                        pt1, pt2 = edge.points()
                        pos1 = pt1.position()
                        pos2 = pt2.position()
                        origin = (pos1 + pos2) / 2.0
                        direction = (pos1- pos2).normalized()

                # 2 POINTS
                elif result == 1:
                    points = self.pick_component(hou.geometryType.Points, "Select 2 points", quick=False)
                    if len(points) == 2:
                        pos1 = points[0].position()
                        pos2 = points[1].position()
                        origin = (pos1 + pos2) / 2.0
                        direction = (pos1- pos2).normalized()

                # H
                elif result == 2:
                    direction = get_hvd(VIEWER, True)[0]
                    xform = hou.modeler.ui.modeler.ancestor_object(sop).worldTransform()
                    direction *= xform.transposed()
                    origin = hou.Vector3() * xform.inverted()

                # V
                elif result == 3:
                    direction = get_hvd(VIEWER, True)[1]
                    direction *= xform.transposed()
                    origin = hou.Vector3() * xform.inverted()

                # X
                elif result == 4:
                    origin = (0, 0, 0)
                    direction = hou.Vector3(1, 0, 0)

                # Y
                elif result == 5:
                    origin = (0, 0, 0)
                    direction = hou.Vector3(0, 1, 0)

                # Z
                elif result == 6:
                    origin = (0, 0, 0)
                    direction = hou.Vector3(0, 0, 1)
                
                if direction is not None:
                    direction = self.fix_dir_by_viewport(direction, xform)
                    
                    with hou.undos.group("Modeler: Mirror"):
                        sop = sop.createOutputNode("modeler::mirror")
                        sop.parm("group").set(group)
                        sop.parmTuple("origin").set(origin)
                        sop.parmTuple("dir").set(direction)
                        self.activate_sop_with_state(sop)

            else:
                prompt(PROMPT_POLYGONS)

        elif name == "copy_polygons":
            sop, group, grouptype, empty = self.selection(activate_one_object=False)

            if sop is None and group is not None:
                prompt("Selected nodes copied to clipboard")
                hou.copyNodesToClipboard(group)

            elif grouptype == hou.geometryType.Primitives:
                geo = self.last_selection_geo.freeze()
                bv = hou.sopNodeTypeCategory().nodeVerb("blast")
                bv.setParms({"group": group, "negate": True})   
                hou.modeler.ui.modeler.COPIED_GEO = hou.Geometry()
                bv.execute(hou.modeler.ui.modeler.COPIED_GEO, (geo,))
                hou.modeler.ui.modeler.COPIED_GEO.transform(self.ancestor_object(sop).worldTransform())
                prompt("{} polygons was copied to clipboard".format(hou.modeler.ui.modeler.COPIED_GEO.intrinsicValue("primitivecount")))

            else:
                prompt("Objects or polygons must be selected")


        elif name == "cut_polygons":
            sop, group, grouptype, empty = self.selection(activate_one_object=False)

            if sop is None and group is not None:
                prompt("Selected nodes copied to clipboard")
                hou.copyNodesToClipboard(group)
                pwd.deleteItems(group)

            elif grouptype == hou.geometryType.Primitives:
                geo = self.last_selection_geo.freeze()
                bv = hou.sopNodeTypeCategory().nodeVerb("blast")
                bv.setParms({ "group": group, "negate": True })
                hou.modeler.ui.modeler.COPIED_GEO = hou.Geometry()
                bv.execute(hou.modeler.ui.modeler.COPIED_GEO, (geo,))
                hou.modeler.ui.modeler.COPIED_GEO.transform(self.ancestor_object(sop).worldTransform())
                
                with hou.undos.group("Modeler: Cut Polygons"):
                    sop = sop.createOutputNode("blast", "cut_faces1")
                    sop.parm("group").set(group)
                    self.activate_sop_with_select_state(sop)
                    prompt("{} polygons was cutted to clipboard".format(hou.modeler.ui.modeler.COPIED_GEO.intrinsicValue("primitivecount")))

            else:
                prompt("Objects or polygons must be selected")

        elif name == "paste_polygons":
            sop, group, grouptype, empty = self.selection(activate_one_object=False)

            if sop is not None:
                if hou.modeler.ui.modeler.COPIED_GEO is None:
                    prompt("There are no polygons in clipboard")
                else:
                    xform = self.ancestor_object(sop).worldTransform().inverted()
                    geo = hou.Geometry(hou.modeler.ui.modeler.COPIED_GEO)
                    geo.transform(xform)

                    with hou.undos.group("Modeler: Paste Polygons"):
                        merge = sop.createOutputNode("merge")
                        stash = merge.createInputNode(1, "stash", "pasted_geo1")
                        stash.parm("stash").set(geo)
                        geo = merge.geometry()
                        b = geo.intrinsicValue("primitivecount") - 1
                        a = b - hou.modeler.ui.modeler.COPIED_GEO.intrinsicValue("primitivecount") + 1
                        sel = hou.Selection(geo, hou.geometryType.Primitives, "{}-{}".format(a, b))
                        self.activate_sop_with_select_state(merge)
                        VIEWER.setPickGeometryType(hou.geometryType.Primitives)

                        if sel is not None:
                            VIEWER.setCurrentGeometrySelection(hou.geometryType.Primitives, (merge,), (sel,))

                        prompt("{} polygons pasted from clipboard".format(hou.modeler.ui.modeler.COPIED_GEO.intrinsicValue("primitivecount")))

            else:
                pwd = hou.modeler.ui.VIEWER.pwd()
                if pwd.childTypeCategory() == hou.objNodeTypeCategory():
                    pre_nodes = hou.selectedNodes()
                    hou.pasteNodesFromClipboard( pwd )
                    post_nodes = hou.selectedNodes()
                    
                    delta = list(set(post_nodes) - set(pre_nodes))
                    for node in delta:
                        node.moveToGoodPosition()
                        
                    hou.modeler.ui.frame_items(delta)

        elif name == "normals":
            sop, group, grouptype, empty = self.selection()
            if grouptype is not None:
                with hou.undos.group("Modeler: Normals"):
                    sop = sop.createOutputNode("normal")
                    sop.setParms({"method": 2, "cuspangle": 30})

                    if grouptype == hou.geometryType.Primitives:
                        sop.setParms({ "group": group, "grouptype": 4 })
                    elif grouptype == hou.geometryType.Edges:
                        sop.setParms({ "group": group, "grouptype": 2 })
                    else:
                        sop.setParms({ "group": group, "grouptype": 3 })

                    self.activate_sop_with_select_state(sop)
            else:
                prompt(PROMPT_POINTS_EDGES_POLYGONS)

        elif name == "subdivide":
            sop, group, grouptype, empty = self.selection()
            if grouptype == hou.geometryType.Primitives:
                with hou.undos.group("Modeler: Subdivide"):
                    sop = sop.createOutputNode("subdivide")        
                    sop.setParms({ "subdivide": group, "surroundpoly": 2, "vtxboundary": 1, "fvarlinear": 3 })
                    self.activate_sop_with_select_state(sop)
            else:
                prompt(PROMPT_POLYGONS)

        elif name == "fuse":
            sop, group, grouptype, empty = self.selection(empty_type=hou.geometryType.Points)
            if grouptype is not None:
                if grouptype != hou.geometryType.Points:
                    sel = self.last_selection.freeze()
                    sel.convert(self.last_selection_geo, hou.geometryType.Points)      
                    group = sel.selectionString(self.last_selection_geo, force_numeric=True)

                with hou.undos.group("Modeler: Fuse"):
                    sop = sop.createOutputNode("fuse::2.0")
                    sop.setParms({ "querygroup": group, "tol3d": 0.0001, "delunusedpoints": True })
                    pre_vtx_count = self.last_selection_geo.intrinsicValue("vertexcount")
                    pre_point_count = self.last_selection_geo.intrinsicValue("pointcount")
                    self.activate_sop_with_select_state(sop)
                
                geo = sop.geometry()
                post_vtx_count = geo.intrinsicValue("vertexcount")
                post_point_count = geo.intrinsicValue("pointcount")
                vtx_delta = pre_vtx_count - post_vtx_count
                point_delta = pre_point_count - post_point_count
                if vtx_delta + point_delta == 0:
                    prompt("Initially nothing was fused")
                else:
                    prompt("Initially fused %d points and %d vertices." % (point_delta, vtx_delta))

            else:
                prompt(PROMPT_POINTS_EDGES_POLYGONS)

        elif name == "fix_overlaps":
            sop, group, grouptype, empty = self.selection()
            if sop is not None:
                with hou.undos.group("Modeler: Fix Overlaps"):
                    sop = sop.createOutputNode("modeler::fix_overlaps")
                    self.activate_sop_with_select_state(sop)
            else:
                prompt(PROMPT_ONE_GEO)
        
        elif name == "clean_edges":
            sop, group, grouptype, empty = self.selection()
            if grouptype == hou.geometryType.Primitives:
                with hou.undos.group("Modeler: Clean Edges"):
                    sop = sop.createOutputNode("modeler::clean_edges")
                    sop.parm("group").set(group)
                    self.activate_sop_with_select_state(sop)
            else:
                prompt(PROMPT_POLYGONS)

        elif name == "fill":
            self.fill()

        elif name == "reduce":
            sop, group, grouptype, empty = self.selection()
            if grouptype == hou.geometryType.Primitives:
                with hou.undos.group("Modeler: Reduce"):
                    sop = sop.createOutputNode("polyreduce::2.0")        
                    sop.setParms({ "group": group, "percentage": 50.0, "preservequads": True })
                    self.activate_sop_with_select_state(sop)
            else:
                prompt(PROMPT_POLYGONS)

        elif name == "curve":
            VIEWER.runShelfTool("sop_curve::2.0")

        elif name == "edit_curve":
            VIEWER.runShelfTool("sop_curve::2.0_edit")

        elif name == "box":
            self.geo_qprimitive(0)
        
        elif name == "tube":
            self.geo_qprimitive(3)

        elif name == "sphere":
            self.geo_qprimitive(2)

        elif name == "grid":
            self.geo_qprimitive(1)

        elif name == "clear_materials":
            self.clear_materials()

        elif name == "select_material_node":
            self.select_material_node()

        elif name == "get_material":
            self.get_material()
        
        elif name == "sample_material_copy":
            self.sample_material_copy()
        
        elif name == "sample_material":
            self.sample_material()
        
        elif name == "assign_material":
            self.assign_material()

        elif name == "network_frame_all":
            ne = hou.ui.paneTabOfType(hou.paneTabType.NetworkEditor)
            nodegraphview.frameItems(ne, ne.pwd().children())

        elif name == "network_frame":
            hou.ui.paneTabOfType(hou.paneTabType.NetworkEditor).homeToSelection()

        elif name == "delete_attributes":
            sop = modeler.get_sop()
            if sop is not None:
                with hou.undos.group("Modeler: Delete Attributes"):
                    sop = sop.createOutputNode("attribdelete")
                    sop.setParms({ "ptdel": "*", "vtxdel": "*", "primdel": "*", "dtldel": "*" })
                    self.activate_sop_with_select_state(sop)

        elif name == "delete_groups":
            sop = modeler.get_sop()
            if sop is not None:
                with hou.undos.group("Modeler: Delete Groups"):
                    sop = sop.createOutputNode("groupdelete")
                    sop.parm("group1").set("*")
                    self.activate_sop_with_select_state(sop)

        elif name == "merge_nodes":
            pwd = VIEWER.pwd()
            sel_nodes = hou.selectedNodes()
            nodes = [node for node in (sel_nodes or pwd.children()) if node.type().name()=="geo"]
    
            # OBJ
            if nodes:
                with hou.undos.group("Modeler: Merge Nodes"):
                    parent = nodes[0].parent()
                    null = parent.createNode("null", "merged_objects1")
                    global_center = hou.Vector3()
                    for node in nodes:
                        sop = node.displayNode()
                        if sop is not None:
                            global_center += sop.geometry().boundingBox().center() * node.worldTransform()

                        node.setInput(0, null)

                    global_center /= len(nodes)
                    null.parm("childcomp").set(True)
                    null.parmTuple("t").set(global_center)
                    null.parm("childcomp").set(False)
                    null.setCurrent(True, True)
                    parent.layoutChildren( [null] + nodes )
                    
                    home_selected()

            # SOP
            elif len(sel_nodes) > 1 and sel_nodes[0].type().category() == hou.sopNodeTypeCategory():
                sop = sel_nodes[0]
                result = hou.ui.displayMessage("Select node type", buttons=("Merge", "Swith", "Abort"), close_choice=2, default_choice=0, title="SOP Type Name")
                if result < 2:
                    with hou.undos.group("Modeler: Merge Nodes"):
                        m = sop.createOutputNode("switch" if result else "merge")
                        for node in sel_nodes[1:]:
                            m.setNextInput(node)
                        
                        m.moveToGoodPosition()
                        self.activate_sop_with_select_state(m)         

                        home_selected()

        elif name == "stash_history":
            pwd = VIEWER.pwd()
            cat = pwd.childTypeCategory()

            # SOP
            if cat == hou.sopNodeTypeCategory():
                sel_nodes = pwd.selectedChildren()

                with hou.undos.group("Modeler: Stash History"):
                    if len(sel_nodes) > 1:
                        subnet = pwd.collapseIntoSubnet(sel_nodes)
                        display = pwd.displayNode()
                        geo = subnet.geometry().freeze()
                        stash = subnet.changeNodeType("stash")
                        stash.setName("raw_geometry1", unique_name=True)
                        stash.parm("stash").set(geo)
                        stash.setColor(hou.Color(1,0,0))
                        display = pwd.displayNode()
                        if display != stash:
                            display.setCurrent(True, True)
                    else:
                        display = pwd.displayNode()
                        if display is None:
                            return

                        elif len(sel_nodes) == 0:
                            sop = display

                        else:
                            display.setCurrent(True, True)
                            sop = sel_nodes[0]

                        geo = sop.geometry().freeze()
                        
                        if sop == display:
                            home = True
                            isolate_group = geo.findPrimGroup("_3d_hidden_primitives")
                            if isolate_group is not None:
                                result = hou.ui.displayMessage("The geometry contains hidden polygons. How to process them?", buttons=("Unhide", "Leave Hidden", "Destroy"), close_choice=0, default_choice=0, title="Stash Partially Hidden Geometry")
                                if result == 0:
                                    isolate_group.destroy()
                                
                                elif result == 2:
                                    sop = sop.createOutputNode("blast")
                                    sop.parm("group").set("_3d_hidden_primitives")
                                    geo = sop.geometry().freeze()
                                    geo.findPrimGroup("_3d_hidden_primitives").destroy()
                        else:
                            home = False
                        
                        is_in_subnet = pwd.type() == hou.nodeType(hou.sopNodeTypeCategory(), "subnet")

                        if is_in_subnet:
                            parent = pwd.parent()
                            stash = pwd.changeNodeType("stash")
                            VIEWER.setPwd(parent)
                        else:
                            input_ancestors = sop.inputAncestors()

                            stash = sop.changeNodeType("stash")
                            stash.setName("raw_geometry1", unique_name=True)

                            if input_ancestors:
                                pwd.deleteItems(input_ancestors, disable_safety_checks=True)
                            
                            pwd.displayNode().setCurrent(True, True)

                        stash.parm("stash").set(geo)
                        stash.setColor(hou.Color(1,0,0))

                        if home:
                            home_selected()
    
            # OBJ
            else:
                sops = []
                with hou.undos.group("Modeler: Stash History"):
                    for sel in hou.selectedNodes():
                        if sel.childTypeCategory() == hou.sopNodeTypeCategory():
                            display = sel.displayNode()
                            if display is not None:
                                geo = display.geometry().freeze()
                                sel.deleteItems(sel.children())
                                stash = sel.createNode("stash")
                                stash.setName("raw_geometry1")
                                stash.parm("stash").set(geo)
                                stash.setColor(hou.Color(1,0,0))

        # TOPO MODE
        elif name == "topo_toggle":
            topo_src = self.topo_get_src_object()

            # ON
            if topo_src is None:
                node, sop = self.get_object(prompt="Select high-poly model", return_to_current_node=False)
                if node is not None:
                    node.setUserData("__topo__", "")
                    
                    with hou.undos.disabler():
                        node.setSelectableInViewport(False)
                        node.setDisplayFlag(False)

                    self.widget.findChild(qtw.QToolButton, "topo_toggle").setChecked(True)
                    
                    for viewport in VIEWER.viewports():
                        viewport.settings().displaySet(hou.displaySetType.DisplayModel).useXRay(True)
                        viewport.settings().displaySet(hou.displaySetType.TemplateModel).setShadedMode(hou.glShadingType.Smooth)
                        viewport.settings().displaySet(hou.displaySetType.TemplateModel).useGhostedLook(True)

                    prompt("Topo mode activated!")
                else:
                    self.widget.findChild(qtw.QToolButton, "topo_toggle").setChecked(False)
                    prompt("Topo mode deactivated!")
                    
            # OFF
            else:
                with hou.undos.disabler():
                    topo_src.destroyUserData("__topo__")
                    topo_src.setSelectableInViewport(True)
                    topo_src.setDisplayFlag(True)



                    for parm in topo_src.parmsReferencingThis():
                        node = parm.node()
                        if node.isTemplateFlagSet():
                            node.setTemplateFlag(False)

                self.widget.findChild(qtw.QToolButton, "topo_toggle").setChecked(False)
                prompt("Topo mode deactivated!")


            hou.undos.clear()

        # TOPOBUILD
        elif name == "topobuild_build":
            self.topobuild()

        # POLYPEN
        elif name == "polypen":
            hou.modeler.states.PolyPen()

        elif name == "magnet":
            hou.modeler.states.Magnet()

        elif name == "knife":
            hou.modeler.states.Knife()
        
        elif name == "polygons":
            self.polygons()

        elif name == "loop":
            VIEWER.runShelfTool("sop_edgeloop")

        elif name == "delete":
            sop, group, grouptype, empty = self.selection(activate_one_object=False)
            if sop is not None and group is not None:
                with hou.undos.group("Modeler: Delete"):  
                    if grouptype == hou.geometryType.Edges:
                        sop = sop.createOutputNode("dissolve::2.0")
                        sop.setParms({ "group": group, "deldegeneratebridges": True, "coltol": 100 })
                
                        self.activate_sop_with_select_state(sop)
                
                    elif grouptype == hou.geometryType.Points:
                        prim_sel = self.last_selection.freeze()
                        prim_sel.convert(self.last_selection_geo, hou.geometryType.Primitives)

                        # DISSOLVE POINT EDGES
                        if prim_sel.numSelected() >= self.last_selection.numSelected() * 3:
                            edge_sel = self.last_selection.freeze()
                            edge_sel.convert(self.last_selection_geo, hou.geometryType.Edges)
                            sop = sop.createOutputNode("dissolve::2.0")
                            sop.parm("group").set( edge_sel.selectionString(self.last_selection_geo) )
                        
                        # DEL POINTS
                        else:
                            sop = sop.createOutputNode("blast")
                            sop.setParms({ "group": group, "grouptype": 3 })

                        self.activate_sop_with_select_state(sop)
                
                    elif grouptype == hou.geometryType.Primitives:
                        if sop.type().name() == "modeler::unwrap" and sop.evalParm("do_unwrap"):
                            sop.hdaModule().add_rectify_prims(sop, hou.pickModifier.Add)
                        else:
                            sop = sop.createOutputNode("blast")
                            sop.parm("group").set(group)
                
                            self.activate_sop_with_select_state(sop)

            elif group is not None:
                with hou.RedrawBlock() as rb:
                    VIEWER.setPwd(group[0].parent())
                    with hou.undos.group("Modeler: Delete"):
                        for n in group:
                            n.destroy()
                            
            else:
                prompt(PROMPT_OBJECTS_OR_COMPONENTS)
        
        elif name == "collapse":
            sop, group, grouptype, empty = self.selection()
            if sop is not None and group is not None:
                # SEW EDGES IN UV EDITOR
                if VIEWER.curViewport().type() == hou.geometryViewportType.UV and grouptype == hou.geometryType.Edges:
                    VIEWER.setCurrentState("uvedit")
                    hou.ui.waitUntil(lambda: True)
                    self.run_stock_hotkey_action("h.pane.gview.state.sop.uvedit.toggle_sew")

                # MORE THEN ONE POINT
                elif grouptype == hou.geometryType.Points:
                    if self.last_selection.numSelected() > 1:
                        with hou.undos.group("Modeler: Collapse"):  
                            f1 = sop.createOutputNode("fuse")
                            f1.setParms({"querygroup": group, "tol3d": 999999, "createsnappedgroup": True})
                            new_point = str(f1.geometry().findPointGroup("snapped_points").points()[0].number())
                            f1.parm("createsnappedgroup").set(False)
                            self.activate_sop_with_select_state(f1, False)
                            sel = hou.Selection(sop.geometry(), grouptype, new_point)
                            VIEWER.setCurrentGeometrySelection(grouptype, (f1,), (sel,))
                    else:
                        prompt("More than one point must be selected")

                # EDGES OR FACES
                else:
                    with hou.undos.group("Modeler: Collapse"):  
                        geo = sop.geometry()
                        sop = sop.createOutputNode("edgecollapse")
                        sop.parm("group").set(group)
                        self.activate_sop_with_select_state(sop, False)
            else:
                prompt(PROMPT_POINTS_EDGES_POLYGONS)

        elif name == "split_by_edges":
            sop, group, grouptype, empty = self.selection()
            if grouptype in (hou.geometryType.Edges, hou.geometryType.Primitives) and not empty:
                with hou.undos.group("Modeler: Split By Edges"):  
                    sop = sop.createOutputNode("modeler::split_by_edges")
                    sop.parm("group").set(group)
                    self.activate_sop_with_select_state(sop)
                    VIEWER.setPickGeometryType(hou.geometryType.Primitives)
            else:
                prompt(PROMPT_EDGES_OR_POLYGONS)

        elif name == "connect":
            sop, group, grouptype, empty = self.selection()
            if grouptype is not None:
                succes = True
                # EDGES
                if grouptype == hou.geometryType.Edges:
                    grouptype = 1
                
                # POINTS
                elif grouptype == hou.geometryType.Points:
                    count = self.last_selection.numSelected()
                    if count == 1:
                        prompt("More than one polygon must be selected")
                        succes = False

                    elif count > 2:
                        # HOUDINI ISSUE. CREATE GROUP MANUALLY
                        points = self.last_selection.points(self.last_selection_geo)
                        group = " ".join( [str(point.number()) for point in points] )
                        grouptype = 0
                    
                    elif count == 2:
                        pt1, pt2 = self.last_selection.points(self.last_selection_geo)
                        edge = self.last_selection_geo.findEdge(pt1, pt2)
                        
                        if edge is None:
                            grouptype = 0

                        else:
                            group = edge.edgeId()
                            grouptype = 1

                # POLYGONS
                else:
                    if self.last_selection.numSelected() == 1:
                        prompt("More than one polygon must be selected")
                        succes = False
                    else:        
                        grouptype = 2

                if succes:
                    with hou.undos.group("Modeler: Connect"):  
                        sop = sop.createOutputNode("modeler::connect")
                        sop.setParms({ "group": group, "grouptype": grouptype })
                        self.activate_sop_with_select_state(sop)

            else:
                prompt(PROMPT_POINTS_EDGES_POLYGONS)
        
        elif name == "loop_cut":
            sop, group, grouptype, empty = self.selection()
            if grouptype == hou.geometryType.Edges:
                with hou.undos.group("Modeler: Loop Cut"):  
                    sop = sop.createOutputNode("modeler::loop_cut")
                    sop.setParms({ "group": group })
                    self.activate_sop_with_state(sop)
            else:
                prompt(PROMPT_EDGES)
        
        elif name == "topo_project":
            self.topo_project()

        elif name == "toolbar_network_merge":
            pwd = VIEWER.pwd()
            sel_nodes = hou.selectedNodes()
            nodes = [node for node in (sel_nodes or pwd.children()) if node.type().name()=="geo"]
            
            # OBJ
            if nodes:
                with hou.undos.group("Modeler: Toolbar Network Merge"):
                    parent = nodes[0].parent()
                    null = parent.createNode("null", "merged_objects1")
                    global_center = hou.Vector3()
                    for node in nodes:
                        sop = node.displayNode()
                        if sop is not None:
                            global_center += sop.geometry().boundingBox().center() * node.worldTransform()

                        node.setInput(0, null)

                    global_center /= len(nodes)
                    null.parm("childcomp").set(True)
                    null.parmTuple("t").set(global_center)
                    null.parm("childcomp").set(False)
                    null.setCurrent(True, True)
                    parent.layoutChildren( [null] + nodes )
                    home_selected()

            # SOP
            elif sel_nodes and sel_nodes[0].type().category() == hou.sopNodeTypeCategory():
                with hou.undos.group("Modeler: Toolbar Network Merge"):
                    if len(sel_nodes) > 1:
                        sop = sel_nodes[0]
                        m = sop.createOutputNode("switch" if qt_app.queryKeyboardModifiers() == qt.ControlModifier else "merge")
                        for node in sel_nodes[1:]:
                            m.setNextInput(node)
                        m.moveToGoodPosition()
                        m.setDisplayFlag(True)
                        m.setRenderFlag(True)
                        m.setCurrent(True, True)
                        home_selected()
                    
                    else:
                        tmp_nodes = [ child for child in pwd.children() if (child.isTemplateFlagSet() and child != sel_nodes[0]) ]
                        if tmp_nodes:
                            m = sel_nodes[0].createOutputNode("switch" if qt_app.queryKeyboardModifiers() == qt.ControlModifier else "merge")
                            for tmp in tmp_nodes:
                                tmp.setTemplateFlag(False)
                                m.setNextInput(tmp)

                            m.moveToGoodPosition()
                            m.setDisplayFlag(True)
                            m.setRenderFlag(True)
                            m.setCurrent(True, True)
                            home_selected()

        # VIEWBAR
        elif name == "handle_detach":
            self.run_stock_hotkey_action("h.pane.gview.handle.xform.handle_geometry_detachment")
        
        elif name == "handle_orient":
            self.run_stock_hotkey_action("h.pane.gview.handle.xform.click_orient")
        
        elif name == "handle_space":
            self.run_stock_hotkey_action("h.pane.gview.handle.xform.cycle_alignment")

        # FRAME SELECTED
        elif name == "frame_selected":
            VIEWER.curViewport().frameSelected()

        # FRAME ALL
        elif name == "frame_all":
            VIEWER.curViewport().frameAll()

        elif name == "align_view":
            align_view.start()

        # REPEAT
        elif name == "repeat":
            self.run_stock_hotkey_action("h.pane.gview.repeat_current")
        
        # UNDO
        elif name == "undo":
            executeDeferred(hou.undos.performUndo)

        # REDO
        elif name == "redo":
            executeDeferred(hou.undos.performRedo)

        # MULTISNAP
        elif name == "multisnap":
            if self.viewbar.findChild(qtw.QToolButton, "multisnap").isChecked():
                VIEWER.setSnappingMode(hou.snappingMode.Multi)
            else:
                VIEWER.setSnappingMode(hou.snappingMode.Off)

        # MOVE
        elif name == "move":
            self.xform(0)

        # ROTATE
        elif name == "rotate":
            self.xform(1)

        # SCALE
        elif name == "scale":
            self.xform(2)

        elif name == "relax":
            sop, group, grouptype, empty = self.selection()
            if grouptype is not None:
                if grouptype == hou.geometryType.Primitives:
                    grouptype = 0

                elif grouptype == hou.geometryType.Points:
                    grouptype = 1
                
                else:
                    grouptype = 2
             
                if not ( sop.type().name() == "modeler::relax" and sop.evalParm("group") == group and sop.evalParm("grouptype") == grouptype and sop.evalParm("project_to_src") == True ):
                    with hou.undos.group("Modeler: Relax"):
                        sop = sop.createOutputNode("modeler::relax")
                        sop.setParms({ "group": group, "grouptype": grouptype, "highlight_selection": not self.is_all_selected(self.last_selection, self.last_selection_geo) })
                        self.activate_sop_with_state(sop)

            else:
                prompt(PROMPT_POINTS_EDGES_POLYGONS)

        elif name == "slide":
            hou.modeler.states.Grab.override_command = "slide"
            hou.modeler.states.grab("modeler::grab")

        elif name == "peak":
            hou.modeler.states.grab("modeler::grab_peak")

        elif name == "node_state":
            pwd = VIEWER.pwd()
            if pwd.childTypeCategory() == hou.sopNodeTypeCategory():
                display = pwd.displayNode()
                if display is not None:
                    if not display.isSelected():
                        display.setCurrent(True, True)
                    VIEWER.enterCurrentNodeState()

            elif pwd.childTypeCategory() == hou.objNodeTypeCategory() and hou.selectedNodes():
                VIEWER.enterCurrentNodeState()

        elif name == "add_mod":
            VIEWER.setPickModifier(hou.pickModifier.Add)

        elif name == "remove_mod":
            VIEWER.setPickModifier(hou.pickModifier.Remove)

        elif name == "replace_mod":
            VIEWER.setPickModifier(hou.pickModifier.Replace)

        elif name == "convert":
            self._viewbar_convert_mode = True

        elif name == "select_objects":
            if VIEWER.selectionMode() == hou.selectionMode.Geometry:
                if VIEWER.currentNode() == VIEWER.pwd():
                    VIEWER.setPwd(hou.node("/obj"))

                VIEWER.setSelectionMode(hou.selectionMode.Object)
                VIEWER.setCurrentState("select")
            else:
                if VIEWER.currentState() == "select":
                    hou.clearAllSelected()
                else:
                    VIEWER.setCurrentState("select")

        # POINTS MODE
        elif name == "select_points":
            self.set_selection_mode(hou.geometryType.Points)

        # EDGES MODE
        elif name == "select_edges":
            self.set_selection_mode(hou.geometryType.Edges)

        # POLYGONS MODE
        elif name == "select_polygons":
            self.set_selection_mode(hou.geometryType.Primitives)


        elif name == "parm_slider":
            parm_slider.start()

        elif name == "rmb_menu":
            gpos = qtg.QCursor.pos() + qtc.QPoint(0, hou.ui.scaledSize(10))
            lpos = VIEWER_WIDGET.mapFromGlobal(gpos)
            qtg.QCursor.setPos(gpos)
            VIEWER_WIDGET.removeEventFilter(self)
            qtest.mouseClick(VIEWER_WIDGET, qt.RightButton, qt.NoModifier, lpos)
            VIEWER_WIDGET.installEventFilter(self)

        elif name == "wire":
            self.run_stock_hotkey_action("h.pane.gview.toggle_wireshaded")
        
        elif name == "wire_on_shade":
            self.run_stock_hotkey_action("h.pane.gview.toggle_wireover")

        elif name == "preview_subd":
            preview_subd_ef.start(False)

        elif name == "preview_subd_wired":
            preview_subd_ef.start(False, hou.glShadingType.SmoothWire)

        elif name == "preview_subd_isolines":
            preview_subd_ef.start(True)


        elif name == "tumble":
            navigator.start(0)


        elif name == "pan":
            navigator.start(1)

        elif name == "zoom":
            navigator.start(2)

        elif name == "ortho":
            align_view.finish()
            VIEWER.curViewport().defaultCamera().setPerspective( not VIEWER.curViewport().defaultCamera().isPerspective() )

    def modeler_resource_clicked_callback(self, name):
        if qt_app.queryKeyboardModifiers() == qt.NoModifier:
            self.modeler_resource_exec(name)
            
            if name != "reload":
                VIEWER_WIDGET.setFocus()

        elif qt_app.queryKeyboardModifiers() == qt.ControlModifier:
            hotkey_manager.assign(name)

    def update_viewbar_pos(self):
        if self.viewbar is not None:
            self.viewbar.move( VIEWER_WIDGET.mapToGlobal(qtc.QPoint(hou.ui.scaledSize(6), hou.ui.scaledSize(6))) )

    def reset_shading_mode(self):
        settings = VIEWER.curViewport().settings()
        sm = settings.displaySet(hou.displaySetType.DisplayModel).shadedMode()
        ds1 = settings.displaySet(hou.displaySetType.SceneObject)
        ds2 = settings.displaySet(hou.displaySetType.GhostObject)
        ds1.setShadedMode(sm)
        ds2.setShadedMode(sm)
        ds1.setShadingModeLocked(False)
        ds2.setShadingModeLocked(False)

    # DESTROY WHOLE WIDGET EVENT: FOR RELOAD BUTTON OR CLOSING HOUDINI
    def destroy_event(self, event):
        if qt_app.widgetAt(qtg.QCursor.pos()) != self.tab_widget.tabBar():
            self.save_config_files()

    def reset_setup_callback(self):
        self.setup_list = default_setup_list.copy()
        exec(self.toolbar_reload_callback_script)

    def clear_favorites_callback(self):
        if not hou.ui.displayMessage("Clear Favorites list?", title="Clear Favorites List", buttons=("Yes", "No"), default_choice=1, close_choice=1):
            self.favorites.clear()

    ### CONFIG FILES ###
    def load_config_files(self):
        # FAVORITES
        if os.path.exists(self.favorites_config_file):
            with open(self.favorites_config_file, 'rb') as f:
                try:
                    self.favorites_list = pickle.loads(f.read())
                    
                    # RESIZE SPLITTER WIDGETS
                    self.splitter.setSizes( self.favorites_list.pop() )
                except:
                    self.favorites_list = []

        # EMPTY LIST IF THE FILE NOT EXISTS
        else:
            self.favorites_list = []

        # SETUP
        if os.path.exists(self.setup_file):
            with open(self.setup_file, 'rb') as f:
                try:
                    self.setup_list = pickle.loads(f.read())
                except:
                    self.setup_list = default_setup_list.copy()
        
        # DEFAULT DICT IF FILE DOES NOT EXIST
        else:
            self.setup_list = default_setup_list.copy()


        # UPDATE SETUP UI CONTROLS VALUES
        self.material_type.setText(self.setup_list[0])
        self.template_at_sop_level.setChecked(self.setup_list[1])

    def save_config_files(self):
        # BUILD FAVORITES LIST
        favorites_to_save = []
        for i in range(self.favorites.count()):
            item = self.favorites.item(i)
            
            # SHELF TOOL
            if hasattr(item, "shelf_tool_name"):
                favorites_to_save.append( (item.shelf_tool_name, None) )
            
            # RADIAL MENU
            elif hasattr(item, "rm_name"):
                favorites_to_save.append( (None, item.rm_name) )
            
            # SEPARATOR
            else:
                favorites_to_save.append( (None, None) )

        # SAVE SPLITTER SIZES
        favorites_to_save.append( self.splitter.sizes() )

        # SAVE FAVORITES FILE
        with open(self.favorites_config_file, 'wb') as f:
            f.write( pickle.dumps(favorites_to_save) )

        # SAVE SETUP FILE
        with open(self.setup_file, 'wb') as f:
            f.write( pickle.dumps(self.setup_list) )

    def update_setup_list_from_ui(self, arg):
        self.setup_list = [ self.material_type.text(), self.template_at_sop_level.isChecked() ] 

    ### QT WIDGETS FUNCTIONS ###
    def build_tree(self):
        # CLEAR WIDGET
        self.tree.clear()

        # SHELF TOOLS
        shelves = hou.shelves.shelves()
        houdini_main_shelves = [ "create", "polygon", "modify", "deform", "model" ]
        
        sorted_names = houdini_main_shelves + [ name for name in shelves.keys() if name not in houdini_main_shelves ]

        for name in sorted_names:
            shelf = shelves[name]
            shelf_item = qtw.QTreeWidgetItem(self.tree, [shelf.label()])
            self.tree.addTopLevelItem(shelf_item)

            for tool in shelf.tools():
                tool_name = tool.name()

                tool_item = qtw.QTreeWidgetItem([tool.label()])
                tool_item.shelf_tool_name = tool_name
                tool_item.setToolTip(0, 'Shelf Tool Name: "%s"\nShelf Tool Label: "%s"' % (tool_name, tool.label()))

                try:
                    tool_item.setIcon(0, hou.qt.Icon(tool.icon(), hou.ui.scaledSize(20), hou.ui.scaledSize(20)))
                except:
                    pass

                # ADD ITEM
                shelf_item.addChild(tool_item)

            # SEPARATORS
            if name == "model":
                qtw.QTreeWidgetItem(self.tree, "")

        # SEPARATOR BEFORE RADIAL MENUS
        qtw.QTreeWidgetItem(self.tree, "")

        # RADIAL MENUS
        radial_menus_item = qtw.QTreeWidgetItem(self.tree, ["Radial Menus"])
        initial_rm_names = [ menu.name() for menu in hou.ui.radialMenus() ]
        sorted_rm_names = [ "defaultmodeling", "polymodel", "curvesop", "curvemodeling", "textureedit" ]
        sorted_rm_names += [ name for name in initial_rm_names if name not in sorted_rm_names ]

        for name in sorted_rm_names:
            menu = hou.ui.radialMenu(name)
            item = qtw.QTreeWidgetItem([menu.label()])
            item.setIcon(0, self.rm_icon)
            item.rm_name = menu.name()
            radial_menus_item.addChild(item)

            # SEPARATORS
            if name == "textureedit":
                qtw.QTreeWidgetItem(radial_menus_item, "")

    def build_favorites_list(self):
        self.favorites.clear()
        
        # BUILD FAVORITES LIST
        for shelf_tool_name, rm_name in self.favorites_list:
        
            # SHELF TOOL
            if shelf_tool_name is not None:
                shelf_tool = hou.shelves.tool(shelf_tool_name)
    
                # ADD ITEM IF THE TOOL EXISTS IN HOUDINI
                if shelf_tool is not None:
                    # IF HOUDINI ICON EXISTS
                    try:
                        item = qtw.QListWidgetItem(hou.qt.Icon(shelf_tool.icon(), hou.ui.scaledSize(20), hou.ui.scaledSize(20)), shelf_tool.label())
                    
                    # OR USE JUST A LABEL
                    except hou.OperationFailed:
                        item = qtw.QListWidgetItem(shelf_tool.label())

                    item.shelf_tool_name = shelf_tool_name
                    self.favorites.addItem(item)
            
            # RADIAL MENU
            elif rm_name is not None:
                radial_menu = hou.ui.radialMenu(rm_name)
                # ADD ITEM IF THE RADIAL MENU EXISTS IN HOUDINI
                if radial_menu is not None:
                    item = qtw.QListWidgetItem(self.rm_icon, radial_menu.label())
                    item.rm_name = rm_name
                    self.favorites.addItem(item)
            
            # SEPARATOR
            else:
                self.favorites.addItem("")

    ### TREE FUNCRIONS ###
    def tree_clicked(self, item, col):
        if qt_app.queryKeyboardModifiers() == qt.NoModifier:
            if hasattr(item, "shelf_tool_name"):
                VIEWER_WIDGET.setFocus()
                VIEWER.runShelfTool(item.shelf_tool_name)
            
            elif hasattr(item, "rm_name"):
                cursor_pos = VIEWER_WIDGET.mapToGlobal(VIEWER_WIDGET.rect().center())
                qtg.QCursor.setPos(cursor_pos)
                VIEWER.displayRadialMenu(item.rm_name)

        elif qt_app.queryKeyboardModifiers() == qt.ControlModifier:
            if hasattr(item, "shelf_tool_name"):
                hotkey_manager.assign(item.shelf_tool_name)

            elif hasattr(item, "rm_name"):
                hotkey_manager.assign(item.rm_name)

            else:
                return

    ### FAVORITES FUNCTIONS ###
    def favorites_clicked(self, item):
        if qt_app.queryKeyboardModifiers() == qt.NoModifier:
            if hasattr(item, "shelf_tool_name"):
                VIEWER_WIDGET.setFocus()
                VIEWER.runShelfTool(item.shelf_tool_name)
            
            elif hasattr(item, "rm_name"):
                cursor_pos = VIEWER_WIDGET.mapToGlobal(VIEWER_WIDGET.rect().center())
                qtg.QCursor.setPos(cursor_pos)
                VIEWER.displayRadialMenu(item.rm_name)

        elif qt_app.queryKeyboardModifiers() == qt.ControlModifier:
            result = hou.ui.displayMessage(('Delete "%s" item?' % item.text()).replace('""', "separator"), buttons=("Yes", "No", "Delete All"), close_choice=1, default_choice=1, title="Delete Item")
            if not result:
                self.favorites.takeItem(self.favorites.row(item))
            elif result == 2:
                self.favorites.clear()
            else:
                item.setSelected(True)

    def favorites_row_inserted(self, index, a, b):
        current_tree_item = self.tree.currentItem()
        
        item = self.favorites.item(a)

        if hasattr(current_tree_item, "shelf_tool_name"):
            item.shelf_tool_name = current_tree_item.shelf_tool_name
        
        elif hasattr(current_tree_item, "rm_name"):
            item.rm_name = current_tree_item.rm_name
        
        self.favorites.model().rowsInserted.disconnect(self.favorites_row_inserted)

    def favorites_dropEvent(self, event):
        # DRAGGED FROM THE TREE WIDGET
        if event.source() == self.tree:
            cur_item = self.tree.currentItem()
            if hasattr(cur_item, "shelf_tool_name") or hasattr(cur_item, "rm_name") or not cur_item.text(0):
                self.favorites.model().rowsInserted.connect(self.favorites_row_inserted)
                self.favorites.setDragDropMode(qtw.QAbstractItemView.DragDrop)
                super(qtw.QListWidget, self.favorites).dropEvent(event)

        # ALLOW TO MOVE INTERNALLY
        else:
            self.favorites.setDragDropMode(qtw.QAbstractItemView.InternalMove)
            super(qtw.QListWidget, self.favorites).dropEvent(event)

    ### FILTER FIELD FUNCRIONS ###
    def filter_tree_slot(self, text):
        cursor = qtw.QTreeWidgetItemIterator(self.tree)
        while cursor.value():
            item = cursor.value()
            if text.lower() in item.text(0).lower():
                item.setHidden(False)
                try:
                    item.parent().setHidden(False)
                except Exception:
                    pass
            else:
                item.setHidden(True)

            cursor = cursor.__iadd__(1)

        if text:
            self.tree.expandAll()
        else:
            self.tree.collapseAll()

    def clear_filter_field_slot(self, event):
        self.filter_field.setText("")

    def is_create_at_sop_level(self):
        return self.widget.findChild(qtw.QToolButton, "create_at_sop_level").isChecked()

    def geo_qprimitive(self, primitive_type):
        pwd = VIEWER.pwd()
        sop = None

        with hou.undos.group("Modeler: QPrimitive"):
            # SOPS: CREATE ONLY SOP
            if pwd.childTypeCategory() == hou.sopNodeTypeCategory():
                display = pwd.displayNode()
                
                if self.is_create_at_sop_level():
                    sop = pwd.createNode("modeler::qprimitive")
        
                    if display is not None:
                        sop.setPosition(display.position() + hou.Vector2(3, 0))
                        if self.setup_widget.findChild(qtw.QCheckBox, "template_at_sop_level").isChecked():
                            display.setTemplateFlag(True)
                    
                    at_obj = False
        
                else:
                    obj = hou.node("/obj").createNode("geo", "qprimitive_object1")
                    obj.moveToGoodPosition()
                    sop = obj.createNode("modeler::qprimitive")

                    at_obj = True

            # OTHERS: CREATE OBJECT AND SOP
            else: 
                obj = hou.node("/obj").createNode("geo", "qprimitive_object1")
                obj.moveToGoodPosition()
                sop = obj.createNode("modeler::qprimitive")

                at_obj = True

            # MODIFY CREATED SOP
            if sop is not None:
                sop.parm("type").set(primitive_type)    

                t = None
                xform = self.get_cplane_xform_if_visible()
                if xform is not None:
                    xform = hou.hmath.buildRotate(90.0, 0.0, 0.0) * xform
                    t = xform.extractTranslates()
                    r = xform.extractRotates()
                    sop.parmTuple("t").set(t)
                    sop.parmTuple("r").set(r)

                # TRY TO SCALE NODE ACCORDING TO PREVIOUSLY CREATED NODE
                ii = list(sop.type().instances())
                if len(ii) > 1:
                    ii.pop()
                    ii.reverse()
                    for i in ii:
                        sop.parm("scale").set( i.evalParm("scale") )
                        break

                # MODIFY TRANSFORM
                if t is not None:
                    sop.parmTuple("t").set(t)
                    sop.parmTuple("r").set(r)

                # SET SOP AS CURRENT
                if not sop.isCurrent():
                    sop.setCurrent(True, True)

                if not sop.isDisplayFlagSet():
                    sop.setDisplayFlag(True)
                    sop.setRenderFlag(True)

                # WAIT IF THE PRIMITIVE WAS CREATED AT OBJECT LEVEL
                if at_obj:
                    hou.ui.waitUntil(lambda: True)
                
                # ENTER NODE STATE
                VIEWER.enterCurrentNodeState()

                home_selected()

    def walk_selection(self, target_dir):
        sop, group, grouptype, empty = self.selection()
        if grouptype is not None:
            with hou.undos.group("Modeler: Walk Selection"):
                sop.setCurrent(True, True)
                g = sop.createOutputNode("modeler::walk")
                
                if grouptype == hou.geometryType.Primitives:
                    grouptype_ = 0
                
                elif grouptype == hou.geometryType.Points:
                    grouptype_ = 1

                else:
                    grouptype_ = 2

                g.setParms({ "group": group, "grouptype": grouptype_, "add": qt_app.queryKeyboardModifiers() == qt.ShiftModifier })
                target_dir = target_dir * VIEWER.curViewport().viewTransform().inverted().transposed() * self.ancestor_object(sop).worldTransform().transposed()
                g.parmTuple("target_dir").set(target_dir)
                
                self.set_sop_selection(sop, g.geometry().selection(), grouptype)
                g.destroy()
        else:
            prompt(PROMPT_POINTS_EDGES_POLYGONS)

    def grow_selection(self, grow=True):
        sop, group, grouptype, empty = self.selection()
        if grouptype is not None:
            with hou.undos.group("Modeler: Grow | Shrink Selection"):
                sel = self.last_selection.freeze()
                if grow:
                    sel.grow(self.last_selection_geo)
                else:
                    sel.shrink(self.last_selection_geo)
                if not self.last_selection_was_scripted:
                    VIEWER.setPickGeometryType(grouptype)
                    VIEWER.setCurrentState("select")
                VIEWER.setCurrentGeometrySelection(grouptype, (sop,), (sel,))

    def shrink_selection(self):
        self.grow_selection(False)

    def set_selection_mode(self, sel_type):
        with hou.RedrawBlock() as rb:
            VIEWER.setGroupPicking(False)

            # SCRIPTSELECT 
            if VIEWER.currentState() == "scriptselect":
                
                # CONVERT
                if self._viewbar_convert_mode:
                    if sel_type == hou.geometryType.Points:
                        self.run_stock_hotkey_action("h.pane.gview.model.sel.convertpoint")
                    
                    elif sel_type == hou.geometryType.Primitives:
                        self.run_stock_hotkey_action("h.pane.gview.model.sel.convertprimitive")
                    
                    elif sel_type == hou.geometryType.Edges:
                        self.run_stock_hotkey_action("h.pane.gview.model.sel.convertedge")

                # SELECT
                else:            
                    if sel_type == hou.geometryType.Points:
                        self.run_stock_hotkey_action("h.pane.gview.model.seltypepoints")
                    
                    elif sel_type == hou.geometryType.Primitives:
                        self.run_stock_hotkey_action("h.pane.gview.model.seltypeprims")
                    
                    elif sel_type == hou.geometryType.Edges:
                        self.run_stock_hotkey_action("h.pane.gview.model.seltypeedges")

                self._viewbar_convert_mode = False
            
            # REGULAR SELECTION 
            else:
                pwd = VIEWER.pwd()

                # SOP
                if pwd.childTypeCategory() == hou.sopNodeTypeCategory():
                    
                    # CONVERT
                    if self._viewbar_convert_mode:
                        sop, group, grouptype, empty = self.selection()
                        if grouptype is not None:
                            sel = self.last_selection.freeze()
                            sel.convert(self.last_selection_geo, sel_type)
                            VIEWER.setPickGeometryType(sel_type)
                            hou.ui.waitUntil(lambda: True)
                            VIEWER.setCurrentState("select")
                            VIEWER.setCurrentGeometrySelection(sel_type, (sop,), (sel,))
                        

                    # SELECT
                    else:
                        if sel_type == hou.geometryType.Points and VIEWER.curViewport().type() == hou.geometryViewportType.UV:
                            if VIEWER.pickGeometryType() != hou.geometryType.Vertices:
                                sel_type = hou.geometryType.Vertices

                        display = pwd.displayNode()
                        if display is not None:
                            if not display.isCurrent():
                                VIEWER.setCurrentNode(display)
                            VIEWER.setCurrentState("select")
                            VIEWER.setPickGeometryType(sel_type)
                            self.clear_sop_selection()
                # OBJ
                elif pwd.childTypeCategory() == hou.objNodeTypeCategory():
                    cur_node = VIEWER.currentNode()
                    if cur_node.childTypeCategory() == hou.sopNodeTypeCategory():
                        display = cur_node.displayNode()
                        if display is not None:
                            VIEWER.setCurrentNode(display)
                            VIEWER.setPickGeometryType(sel_type)
                            VIEWER.setCurrentState("select")
                            
                            self.clear_sop_selection()
                
                self._viewbar_convert_mode = False

    def convert_selection(self, sel_type):
        sop, group, grouptype, empty = self.selection()
        if grouptype is not None:
            if not self.last_selection_was_scripted:
                VIEWER.setCurrentState("select")
            
            if sel_type == hou.geometryType.Points:
                self.run_stock_hotkey_action("h.pane.gview.model.sel.convertpoint")
            elif sel_type == hou.geometryType.Edges:
                self.run_stock_hotkey_action("h.pane.gview.model.sel.convertedge")
            else:
                self.run_stock_hotkey_action("h.pane.gview.model.sel.convertprimitive")
           
            VIEWER.setGroupPicking(False)

    def fill(self):
        sop, group, grouptype, empty = self.selection()
        if grouptype is not None:
            with hou.undos.group("Modeler: Fill"):
                if grouptype == hou.geometryType.Points:
                    if self.last_selection.numSelected() < 3:
                        prompt( "At least 3 points must be selected")
                    else:
                        points = self.last_selection.points(self.last_selection_geo)
                        group = " ".join( [str(point.number()) for point in points] )
                        sop = sop.createOutputNode("modeler::polygon")
                        sop.parm("group").set(group)
                        self.activate_sop_with_select_state(sop)

                elif grouptype == hou.geometryType.Edges:
                    sop = sop.createOutputNode("polyfill")
                    sop.setParms({ "group": group, "fillmode": 0, "smoothtoggle": False, "subdivtoggle": False, "completeloops": True })
                    self.activate_sop_with_select_state(sop)

                elif grouptype == hou.geometryType.Primitives:
                    sop1 = sop.createOutputNode("modeler::quadrify")
                    
                    om = self.topo_get_ref(sop.parent())
                    sop1.setInput(1, sop if om is None else om)
                        
                    

                    sop1.parm("group").set(group)
                    self.activate_sop_with_select_state(sop1)
        else:
            prompt(PROMPT_POINTS_EDGES_POLYGONS)

    def boolean(self, op):
        pwd = VIEWER.pwd()
        child_cat = pwd.childTypeCategory()
        
        if child_cat == hou.objNodeTypeCategory():
            nodes = [ node for node in hou.selectedNodes() if node.type().name()=="geo" ]
            count = len(nodes)
            if count != 2:
                prompt("Select the cutter object, the object to cut from, and try again")
                return
            
            cutter_object = nodes[0]
            cutter_object_sop = cutter_object.displayNode()
            src_object = nodes[1]
            src_object_sop = src_object.displayNode()
            
            if src_object_sop is not None and cutter_object_sop is not None:
                src_object_xform_inverted = src_object.worldTransform().inverted()
                cutter_object_xform = cutter_object.worldTransform() * src_object_xform_inverted                
                
                with hou.undos.group("Modeler: Boolean Operation"):
                    src_object.setCurrent(True, True)
                    
                    boolean_sop = src_object_sop.createOutputNode("modeler::boolean")
                    boolean_sop.parm("type").set(op if op < 3 else 2)
                    if op == 3:
                        boolean_sop.parm("do_cutter_thickness").set(True)

                    nodes = (cutter_object_sop,) + cutter_object_sop.inputAncestors()
                    xform_sop = src_object.createNode("xform")
                    new_nodes = hou.moveNodesTo(nodes, src_object)
                    xform_sop.setInput(0, new_nodes[0])
                    boolean_sop.setNextInput(xform_sop)
                    
                    xform_sop.parmTuple("t").set( cutter_object_xform.extractTranslates() )
                    xform_sop.parmTuple("r").set( cutter_object_xform.extractRotates() )
                    xform_sop.parmTuple("s").set( cutter_object_xform.extractScales() )
                    xform_sop.parmTuple("shear").set( cutter_object_xform.extractShears() )
                    
                    cutter_object.destroy()
                    boolean_sop.parmTuple("p").set( xform_sop.evalParmTuple("t") )
                    boolean_sop.parmTuple("pr").set( xform_sop.evalParmTuple("r") )
                    boolean_sop.setDisplayFlag(True)
                    boolean_sop.setRenderFlag(True)
                    boolean_sop.setCurrent(True, True)
                    
                    src_object.layoutChildren()
                    
                VIEWER.enterCurrentNodeState()
                
            else:
                prompt("Cutter and source objects must have a display node")
                    
        elif child_cat == hou.sopNodeTypeCategory():
            sel = hou.selectedNodes()
            if len(sel) == 2:
                with hou.undos.group("Modeler: Boolean Operation"):
                    sop1 = sel[1].createOutputNode("modeler::boolean")
                    sop1.parm("type").set(op if op < 3 else 2)
                    if op == 3:
                        sop1.parm("do_cutter_thickness").set(True)
                    sop1.setInput(1, sel[0])
                    sop1.setDisplayFlag(True)
                    sop1.setRenderFlag(True)
                    sop1.setCurrent(True, True)
            
                VIEWER.enterCurrentNodeState()
                
            else:
                sop, group, grouptype, empty = self.selection()
                if sop is not None:
                    with hou.undos.group("Modeler: Boolean Operation"):
                        if empty:
                            next_pwd, next_sop = self.get_object("Select the object to cut from")
                            if next_pwd is not None and next_pwd != pwd:
                                xform = pwd.worldTransform() * next_pwd.worldTransform().inverted()
                                pivot = self.last_selection_geo.boundingBox().center() * xform
                                boolean_sop = self.merge_with_object(sop, pwd, next_sop, next_pwd, merge_node_type="modeler::boolean", merge_node_parms={"type": op if op < 3 else 2, "do_cutter_thickness": op==3})
                                xform_sop = boolean_sop.inputs()[1]
                                boolean_sop.parmTuple("p").set( xform_sop.evalParmTuple("t") )
                                boolean_sop.parmTuple("pr").set( xform_sop.evalParmTuple("r") )                       
                                VIEWER.enterCurrentNodeState()
                        
                        elif grouptype == hou.geometryType.Primitives:
                            sop = sop.createOutputNode("split", "separate_boolean_cutter1")
                            sop.setParms({ "group": group, "negate": True })
                            sop1 = sop.createOutputNode("modeler::boolean")
                            sop1.parm("type").set(op if op < 3 else 2)
                            if op == 3:
                                sop1.parm("do_cutter_thickness").set(True)
                            
                            sop1.setInput(1, sop, 1)
                            sop1.parmTuple("p").set( self.last_selection_geo.primBoundingBox(group).center() )                    
                            sop1.setDisplayFlag(True)
                            sop1.setRenderFlag(True)
                            sop1.setCurrent(True, True)
                           
                            VIEWER.enterCurrentNodeState()

    def lattice(self):
        pwd = VIEWER.pwd()
        
        # TRY TO FINISH LATTICE OPERATION
        if pwd.childTypeCategory() == hou.sopNodeTypeCategory():
            sop = pwd.displayNode()
            if sop is not None:
                outputs = sop.outputs()
                if outputs and outputs[0].type().name() == "modeler::lattice":
                    sop = outputs[0]
                    with hou.undos.group("Modeler: Lattice Finish"):
                        with hou.RedrawBlock() as rb:
                            sop.parm("do_subdivide").set(False)
                            sop.setInput(2, VIEWER.pwd().displayNode())
                            sop.setTemplateFlag(False)
                            sop.setDisplayFlag(True)
                            sop.setRenderFlag(True)
                            sop.setCurrent(True, True)

                        sop.moveToGoodPosition()
                        
                        # RESTORE SELECTION
                        sel = hou.Selection(sop.geometry(), hou.geometryType.Points, sop.evalParm("group"))
                        VIEWER.setPickGeometryType(hou.geometryType.Points)
                        VIEWER.setCurrentState("select")
                        self.set_sop_selection(sop, sel, hou.geometryType.Points)
                else:
                    sop, group, grouptype, empty = self.selection()
                    if sop is not None:
                        with hou.undos.group("Modeler: Lattice Start"):
                            if empty:
                                sel = hou.Selection(self.last_selection_geo, hou.geometryType.Primitives, "!_3d_hidden_primitives")
                                sel.convert(self.last_selection_geo, hou.geometryType.Points)
                                group = sel.selectionString(self.last_selection_geo, force_numeric=True)

                            elif grouptype != hou.geometryType.Points:
                                sel = self.last_selection.freeze()
                                sel.convert(self.last_selection_geo, hou.geometryType.Points)      
                                group = sel.selectionString(self.last_selection_geo, force_numeric=True)

                            cage_sop = sop.createOutputNode("modeler::lattice_cage")
                            cage_sop.parm("group").set(group)

                            lattice_sop = sop.createOutputNode("modeler::lattice")
                            lattice_sop.setPosition(cage_sop.position() + hou.Vector2(3, 0))
                            lattice_sop.setParms({ "group": group, "subdivide": 3 })
                            cage_sop_name = cage_sop.name()
                            lattice_sop.parm("divsx").setExpression( 'ch("../%s/divs") + ch("../%s/extra_divsx")' % (cage_sop_name, cage_sop_name) )
                            lattice_sop.parm("divsy").setExpression( 'ch("../%s/divs") + ch("../%s/extra_divsy")' % (cage_sop_name, cage_sop_name) )
                            lattice_sop.parm("divsz").setExpression( 'ch("../%s/divs") + ch("../%s/extra_divsz")' % (cage_sop_name, cage_sop_name) )
                            lattice_sop.setTemplateFlag(True)

                            edit_sop = cage_sop.createOutputNode("edit", "edit_lattice")
                            lattice_sop.setInput(1, cage_sop)
                            lattice_sop.setInput(2, edit_sop)

                            with hou.RedrawBlock() as rb:
                                edit_sop.setDisplayFlag(True)
                                edit_sop.setRenderFlag(True)
                                edit_sop.setCurrent(True, True)

                                for viewport in VIEWER.viewports():
                                    viewport.settings().displaySet(hou.displaySetType.TemplateModel).setShadedMode(hou.glShadingType.Smooth)

                            VIEWER.setCurrentState("select")
                            VIEWER.setPickGeometryType(hou.geometryType.Points)

                            hou.hscript('oppane -t parmeditor "' + cage_sop.path() + '"')

    def topo_get_src_object(self):
        for i in hou.nodeType(hou.objNodeTypeCategory(), "geo").instances():
            if i.userData("__topo__") is not None:
                return i
        return None

    def topo_get_ref(self, object_to_inject):
        topo_src = self.topo_get_src_object()
        if topo_src is not None and topo_src != object_to_inject:
            topo_src_path = topo_src.path()
            display = object_to_inject.displayNode()

            if display is None:
                om = object_to_inject.createNode("object_merge")
                om.setParms({ "objpath1": topo_src_path, "xformtype": 1 })    
                om.setTemplateFlag(True)
                om.moveToGoodPosition()
                return om
            else:
                for child in object_to_inject.children():
                    if child.type().name() == "object_merge" and child.evalParm("objpath1") == topo_src_path:
                        if not child.isTemplateFlagSet():
                            child.setTemplateFlag(True)
                        return child

                om = object_to_inject.createNode("object_merge")
                om.setParms({ "objpath1": topo_src_path, "xformtype": 1 })    
                om.setTemplateFlag(True)
                om.moveToGoodPosition()
                return om
        else:
            return None

    def topobuild(self):
        sop = self.get_sop()

        with hou.RedrawBlock() as rb:
            # NEW SOP
            if sop is None:
                pwd = VIEWER.pwd()
                if pwd.childTypeCategory() == hou.sopNodeTypeCategory():
                    topobuild_sop = pwd.createNode("topobuild")
                else:
                    pwd = hou.node("/obj").createNode("geo")
                    pwd.moveToGoodPosition()
                    topobuild_sop = pwd.createNode("topobuild")
                    
                topobuild_sop.setCurrent(True, True)

            # EXISTING SOP
            else:
                if sop.type().name() == "topobuild":
                    topobuild_sop = sop
                    topobuild_sop.parm("topobuild_preedit").pressButton()
                else:
                    topobuild_sop = sop.createOutputNode("topobuild")
                    topobuild_sop.setDisplayFlag(True)
                    topobuild_sop.setRenderFlag(True)
                    topobuild_sop.setCurrent(True, True)

                pwd = sop.parent()
        
            # CONNECT OR DISCONNECT TOPOBUILD SECOND INPUT
            topobuild_sop.setInput(1, self.topo_get_ref(pwd))

        if VIEWER.currentState() != "topobuild":
            VIEWER.enterCurrentNodeState()

    def topo_build(self):
        self.topobuild()
        self.run_stock_hotkey_action("h.pane.gview.state.sop.topobuild.build")
    
    def topo_brush(self):
        self.topobuild()
        self.run_stock_hotkey_action("h.pane.gview.state.sop.topobuild.brush")

    def topo_smooth(self):
        self.topobuild()
        self.run_stock_hotkey_action("h.pane.gview.state.sop.topobuild.smooth")

    def topo_skin(self):
        self.topobuild()
        self.run_stock_hotkey_action("h.pane.gview.state.sop.topobuild.skin")

    def topo_project(self):
        topo_src = self.topo_get_src_object()
        
        if topo_src is not None:
            with hou.undos.group("Modeler: Topo Project"):
                sop = self.get_sop()
                if sop is not None and VIEWER.pwd().childTypeCategory() == hou.sopNodeTypeCategory():
                    om = self.topo_get_ref(VIEWER.pwd())
                    ray_sop = sop.createOutputNode("ray", "topo_project1")
                    ray_sop.setParms({ "method": 0, "showguide": False })
                    ray_sop.setInput(1, om)
                    ray_sop.setRenderFlag(True)
                    ray_sop.setDisplayFlag(True)
                    ray_sop.setCurrent(True, True)
                    VIEWER.setCurrentState("select")

    def polygons(self):
        cur_node = VIEWER.currentNode()

        # FINISH STROKES
        if cur_node.type().name() == "stroke":
            with hou.undos.group("Modeler: Toolbar Finish Polygons"):
                topo_strokes_sop = cur_node.createOutputNode("modeler::polygons")
                topo_strokes_sop.setParms({ "fuse_tol": self._topo_fuse_tol, "resample": self._topo_strokes_resample_length })
                topo_strokes_sop.setRenderFlag(True)
                topo_strokes_sop.setDisplayFlag(True)
                topo_strokes_sop.setCurrent(True, True)
        else:
            topo_src = self.topo_get_src_object()

            with hou.undos.group("Modeler: Polygons"):
                if topo_src is None:
                    sop = self.get_sop()
                    if sop is None:
                        pwd = hou.node("/obj").createNode("geo")
                        pwd.moveToGoodPosition()
                        stroke_sop = pwd.createNode("stroke")
                    else:
                        stroke_sop = sop.parent().createNode("stroke")
                        stroke_sop.setInput(1, sop)
                        stroke_sop.moveToGoodPosition()

                    stroke_sop.setParms({ "stroke_radius": 0.0, "stroke_projtype": 3 })
                
                else:
                    sop = self.get_sop()
                    if sop is None:
                        pwd = VIEWER.pwd()

                        if pwd.childTypeCategory() == hou.sopNodeTypeCategory():
                            om = self.topo_get_ref(pwd)
                        
                        else:
                            pwd = hou.node("/obj").createNode("geo")
                            pwd.moveToGoodPosition()
                            om = self.topo_get_ref(pwd)

                        stroke_sop = om.createOutputNode("stroke")

                    else:
                        om = self.topo_get_ref(VIEWER.pwd())
                        stroke_sop = om.createOutputNode("stroke")
                        if om != sop:
                            stroke_sop.setInput(1, sop)

                    stroke_sop.setParms({ "stroke_radius": 0.0, "stroke_projtype": 4 })

            self.activate_sop_with_state(stroke_sop)

    ### TOOLS ###
    def _approve_points_deformation(self):
        sop, group, grouptype, empty = self.selection(empty_type=hou.geometryType.Points)
        if grouptype is not None:
            self.pwd = self.ancestor_object(sop)
            self.sop = sop
            self.sop_geo = self.last_selection_geo
            self.initial_sel = self.last_selection
            self.initial_sel_type = grouptype
            self.initial_items = group
            return True
        else:
            prompt("Geometry object or components must be selected")
        
        return False
    
    def _approve_classic_deformation(self, bend=False, twist=False, taper=False, length_scale=False, tapermode=0):
        sop, group, grouptype, empty = self.selection()
        if sop is not None:
            if empty:
                sel = hou.Selection(self.last_selection_geo, hou.geometryType.Primitives, "!_3d_hidden_primitives")
                sel.convert(self.last_selection_geo, hou.geometryType.Points)
                group = sel.selectionString(self.last_selection_geo, force_numeric=True)

            elif grouptype != hou.geometryType.Points:
                sel = self.last_selection.freeze()
                sel.convert(self.last_selection_geo, hou.geometryType.Points)      
                group = sel.selectionString(self.last_selection_geo, force_numeric=True)

            prompts = [
            "Select start of deformation. Press Enter or Escape to deform the entire geometry.",
            "Select end of deformation. Press Enter or Escape to deform the entire geometry.",
            "Select right direction of deformation. Press Enter or Escape to deform the entire geometry.",
            ]

            positions, directions = self.get_bound_positions_and_directions(sop, group, prompts=prompts)

            if positions is None:
                bound = sop.createOutputNode("bound")
                bound.setParms({ "group": group, "grouptype": 3, "orientedbbox": True })
                bound_geo = bound.geometry()
                start_pos = bound_geo.prim(4).positionAtInterior(0.5, 0.5)
                end_pos = bound_geo.prim(5).positionAtInterior(0.5, 0.5)
                right_pos = bound_geo.prim(1).positionAtInterior(0.5, 0.5)
                bound.destroy()
            else:
                start_pos, end_pos, right_pos = positions

            uo = (end_pos - start_pos)
            right = uo.cross(right_pos - start_pos).cross(uo).normalized()
            length = uo.length()
            uo_norm = uo.normalized()

            bend_sop = sop.createOutputNode("bend")

            bend_sop.setParms({ "group": group, "grouptype": 3, "upvectorcontrol": 3,
                            "enablebend": bend, "enabletwist": twist, "enabletaper": taper, "enablelengthscale": length_scale,
                            "originx": start_pos[0], "originy": start_pos[1], "originz": start_pos[2],
                            "upx": right[0], "upy": right[1], "upz": right[2],
                            "dirx": uo_norm[0], "diry": uo_norm[1], "dirz": uo_norm[2],
                            "length": length, "tapermode": tapermode })

            bend_sop.setDisplayFlag(True)
            bend_sop.setRenderFlag(True)
            bend_sop.setCurrent(True, True)
            
            VIEWER.enterCurrentNodeState()

    def _advanced_deform(self, node_type_name):
        sop, group, grouptype, empty = self.selection()
        if sop is not None:
            if empty:
                sel = hou.Selection(self.last_selection_geo, hou.geometryType.Primitives, "!_3d_hidden_primitives")
                sel.convert(self.last_selection_geo, hou.geometryType.Points)
                group = sel.selectionString(self.last_selection_geo, force_numeric=True)

            elif grouptype != hou.geometryType.Points:
                sel = self.last_selection.freeze()
                sel.convert(self.last_selection_geo, hou.geometryType.Points)      
                group = sel.selectionString(self.last_selection_geo, force_numeric=True)

            sop = sop.createOutputNode(node_type_name)
            sop.parm("group").set(group)
            
            with hou.RedrawBlock() as rb:
                sop.setDisplayFlag(True)
                sop.setRenderFlag(True)
                sop.setCurrent(True, True)
            
            VIEWER.enterCurrentNodeState()
            return sop

    def _select_item_for_flatten(self, prompt, geometry_type):
        pre_higlight = self.sop.isHighlightFlagSet()
        pre_pick_type = VIEWER.pickGeometryType()
        self.sop.setHighlightFlag(False)
        try:
            gs = VIEWER.selectGeometry(prompt, geometry_types=(geometry_type,),
                                                  use_existing_selection=False, quick_select=True,
                                                  consume_selections=False)
            return gs.selections()[0]
        
        except:
            VIEWER.setPickGeometryType(self.initial_sel_type)
            hou.ui.waitUntil(lambda: True)
            VIEWER.setCurrentState("select")
            return None
        
        finally:
            try:
                self.sop.setHighlightFlag(pre_higlight)
                VIEWER.setPickGeometryType(pre_pick_type)
            except:
                pass

    def pack_history(self):
        sop = modeler.get_sop()
        if sop is not None:
            VIEWER.setCurrentState("select")
            
            pwd = VIEWER.pwd()
            children = pwd.children()
            if children:
                ancestors = sop.inputAncestors()
                
                with hou.RedrawBlock() as rb:
                    if ancestors and ancestors[-1].type().name() == "subnet" and not ancestors[-1].isHardLocked():
                        subnet = ancestors[-1]
                        subnet_sop = subnet.displayNode()
                        if subnet_sop is not None:
                            nodes = (sop,) + ancestors[:-1]
                            new_subnet = pwd.collapseIntoSubnet(nodes, pwd.name() + "_edit1")
                            new_subnet = hou.moveNodesTo((new_subnet,), subnet)[0]
                            new_subnet.setInput(0, subnet_sop)
                            new_subnet.moveToGoodPosition()
                            new_subnet.setHardLocked(True)
                            typ = VIEWER.pickGeometryType()
                            VIEWER.setPwd(pwd)
                            sel = hou.Selection(typ)
                            VIEWER.setCurrentGeometrySelection(typ, (subnet_sop,), (sel,))
                    else:
                        new_subnet = pwd.collapseIntoSubnet(children, pwd.name() + "_edit1")
                        new_subnet.setHardLocked(True)
                        s = pwd.collapseIntoSubnet((new_subnet,), pwd.name() + "_history")

    def clean_history(self):
        pwd = VIEWER.pwd()
        if pwd.childTypeCategory() == hou.sopNodeTypeCategory():
            sop = pwd.displayNode()
            if sop is not None:
                items = list(set(pwd.glob("* ^_*")) - set(sop.inputAncestors()) - set([sop]))
                if items:
                    pwd.deleteItems(items)
                    sop.setCurrent(True, True)
                    ui.home_selected()

    def merge_nodes(self, node_type_name="merge"):
        pwd = VIEWER.pwd()
        sel_nodes = hou.selectedNodes()
        nodes = [node for node in (sel_nodes or pwd.children()) if node.type().name()=="geo"]
        # OBJ
        if nodes:
            parent = nodes[0].parent()
            null = parent.createNode("null", "merged_objects1")
            global_center = hou.Vector3()
            for node in nodes:
                sop = node.displayNode()
                if sop is not None:
                    global_center += sop.geometry().boundingBox().center() * node.worldTransform()

                node.setInput(0, null)

            global_center /= len(nodes)
            null.parm("childcomp").set(True)
            null.parmTuple("t").set(global_center)
            null.parm("childcomp").set(False)
            null.setCurrent(True, True)
            parent.layoutChildren( [null] + nodes )
            ui.home_selected()

        # SOP
        elif len(sel_nodes) > 1 and sel_nodes[0].type().category() == hou.sopNodeTypeCategory():
            sop = sel_nodes[0]
            m = sop.createOutputNode(node_type_name)
            for node in sel_nodes[1:]:
                m.setNextInput(node)
            m.moveToGoodPosition()
            m.setDisplayFlag(True)
            m.setRenderFlag(True)
            m.setCurrent(True, True)
            ui.home_selected()

    def switch_nodes(self):
        self.merge_nodes(node_type_name="switch")

    def _create_material_node(self):
        mat_type = self.setup_list[0]
        mat = hou.node("/mat").createNode(mat_type)
        
        if mat_type == "principledshader::2.0":
            mat.setParms({"basecolorr": 0.4, "basecolorg": 0.4, "basecolorb": 0.4, "rough": 0.5, "ior": 1.5})
        
        mat.moveToGoodPosition()
        return mat, mat.path()

    def _get_material_node(self):
        mat_path = hou.ui.selectNode(initial_node=hou.node("/mat/"), title="Select Material Node")
        mat = hou.node(mat_path)
        if mat is not None:
            mat_type = mat.type()
            if mat is not None and mat_type.category() != hou.managerNodeTypeCategory() and not mat_type.isManager():
                return mat, mat_path
        
        return None, None

    def _get_material_sop_and_parms(self, sop):
        if sop.type().name() == "material":
            num = sop.evalParm("num_materials") + 1
            nums = str(num)
            sop.parm("num_materials").set(num)
            return sop, sop.parm("group" + nums), sop.parm("shop_materialpath" + nums)
        
        sop = sop.createOutputNode("material")
        self.activate_sop_with_select_state(sop)
        return sop, sop.parm("group1"), sop.parm("shop_materialpath1")

    def _sample_material(self):
        mat_path = ""
        
        try:
            VIEWER.selectPositions(prompt="Pick face with material.", position_type=hou.positionType.ViewportXY)[0]
            self.run_stock_hotkey_action("h.pane.gview.state.view.set_active_port")
            vp = VIEWER.curViewport()
            pos = VIEWER_WIDGET.mapFromGlobal( qtg.QCursor.pos() )
            x = pos.x()
            y =  VIEWER_WIDGET.height() - pos.y()
        except:
            return None

        node = vp.queryNodeAtPixel(x, y)
        if node is not None:
            prim = vp.queryPrimAtPixel(node, x, y)
            if prim is not None:
                try:
                    mat_path = prim.attribValue("shop_materialpath")
                except hou.OperationFailed:
                    pass

                if not mat_path:
                    pwd = self.ancestor_object(node)
                    mat_path = pwd.evalParm("shop_materialpath")
        try:
            node = hou.node(mat_path)
            node.cookCount()
            return node
        except:
            return None

    def sample_material(self, duplicate=False):
        pwd = VIEWER.pwd()
        child_cat = pwd.childTypeCategory()

        mat_path = ""
        if child_cat == hou.objNodeTypeCategory():
            nodes = [node for node in hou.selectedNodes() if node.type().name() == "geo"]
            if nodes:
                with hou.undos.group("Modeler: Sample Material"):
                    mat = self._sample_material()

                    if mat is None:
                        mat_path = ""
                    elif duplicate:
                        mat_path = hou.copyNodesTo([mat], mat.parent())[0].path()
                    else:
                        mat_path = mat.path()

                    with hou.RedrawBlock() as rb:
                        for node in nodes:
                            node.parm("shop_materialpath").set(mat_path)

                        VIEWER.setCurrentState("select")
                        
                        if duplicate and mat_path:
                            mat = hou.node(mat_path)
                            mat.setCurrent(True, True)
                        else:
                            VIEWER.setPwd(pwd)
        else:
            sop, group, grouptype, empty = self.selection()
            if grouptype == hou.geometryType.Primitives and not empty:
                with hou.undos.group("Modeler: Sample Material"):
                    mat = self._sample_material()
                    
                    with hou.RedrawBlock() as rb:
                        if mat is None:
                            mat_path = ""
                        elif duplicate:
                            mat_path = hou.copyNodesTo([mat], mat.parent())[0].path()
                        else:
                            mat_path = mat.path()

                        sop, gparm, mparm = self._get_material_sop_and_parms(sop)
                        gparm.set(group)
                        mparm.set(mat_path)

                        if duplicate and mat_path:
                            mat = hou.node(mat_path)
                            mat.setCurrent(True, True)

            else:
                prompt("Select at least one polygon and try again.")

    def sample_material_copy(self):
        self.sample_material(duplicate=True)

    def assign_material(self, existing=False):
        pwd = VIEWER.pwd()
        child_cat = pwd.childTypeCategory()

        if child_cat == hou.objNodeTypeCategory():
            nodes = [ node for node in hou.selectedNodes() if node.type().name() == "geo" ]
            if nodes:
                with hou.undos.group("Modeler: Assign Material"):
                    if existing:
                        mat, mat_path = self._get_material_node()
                    else:    
                        mat, mat_path = self._create_material_node()

                    if mat is not None:
                        # UPDATE SCENE VIEWER
                        for node in nodes:
                            node.parm("shop_materialpath").set(mat_path)

                        if not existing:
                            mat.setCurrent(True, True)

        else:
            sop, group, grouptype, empty = self.selection()
            if grouptype == hou.geometryType.Primitives and not empty:
                with hou.undos.group("Modeler: Assign Material"):
                    if existing:
                        mat, mat_path = self._get_material_node()
                    else:    
                        mat, mat_path = self._create_material_node()

                    if mat is not None:
                        sop, gparm, mparm = self._get_material_sop_and_parms(sop)
                        gparm.set(group)
                        mparm.set(mat_path)
                        
                        if not existing:
                            mat.setCurrent(True, True)

                        VIEWER.setCurrentState("select")
                        self.clear_sop_selection()
            else:
                prompt("Select at least one polygon and try again.")

    def clear_materials(self):
        sop, group, grouptype, empty = self.selection(activate_one_object=False)
        if grouptype == hou.geometryType.Primitives and not empty and self.last_selection_geo.findPrimAttrib("shop_materialpath") is not None:
            with hou.undos.group("Modeler: Clear Materials"):
                sop = sop.createOutputNode("attribwrangle", "clear_material1")
                sop.setParms({ "group": group, "class": 1, "snippet": 's@shop_materialpath = "";' })
                self.activate_sop_with_select_state(sop)

        elif sop is not None:
            prompt("Select at least one polygon with material and try again.")

        else:
            if group is not None:
                with hou.undos.group("Modeler: Clear Materials"):
                    for node in group:
                        parm = node.parm("shop_materialpath")
                        if parm is not None:
                            parm.set("")
            else:
                prompt("Select at least one object with material and try again.")

    def get_material(self):
        self.assign_material(existing=True)

    def select_material_node(self):
        sop, group, grouptype, empty = self.selection(activate_one_object=False)
        if grouptype == hou.geometryType.Primitives and not empty and self.last_selection_geo.findPrimAttrib("shop_materialpath") is not None:
            mat_path = self.last_selection.prims(self.last_selection_geo)[0].stringAttribValue("shop_materialpath")
            if mat_path:
                with hou.undos.group("Modeler: Select Material Node"):
                    self.clear_sop_selection()
                    mat = hou.node(mat_path)
                    mat.setCurrent(True, True)

        elif sop is not None:
            prompt("Select at least one polygon with material and try again.")

        else:
            if group is not None and len(group) == 1:
                mat_path = group[0].evalParm("shop_materialpath")
                if mat_path:
                    hou.node(mat_path).setCurrent(True, True)
            else:
                prompt("Select one object with material and try again.")

    def _flatten(self, o, d):
        VIEWER.setCurrentState("select")
        VIEWER.setCurrentGeometrySelection(self.initial_sel_type, (self.sop,), (self.initial_sel,))
        sop = self.sop.createOutputNode("xformaxis", "flatten1")
        
        if self.initial_sel_type == hou.geometryType.Primitives:
            grouptype = 4
        elif self.initial_sel_type == hou.geometryType.Edges:
            grouptype = 2
        else:
            grouptype = 3

        sop.setParms({"group": self.initial_items, "grouptype": grouptype, "scale": 0.0})
        sop.parmTuple("orig").set(o)
        sop.parmTuple("dir").set(d)

        with hou.RedrawBlock() as rb:
            sop.setDisplayFlag(True)
            sop.setHighlightFlag(True)
            sop.setRenderFlag(True)
            sop.setCurrent(True, True)
            VIEWER.enterCurrentNodeState()
            hou.ui.waitUntil(lambda: True)
            VIEWER.setCurrentState("select")

    def _arrow_flatten(self, axis, direction):
        with hou.undos.group("Modeler: Flatten By Screen"):
            if self._approve_points_deformation():
                if self.initial_sel_type == hou.geometryType.Vertices:
                    sop = VIEWER.currentNode()
                    geo = sop.geometry()
                    
                    try:
                        sel = VIEWER.currentGeometrySelection().selections()[0]
                    except:
                        try:
                            sel = geo.selection()
                        except:
                            return

                    if sel is not None and sel.selectionType() == hou.geometryType.Vertices:
                        items = sel.selectionString(geo, force_numeric=True)

                        if axis == 0:
                            axis_char = "x"
                        else:
                            axis_char = "y"

                        if direction < 0:
                            big = 999999
                            op_char = "<"
                        else:
                            big = 0
                            op_char = ">"

                        aw_snippet = """int vtxs[] = expandvertexgroup(0, "%s");
vector uv;
float target = %f;
foreach(int vtx; vtxs)
{
uv = vertex(0, "uv", vtx)[0];
if(uv.%s %s target)
    target = uv.%s;
}

int prim, i;
foreach(int vtx; vtxs)
{
prim = vertexprim(0, vtx);
uv = vertex(0, "uv", vtx);
uv.%s = target;
i = vertexprimindex(0, vtx);
setvertexattrib(0, "uv", prim, i, uv);
}""" % (items, big, axis_char, op_char, axis_char, axis_char)

                        sop = sop.createOutputNode("attribwrangle", "flatten_uvs1")
                        sop.setParms({ "class": 0, "snippet": aw_snippet })

                        with hou.RedrawBlock() as rb:
                            sop.setDisplayFlag(True)
                            sop.setRenderFlag(True)
                            sop.setCurrent(True, True)
                            VIEWER.setPickGeometryType(hou.geometryType.Vertices)
                            VIEWER.setCurrentState("select")
                            VIEWER.setCurrentGeometrySelection(hou.geometryType.Vertices, (sop,), (sel,))

                else:
                    o = self.sop_selection_center(self.sop, self.initial_sel)
                    
                    self.sop_geo = self.sop_geo.freeze()
                    self.sop_geo.transform(self.pwd.worldTransform())

                    if self.initial_sel_type == hou.geometryType.Points:
                        bb = self.sop_geo.pointBoundingBox(self.initial_items)
                    
                    elif self.initial_sel_type == hou.geometryType.Primitives:
                        bb = self.sop_geo.primBoundingBox(self.initial_items)
                    
                    else:
                        sel = self.initial_sel.freeze()
                        sel.convert(self.sop_geo, hou.geometryType.Points)
                        bb = self.sop_geo.pointBoundingBox(sel.selectionString(self.sop_geo, force_numeric=True))

                    o = bb.center()
                    
                    d = get_hvd(VIEWER, True)[axis]
                    d_ = get_hvd(VIEWER, False)[axis]

                    if direction < 0:
                        m = bb.minvec()
                        M = bb.maxvec()
                    else:
                        m = bb.maxvec()
                        M = bb.minvec()

                    if d[0]:
                        if d_[0] > 0:
                            o = hou.Vector3(m[0], o[1], o[2]) 
                        else:
                            o = hou.Vector3(M[0], o[1], o[2]) 
                    
                    elif d[1]:
                        if d_[1] > 0:
                            o = hou.Vector3(o[0], m[1], o[2]) 
                        else:
                            o = hou.Vector3(o[0], M[1], o[2]) 
                                
                    else:
                        if d_[2] > 0:
                            o = hou.Vector3(o[0], o[1], m[2]) 
                        else:
                            o = hou.Vector3(o[0], o[1], M[2]) 
                                
                    o *= self.pwd.worldTransform().inverted()
                    d *= self.pwd.worldTransform().transposed()
                    
                    self._flatten(o, d)

    def flatten_by_face_normal(self):
        with hou.undos.group("Modeler: Flatten By Face Normal"):
            if self._approve_points_deformation():
                sel = self._select_item_for_flatten("Select a face.", hou.geometryType.Primitives)
                if sel is not None:
                    face = sel.prims(self.sop_geo)[0]
                    sel = self._select_item_for_flatten("Select an origin point.", hou.geometryType.Points)
                    if sel is not None:
                        self._flatten(sel.points(self.sop_geo)[0].position(), face.normal())

    def flatten_auto(self):
        with hou.undos.group("Modeler: Flatten Auto"):
            if self._approve_points_deformation():
                n, c = modeler.get_selection_normal_and_center(self.sop, self.initial_sel, self.sop_geo)
                n = hou.Vector3(0.0, 0.0, 1.0) * (hou.Vector3(0.0, 0.0, 1.0).matrixToRotateTo(n) * hou.hmath.buildTranslate(c)).inverted().transposed()
                self._flatten(c, n)

    def flatten_by_edge(self):
        if self._approve_points_deformation():
            sel = self._select_item_for_flatten("Select an edge.", hou.geometryType.Edges)
            if sel is not None:
                edge = sel.edges(self.sop_geo)[0]
                pt1, pt2 = edge.points()
                pt1_pos = pt1.position()
                pt2_pos = pt2.position()
                edge_vec = pt2_pos - pt1_pos

                edge_prims = edge.prims()
                if len(edge_prims) == 1:
                    normal = edge_prims[0].normal()
                else:
                    if self.initial_sel_type == hou.geometryType.Primitives:
                        prims_str = "{} {}".format(edge_prims[0].number(), edge_prims[1].number())
                        sel1 = hou.Selection(self.sop_geo, hou.geometryType.Primitives, prims_str)
                        sel1.combine(self.sop_geo, self.initial_sel, hou.pickModifier.Intersect)
                        count = sel1.numSelected()
                        if count == 1:
                            normal = sel1.prims(self.sop_geo)[0].normal()
                        else:
                            normal = (edge_prims[0].normal() + edge_prims[1].normal()) / 2.0
                    else:
                        sel = self._select_item_for_flatten("Select support face or press Escape to use an average of edge faces", hou.geometryType.Primitives)
                        if sel is None:
                            normal = (edge_prims[0].normal() + edge_prims[1].normal()) / 2.0
                        else:
                            normal = sel.prims(self.sop_geo)[0].normal()

                d = edge_vec.cross(normal)
                d = d.cross(edge_vec)
                o = (pt1_pos + pt2_pos) / 2.0
                self._flatten(o, d)

    def flatten_by_edge_dir(self):
        if self._approve_points_deformation():
            sel = self._select_item_for_flatten("Select an edge.", hou.geometryType.Edges)
            if sel is not None:
                edge = sel.edges(self.sop_geo)[0]
                pt1, pt2 = edge.points()
                pt1_pos = pt1.position()
                pt2_pos = pt2.position()
                d = pt2_pos - pt1_pos

                sel = self._select_item_for_flatten("Select an orgin point.", hou.geometryType.Points)
                if sel is None:
                    o = (pt1_pos + pt2_pos) / 2.0
                else:
                    o = sel.points(self.sop_geo)[0].position()

                self._flatten(o, d)

    def flatten_left(self):
        self._arrow_flatten(0, -1)

    def flatten_right(self):
        self._arrow_flatten(0, 1)

    def flatten_up(self):
        self._arrow_flatten(1, 1)

    def flatten_down(self):
        self._arrow_flatten(1, -1)

    def twist(self):
        self._approve_classic_deformation(twist=True)

    def taper(self):
        self._approve_classic_deformation(taper=True)

    def bend(self):
        self._approve_classic_deformation(bend=True)

    def length_scale(self):
        self._approve_classic_deformation(length_scale=True)

    def size(self):
        sop = self._advanced_deform("modeler::size_deform")
        if sop is not None:
            sop.parm("init").pressButton()

    def falloff_xform(self):
        sop, group, grouptype, empty = modeler.selection()
        if grouptype is not None:
            if empty:
                group = "!_3d_hidden_primitives"
                faces = True

            elif grouptype == hou.geometryType.Primitives:
                faces = True
            
            elif grouptype == hou.geometryType.Points:
                faces = False
            
            elif grouptype == hou.geometryType.Edges:
                sel = modeler.last_selection.freeze()
                sel.convert(modeler.last_selection_geo, hou.geometryType.Points)
                group = sel.selectionString(modeler.last_selection_geo, force_numeric=True)
                faces = False
            else:
                return

            sop = sop.createOutputNode("modeler::falloff_xform")
            sop.setParms({ "group": group, "is_prims": faces })
            
            with hou.RedrawBlock() as rb:
                sop.setDisplayFlag(True)
                sop.setRenderFlag(True)
                sop.setCurrent(True, True)
            
            VIEWER.enterCurrentNodeState()

    def mountain(self):
        sop = self._advanced_deform("mountain::2.0")
        sop.setParms({ "height": 0.1, "elementsize": 0.5 })

    def is_lattice_cage(self, sop):
        return sop.parent().userData("lattice") is not None

    def is_click(self, old_x, old_y, new_x, new_y, old_time):
         return (time.time() - old_time) < 0.3 and abs(new_x - old_x) < hou.ui.scaledSize(8) and abs(new_y - old_y) < hou.ui.scaledSize(8)

    def hit_info(self, state_origin, state_dir, mouse_x, mouse_y, viewport, local=True):
        # GEO IS BEHIND X, Y
        hit_node = viewport.queryNodeAtPixel(int(mouse_x), int(mouse_y))
        if hit_node is not None and not hit_node.isInsideLockedHDA():
            # NODE HAS GEO
            hit_geo = hit_node.geometry()
            
            if hit_geo is not None:
                # GET HIT PWD AND XFORM
                hit_pwd = hit_node.creator()

                hit_xform = hit_pwd.worldTransform()

                # GET CURRENT PWD AND XFORM
                this_node = VIEWER.currentNode()
                this_pwd = this_node.creator()
                this_xform = this_pwd.worldTransform()

                # CONVERT STATE O\D TO WORLD SPACE DATA
                world_cursor_origin = state_origin * this_xform
                world_cursor_dir = state_dir * this_xform.inverted().transposed()

                # CONVERT WORLD SPACE STATE O\D TO HIT GEO O\D
                hit_cursor_origin = world_cursor_origin * hit_xform.inverted()
                hit_cursor_dir = world_cursor_dir * hit_xform.transposed()

                # TMP DATA
                hit_pos = hou.Vector3()
                hit_normal = hou.Vector3()
                uvw = hou.Vector3()
                
                # TEST INTERSECT
                intersected_prim_number = hit_geo.intersect(hit_cursor_origin, hit_cursor_dir, hit_pos, hit_normal, uvw)
                
                # SOME PRIM IS BEHIND X, Y
                if intersected_prim_number > -1:
                    prim = hit_geo.prim(intersected_prim_number)
                    prim_center = prim.boundingBox().center()
                    points = prim.points()
                    points_ = points + [ points[0] ]
                    nearest_snap_D = hit_pos.distanceTo(prim_center)        
                    nearest_snap = prim_center
                    nearest_edge_D = 9999.9999
                    nearest_edge = None
                    nearest_edge_pos1 = None
                    nearest_edge_pos2 = None
                    edge_positions = []
                    positions = hou.Vector3()

                    for i in range(len(points_)-1):
                        pos1 = points_[i].position()
                        pos2 = points_[i+1].position()

                        positions += pos1

                        # TEST POINT
                        d = hit_pos.distanceTo(pos1)
                        if d < nearest_snap_D:
                            nearest_snap_D = d
                            nearest_snap = pos1

                        edge_positions.append((pos1 * hit_xform * this_xform.inverted(), pos2 * hit_xform * this_xform.inverted()))

                        # TEST EDGE MIDPOS
                        midpos = (pos1 + pos2) / 2.0
                        d = hit_pos.distanceTo(midpos)
                        if d < nearest_edge_D:
                            nearest_edge_D = d
                            nearest_edge = midpos
                            nearest_edge_pos1 = pos1
                            nearest_edge_pos2 = pos2 

                    # EDGE IS CLOSER
                    if nearest_edge.distanceTo(hit_pos) < nearest_snap.distanceTo(hit_pos):
                        nearest_snap = nearest_edge

                    hit_normal = hit_normal * hit_xform.inverted().transposed() * this_xform.transposed()
                    hit_pos = hit_pos * hit_xform * this_xform.inverted()
                    prim_center = prim_center * hit_xform * this_xform.inverted()
                    nearest_snap = nearest_snap * hit_xform * this_xform.inverted()
                    nearest_edge = nearest_edge * hit_xform * this_xform.inverted()

                    kwargs = { "hit_pos": hit_pos, "prim": prim, "prim_center": prim_center, "prim_normal": hit_normal, "edge_positions": edge_positions,
                               "nearest_pos": nearest_snap, "nearest_midpos": nearest_edge, "nearest_midpos_positions": (nearest_edge_pos1, nearest_edge_pos2) }

                    return kwargs

        return None

    def snap_value(self, value, step):
        return round(value / step) * step

    def run_stock_hotkey_action(self, cmd):
        commands_to_restore = []

        for conflict in hou.hotkeys.findConflicts(None, "Print"):
            hou.hotkeys.removeAssignment(conflict, "Print")
            commands_to_restore.append(conflict)

        hou.hotkeys.addAssignment(cmd, "Print")

        mw = hou.qt.mainWindow()
        VIEWER_WIDGET.removeEventFilter(modeler)
        qtest.keyPress(mw, qt.Key_Print, qt.NoModifier)
        hou.ui.waitUntil(lambda: True)
        qtest.keyRelease(mw, qt.Key_Print, qt.NoModifier)
        VIEWER_WIDGET.installEventFilter(modeler)

        hou.hotkeys.removeAssignment(cmd, "Print")
        for cmd in commands_to_restore:
            hou.hotkeys.addAssignment(cmd, "Print")


    def intersect_plane(self, plane_point, plane_normal, line_origin, line_dir):
        try:
            return hou.hmath.intersectPlane(plane_point, plane_normal, line_origin, line_dir)
        except TypeError:
            return line_origin - line_dir * (line_origin - plane_point).dot(line_dir)

    def activate_sop_with_select_state(self, sop, highlight=True):
        sop.setCurrent(True, True)
        sop.setDisplayFlag(True)
        sop.setRenderFlag(True)
        sop.setHighlightFlag(highlight)
        VIEWER.setCurrentState("select")

    def activate_sop_with_state(self, sop, highlight=True):
        with hou.RedrawBlock() as rb:
            sop.setCurrent(True, True)
            sop.setDisplayFlag(True)
            sop.setRenderFlag(True)
            sop.setHighlightFlag(highlight)
        VIEWER.enterCurrentNodeState()

    def get_cplane_xform_if_visible(self):
        if VIEWER.constructionPlane().isVisible():
            cplane = VIEWER.constructionPlane()
            xform = cplane.transform()
            cplane.setIsVisible(False)
            return xform

        return None

    def select_by_mask(self, mask):
        if VIEWER.isGroupPicking() and VIEWER.groupListMask() == mask:
            VIEWER.setGroupPicking(False)
        else:
            VIEWER.setGroupListMask(mask)
            VIEWER.setGroupPicking(True)
            VIEWER.setGroupListColoringGeometry(False)
            VIEWER.setGroupListType(hou.groupListType.Primitives)
            VIEWER.setSelectionMode(hou.selectionMode.Geometry)
            if VIEWER.currentState() != "scriptselect": 
                VIEWER.setCurrentState("select")
            VIEWER.setPickGeometryType(hou.geometryType.Primitives)

    def pick_component(self, sel_type, prompt, quick=True):
        initial_pick_type = VIEWER.pickGeometryType()
        
        try:
            gs = VIEWER.selectGeometry(prompt, geometry_types=(sel_type,), use_existing_selection=False, quick_select=quick, consume_selections=False)
            if gs.mergedSelectionString():
                sel = gs.selections()[0]
                if sel_type == hou.geometryType.Points:
                    return sel.points( gs.nodes()[0].geometry() )
                
                elif sel_type == hou.geometryType.Edges:
                    return sel.edges( gs.nodes()[0].geometry() )

                elif sel_type == hou.geometryType.Primitives:
                    return sel.prims( gs.nodes()[0].geometry() )

            return []
        
        except:
            return []
        
        finally:
            VIEWER.setPickGeometryType(initial_pick_type)

    def get_sop(self, set_current=True):
        cur_node = VIEWER.currentNode()

        if cur_node.type().category() == hou.sopNodeTypeCategory():
            display = cur_node.parent().displayNode()
            display.setCurrent(True, True)
            return display
        else:
            sel = hou.selectedNodes()
            if sel and sel[0].type().childTypeCategory() == hou.sopNodeTypeCategory():
                sop = sel[0].displayNode()
                if sop is not None:
                    if set_current:
                        sop.setCurrent(True, True)
                        hou.ui.waitUntil(lambda: True)
                return sop
        
        return None

    def get_object(self, prompt="Select Object", use_existing_selection=False, return_to_current_node=True):
        cur_node = VIEWER.currentNode()
        with hou.undos.disabler():
            try:
                hou.ui.waitUntil(lambda: True)
                objects = VIEWER.selectObjects(prompt=prompt, quick_select=True, use_existing_selection=use_existing_selection, allow_multisel=False, allowed_types=["geo", "subnet"])
                if objects:
                    obj = objects[0]
                    display = obj.displayNode()
                    if display is not None:
                        return obj, display
            
            except hou.OperationInterrupted:
                VIEWER.setCurrentState("select")
                return None, None
            
            finally:
                if return_to_current_node:
                    VIEWER.setCurrentNode(cur_node)
                else:
                    hou.clearAllSelected()
        
                VIEWER.setCurrentState("select")
            
            return None, None

    def is_all_selected(self, sel, geo):
        sel_type = sel.selectionType()
        
        # NOT ISOLATED POLYGONS
        if geo.findPrimGroup("_3d_hidden_primitives") is None:
            if sel_type == hou.geometryType.Primitives:
                return sel.numSelected() == geo.intrinsicValue("primitivecount")
            elif sel_type == hou.geometryType.Points:
                return sel.numSelected() == geo.intrinsicValue("pointcount")
            else:
                sel = sel.freeze()
                sel.convert(geo, hou.geometryType.Points)
                return sel.numSelected() == geo.intrinsicValue("pointcount")
        
        # ISOLATED POLYGONS
        else:
            unisolated_faces_sel = hou.Selection(geo, hou.geometryType.Primitives, "!_3d_hidden_primitives")
            if sel_type == hou.geometryType.Primitives:
                sel = sel.freeze()
                sel.combine(geo, unisolated_faces_sel, hou.pickModifier.Toggle)
                return not sel.numSelected()
            else:
                unisolated_faces_sel.convert(geo, sel_type)
                unisolated_faces_sel.combine(geo, sel, hou.pickModifier.Toggle)
                return not unisolated_faces_sel.numSelected()
        return False

    def sop_selection_center(self, sop, sel, xform=hou.hmath.identityTransform()):
        typ = sel.selectionType()
        geo = sop.geometry()
        
        if typ == hou.geometryType.Points:
            return geo.pointBoundingBox(sel.selectionString(geo)).center() * xform
        
        elif typ == hou.geometryType.Primitives:
            return geo.primBoundingBox(sel.selectionString(geo)).center() * xform
        
        else:
            sel = sel.freeze()
            sel.convert(geo, hou.geometryType.Points)
            return geo.pointBoundingBox(sel.selectionString(geo)).center() * xform

    def get_bound_positions_and_directions(self, sop, points, prompts):
        with hou.undos.disabler():
            initial_sel_type = VIEWER.pickGeometryType()
            
            geo = sop.geometry()
            obb = geo.orientedPointBoundingBox(points)
            
            t = obb.center()
            r = obb.rotation().inverted().extractRotates()
            size = obb.sizevec()
            delta = max(size) / 20.0
            new_size = [ size[0] + delta, size[1] + delta, size[2] + delta ]

            box = sop.parent().createNode("box")
            box.moveToGoodPosition()
            box.parmTuple("t").set(t)
            box.parmTuple("r").set(r)
            box.parmTuple("size").set(new_size)
            box.setCurrent(True, True)

            box_geo = box.geometry()
            directions = []
            positions = []
            for i in range(len(prompts)):
                try:
                    gs = VIEWER.selectGeometry(prompts[i], geometry_types=(hou.geometryType.Primitives,),
                                                     quick_select = True, use_existing_selection=False, consume_selections=True)
                except hou.OperationInterrupted:
                    VIEWER.setPickGeometryType(initial_sel_type)
                    try:
                        box.destroy()
                    except hou.ObjectWasDeleted:
                        pass
                    return None, None

                try:
                    box.cookCount()
                except hou.ObjectWasDeleted:
                    return None, None

                selections = gs.selections()
                if selections:
                    face = selections[0].prims(box_geo)[0]
                    position = face.positionAtInterior(0.5, 0.5)
                    direction = face.normal()
                    positions.append(position)
                    directions.append(direction)
                else:
                    VIEWER.setPickGeometryType(initial_sel_type)
                    box.destroy()
                    return None, None

            VIEWER.setPickGeometryType(initial_sel_type)
            box.destroy()
            return (positions, directions)

    def get_selection_normal_and_center(self, sop, sel, geo):
        with hou.undos.disabler():
            g = sop.createOutputNode("modeler::group_normal")
            typ = sel.selectionType()
            if typ == hou.geometryType.Primitives:
                grouptype = 0
            elif typ == hou.geometryType.Points:
                grouptype = 1
            else:
                grouptype = 2

            g.setParms({ "group": sel.selectionString(geo), "grouptype": grouptype })
            ggeo = g.geometry()
            n = hou.Vector3(ggeo.attribValue("N"))
            c = hou.Vector3(ggeo.attribValue("center"))
            g.destroy()
            return n, c

    def get_selection_center_and_rotation(self):
        if VIEWER.pwd().childTypeCategory() == hou.sopNodeTypeCategory():
            sop, group, grouptype, empty = self.selection()
            # sop, sel, pwd = sop_selection()
            if sop is not None:
                # geo = sop.geometry()
                if not self.is_all_selected(sel, self.last_selection_geo):
                    z, center = self.get_selection_normal_and_center(sop, sel, geo)
                    world_xform = self.ancestor_object(sop).worldTransform()
                    
                    initial_sel_type = VIEWER.pickGeometryType()

                    try:
                        gs = VIEWER.selectGeometry("To rotate geometry, select the nearest Z-axis. Press Escape to just translate.",
                                                         consume_selections=False, geometry_types=(hou.geometryType.Edges,), use_existing_selection=False, quick_select=True)
                        
                        pt1, pt2 = gs.selections()[0].edges(geo)[0].points()
                        pos1 = pt1.position()
                        pos2 = pt2.position()
                        y = (pos2 - pos1).normalized()

                    except:
                        return center * world_xform, (0.0, 0.0, 0.0)

                    VIEWER.setPickGeometryType(initial_sel_type)
                    
                    world_xform_inverted_transposed = world_xform.inverted().transposed()

                    global_y = y * world_xform_inverted_transposed
                    global_z = z * world_xform_inverted_transposed
                    global_x = global_z.cross(global_y)
                    xform =  hou.Matrix3((global_x, global_z, global_y))

                    return center * world_xform, xform.extractRotates()

        return None, None

    def get_edit_sop(self, sop):
        if sop.type().name() == "edit":
            sop.parm("apply").pressButton()
            sop.setParms({ "slideonsurface": False, "switcher1": 0, "modeswitcher1": 0,
                           "px": 0.0, "py": 0.0, "pz": 0.0, "prx": 0.0, "pry": 0.0, "prz": 0.0 })

        else:
            sop = sop.createOutputNode("edit")

        return sop

    def xform(self, op=0):
        state = VIEWER.currentState()
        node = VIEWER.currentNode()

        with hou.RedrawBlock() as rb:
            # UV EDIT
            if VIEWER.curViewport().type() == hou.geometryViewportType.UV:
                sop, group, grouptype, empty = selection()
                if grouptype is not None:
                    if op == 0:
                        self.run_stock_hotkey_action("h.pane.gview.state.new_move")
                    elif op == 1:
                        self.run_stock_hotkey_action("h.pane.gview.state.new_rotate")
                    else:
                        self.run_stock_hotkey_action("h.pane.gview.state.new_scale")
                
            # EDIT
            elif state == "edit" and node.type().name() == "edit":
                if node.evalParm("xformspace"):
                    node.parm("apply").pressButton()
                    VIEWER.setCurrentState("select")
                    node.parm("xformspace").set(0)
                
                symmetry.setup_edit_sop(node)

                if op == 0:
                    VIEWER.enterTranslateToolState()
                elif op == 1:
                    VIEWER.enterRotateToolState()
                else:
                    VIEWER.enterScaleToolState()

            # OTHER STATES
            elif state in ( "polyextrude::2.0", "copyxform", "xform", "modeler::shift",
                            "modeler::array", "modeler::falloff_xform", "modeler::boolean") or ( state != "select" and not len(VIEWER.currentNode().inputs())):
                
                VIEWER.enterCurrentNodeState()

                if op == 0:
                    self.run_stock_hotkey_action("h.pane.gview.state.new_move")
                elif op == 1:
                    self.run_stock_hotkey_action("h.pane.gview.state.new_rotate")
                else:
                    self.run_stock_hotkey_action("h.pane.gview.state.new_scale")

            # STANDARD TRANSFORM
            else:
                sop, group, grouptype, empty = self.selection(activate_one_object=False)

                # SOPS
                if sop is not None:
                    self.set_sop_selection(sop, self.last_selection, VIEWER.pickGeometryType())

                    if op == 0:
                        VIEWER.enterTranslateToolState()
                    elif op == 1:
                        VIEWER.enterRotateToolState()
                    else:
                        VIEWER.enterScaleToolState()

                    hou.ui.waitUntil(lambda: True)
                    sop = VIEWER.currentNode()
                    symmetry.setup_edit_sop(sop)
                    sop.parm("xformspace").set(0)
                
                # OBJ
                elif group is not None:
                    if op == 0:
                        self.run_stock_hotkey_action("h.pane.gview.state.new_move")
                    elif op == 1:
                        self.run_stock_hotkey_action("h.pane.gview.state.new_rotate")
                    else:
                        self.run_stock_hotkey_action("h.pane.gview.state.new_scale")

            show_handles(VIEWER, True)

    def whole_selection(self, node, selection_type):
        geo = node.geometry()
        sel = hou.Selection(geo, hou.geometryType.Primitives, "!_3d_hidden_primitives")
        if selection_type != hou.geometryType.Primitives:
            sel = sel.freeze()
            sel.convert(geo, selection_type)
        return sel

    def set_sop_selection(self, sop, selection, selection_type):
        scripted = VIEWER.currentState() == "scriptselect"
        if not scripted:
            VIEWER.setCurrentState("select")
        
        try:
            VIEWER.setCurrentGeometrySelection(selection_type, (sop,), (selection,))

        except hou.ObjectWasDeleted:
            hou.ui.waitUntil(lambda: True)
            VIEWER.setCurrentGeometrySelection(selection_type, (VIEWER.currentNode(),), (selection,))

    def selection(self, activate_one_object=True, empty_type=hou.geometryType.Primitives):
        # GEOMETRY
        if VIEWER.selectionMode() == hou.selectionMode.Geometry:
            state = VIEWER.currentState()
            cur_node = VIEWER.currentNode()
            
            self.last_selection_was_scripted = (state == "scriptselect")

            if state == "sopview" or state == "topobuild":
                VIEWER.setCurrentState("select")
                state = "select"

            # SELECT STATE
            if state == "select" or state == "scriptselect":
                gs = VIEWER.currentGeometrySelection()
                if gs is not None:
                    self.last_selection = gs.selections()
                    if self.last_selection:
                        self.last_selection = self.last_selection[0]
                        sel_type = self.last_selection.selectionType()
                        
                        if self.last_selection_was_scripted:
                            sop = cur_node.parent().displayNode()
                            self.last_selection_geo = sop.geometry()
                        else:
                            sop = cur_node
                            self.last_selection_geo = cur_node.geometry()
                        
                        return sop, self.last_selection.selectionString(self.last_selection_geo, asterisk_to_select_all=True, force_numeric=True), sel_type, False

            # OTHER STATES HIGHLIGHTED
            else:
                try:
                    if cur_node.infoTree().branches()["SOP Info"].rows()[0][0][0] == "H":
                        self.last_selection_geo = cur_node.geometry()
                        self.last_selection = self.last_selection_geo.selection()
                        sel_type = self.last_selection.selectionType()
                        
                        with hou.RedrawBlock() as rb:
                            VIEWER.setCurrentState("select")

                            try:
                                cur_node.cookCount()

                            except hou.ObjectWasDeleted:
                                hou.ui.waitUntil(lambda: True)
                                cur_node = VIEWER.currentNode()
                                self.last_selection_geo = cur_node.geometry()


                            if sel_type != VIEWER.pickGeometryType():
                                VIEWER.setPickGeometryType(sel_type)
                                hou.ui.waitUntil(lambda: True)
                            
                            return (cur_node, self.last_selection.selectionString(self.last_selection_geo, asterisk_to_select_all=True, force_numeric=True), sel_type, False)
                            
                except KeyError:
                    pass

            # OTHER STATES -> ACTIVATE SELECTION STATE
            if state != "select":
                VIEWER.setCurrentState("select")


            pick_type = VIEWER.pickGeometryType()
            self.last_selection_geo = cur_node.geometry()
            self.last_selection = hou.Selection(self.last_selection_geo, hou.geometryType.Primitives, "!_3d_hidden_primitives")
            if pick_type != empty_type:
                self.last_selection = self.last_selection.freeze()
                self.last_selection.convert(self.last_selection_geo, empty_type)

            return (cur_node, self.last_selection.selectionString(self.last_selection_geo, asterisk_to_select_all=True, force_numeric=True), empty_type, True)

        # OBJECTS
        else:
            self.last_selection_was_scripted = False
            geo_objects = hou.selectedNodes()
            if geo_objects:
                if activate_one_object and len(geo_objects) == 1 and geo_objects[0].type() == hou.nodeType(hou.objNodeTypeCategory(), "geo"):
                    display = geo_objects[0].displayNode()
                    if display is not None:
                        with hou.RedrawBlock() as rb:
                            display.setCurrent(True, True)
                            hou.ui.waitUntil(lambda: True)
                            pick_type = VIEWER.pickGeometryType()
                            self.last_selection_geo = display.geometry()
                            self.last_selection = hou.Selection(self.last_selection_geo, hou.geometryType.Primitives, "!_3d_hidden_primitives")
                            if pick_type != empty_type:
                                self.last_selection = self.last_selection.freeze()
                                self.last_selection.convert(self.last_selection_geo, empty_type)

                            return (display, self.last_selection.selectionString(self.last_selection_geo, asterisk_to_select_all=True, force_numeric=True), empty_type, True)

                return None, geo_objects, None, False

        return None, None, None, True

    def clear_sop_selection(self):
        sel_type = VIEWER.pickGeometryType()
        sel = hou.Selection(sel_type)
        with hou.undos.disabler():
            VIEWER.setCurrentGeometrySelection(sel_type, (VIEWER.currentNode(),), (sel,))

    def ancestor_object(self, node):
        parent = node.parent()
        cat = parent.type().category()
        while parent is not None and (cat == hou.objNodeTypeCategory() or cat == hou.sopNodeTypeCategory()):
            node = parent
            parent = parent.parent()
            cat = parent.type().category()
        return node

    def merge_with_object(self, src_sop, src_obj, dst_sop, dst_obj, merge_node_type, merge_node_parms={}):
        with hou.RedrawBlock() as rb:
            src_nodes = (src_sop,) + src_sop.inputAncestors()
            
            m = dst_sop.createOutputNode(merge_node_type)
            new_nodes = hou.moveNodesTo(src_nodes, dst_obj)

            xform = src_obj.worldTransform() * dst_obj.worldTransform().inverted()

            t = xform.extractTranslates()
            r = xform.extractRotates()
            s = xform.extractScales()
            sh = xform.extractShears()

            x = new_nodes[0].createOutputNode("xform")
            x.parmTuple("t").set(t)
            x.parmTuple("r").set(r)
            x.parmTuple("s").set(s)
            x.parmTuple("shear").set(sh)

            m.setParms(merge_node_parms)
            m.setInput(1, x)
            m.setCurrent(True, True)
            m.setDisplayFlag(True)
            m.setRenderFlag(True)
            m.setHighlightFlag(True)

            src_obj.destroy()

        dst_obj.layoutChildren()
        return m

    def freeze(self):
        sop, group, grouptype, empty = self.selection(activate_one_object=False)

        if sop is None and group is not None:
            nodes = group

        elif sop is not None:
            nodes = [sop]

        else:
            prompt(PROMPT_GEO_OBJECTS)
            return

        for pwd in nodes:
            if pwd.worldTransform() != hou.hmath.identityTransform():
                objecttoolutils.freeze((pwd,))
                pwd.displayNode().setCurrent(True, True)
        
        hou.ui.waitUntil(lambda: True)

    def catch_node_outputs(self, from_node, to_node):
        for output in from_node.outputs():
            output.setInput(output.inputs().index(from_node), to_node)
        for dot in from_node.parent().networkDots():
            if not len(dot.outputs()):
                dot.destroy()

    def fix_dir_by_viewport(self, direction, xform):
        v_xform = VIEWER.curViewport().viewTransform().inverted().transposed()
        h = hou.Vector3(1, 0, 0) * v_xform * xform
        v = hou.Vector3(0, 1, 0) * v_xform * xform
        h_dot = direction.dot(h)
        v_dot = direction.dot(v)
        if abs(h_dot) > abs(v_dot):
            if h_dot < 0:
                direction = -direction
        else:
            if v_dot < 0:
                direction = -direction

        return direction

modeler = Modeler()