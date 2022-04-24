import hou
from modeler import ui


DISTANCE_PARM_TYPE = 0
FLOAT_PARM_TYPE = 1
INT_PARM_TYPE = 2
VECTOR_PARM_TYPE = 3
SCALE_VECTOR_PARM_TYPE = 4

guide_line_drawable1 = None
guide_line_drawable2 = None
guide_line_drawable3 = None


def show_guide_line1(xform):
    global guide_line_drawable1

    if guide_line_drawable1 is None:
        line_geo = hou.Geometry()
        line_verb = hou.sopNodeTypeCategory().nodeVerb("line")
        line_verb.setParms({ "origin": hou.Vector3(0, -100000, 0), "dist": 200000 })
        line_verb.execute(line_geo, [])

        color_attrib = line_geo.addAttrib(hou.attribType.Prim, "Cd", (1.0, 1.0, 1.0))
        color = hou.Color(1, 0, 0)
        line_geo.prim(0).setAttribValue(color_attrib, color.rgb())

        guide_line_drawable1 = hou.SimpleDrawable(ui.VIEWER, line_geo, "axis_guide")
        guide_line_drawable1.setDisplayMode(hou.drawableDisplayMode.WireframeMode)

    guide_line_drawable1.enable(True)
    guide_line_drawable1.show(True)
    guide_line_drawable1.setTransform(xform)

def show_guide_line2(xform):
    global guide_line_drawable2

    if guide_line_drawable2 is None:
        line_geo = hou.Geometry()
        line_verb = hou.sopNodeTypeCategory().nodeVerb("line")
        line_verb.setParms({ "origin": hou.Vector3(0, -100000, 0), "dist": 200000 })
        line_verb.execute(line_geo, [])

        color_attrib = line_geo.addAttrib(hou.attribType.Prim, "Cd", (1.0, 1.0, 1.0))
        color = hou.Color(0, 1, 0)
        line_geo.prim(0).setAttribValue(color_attrib, color.rgb())

        guide_line_drawable2 = hou.SimpleDrawable(ui.VIEWER, line_geo, "axis_guide")
        guide_line_drawable2.setDisplayMode(hou.drawableDisplayMode.WireframeMode)

    guide_line_drawable2.enable(True)
    guide_line_drawable2.show(True)
    guide_line_drawable2.setTransform(xform)

def show_guide_line3(xform):
    global guide_line_drawable3

    if guide_line_drawable3 is None:
        line_geo = hou.Geometry()
        line_verb = hou.sopNodeTypeCategory().nodeVerb("line")
        line_verb.setParms({ "origin": hou.Vector3(0, -100000, 0), "dist": 200000 })
        line_verb.execute(line_geo, [])

        color_attrib = line_geo.addAttrib(hou.attribType.Prim, "Cd", (1.0, 1.0, 1.0))
        color = hou.Color(0, 0, 1)
        line_geo.prim(0).setAttribValue(color_attrib, color.rgb())

        guide_line_drawable3 = hou.SimpleDrawable(ui.VIEWER, line_geo, "axis_guide")
        guide_line_drawable3.setDisplayMode(hou.drawableDisplayMode.WireframeMode)

    guide_line_drawable3.enable(True)
    guide_line_drawable3.show(True)
    guide_line_drawable3.setTransform(xform)

def hide_guide_line1():
    if guide_line_drawable1 is not None:
        guide_line_drawable1.enable(False)

def hide_guide_line2():
    if guide_line_drawable2 is not None:
        guide_line_drawable2.enable(False)

def hide_guide_line3():
    if guide_line_drawable3 is not None:
        guide_line_drawable3.enable(False)

def hide_guide_lines():
    if guide_line_drawable1 is not None:
        guide_line_drawable1.enable(False)

    if guide_line_drawable2 is not None:
        guide_line_drawable2.enable(False)

    if guide_line_drawable3 is not None:
        guide_line_drawable3.enable(False)



class StateTemplate(object):
    prompt = ""
    node = None

    def __init__(self, state_name, scene_viewer):
        self.allow_snapping = False
        self.state_name = state_name
        self.onResume = self.onEnter
        self._pre_snapping_mode = None
        self._drag_parm = None
        
    def get_geometry(self):
        return self.node.inputGeometry(0)

    def onGenerate(self, kwargs):
        self.onEnter(kwargs)

    def onEnter(self, kwargs):
        ui.VIEWER.setPromptMessage(self.prompt)
        self.node = self.node or kwargs["node"]
        
        # NODE CAN BE DESTROYED ON THE INTERRUPT EVENT
        try:
            self.geo = self.get_geometry()
        except hou.ObjectWasDeleted:
            ui.VIEWER.setCurrentState("select")
            return

        # STOP STATE. FOR EXAMPLE, AFTER DISCONNECTING IT
        if self.geo is None:
            ui.VIEWER.setCurrentState("select")
            return

        self.viewport = ui.VIEWER.curViewport()

        # OBJECT MATRICES
        if ui.VIEWER.isWorldSpaceLocal():
            self._xform = hou.hmath.identityTransform()
        else:
            self._xform = self.node.creator().worldTransform()
        
        self._xform_inverted = self._xform.inverted()
        self._xform_transposed = self._xform.transposed()
        self._xform_inverted_transposed = self._xform_inverted.transposed()
        
        # VIEWPORT MATRICES
        self._viewport_xform = self.viewport.viewTransform()
        self._viewport_xform_inverted = self._viewport_xform.inverted()
        self._viewport_xform_inverted_transposed = self._viewport_xform_inverted.transposed()

        # VIEWPORT PLANE DIRS
        self._hvd = ui.get_hvd(ui.VIEWER)
        self._local_view_right_dir = hou.Vector3(1.0, 0.0, 0.0) * self._viewport_xform_inverted_transposed * self._xform_transposed
        self._local_view_up_dir = hou.Vector3(0.0, 1.0, 0.0) * self._viewport_xform_inverted_transposed * self._xform_transposed
        self._local_view_plane_dir = hou.Vector3(0.0, 0.0, 1.0) * self._viewport_xform_inverted_transposed * self._xform_transposed
        self._local_view_best_plane_dir = self._hvd[2] * self._xform_transposed

        # DEFAULT VECTOR PARMS MOVING IN VIEW PLANE
        self._current_viewport_plane_dir = self._local_view_plane_dir
        self._project_dir = None

        self.drag_scale = 1
        self.snap_value = None
        self._drag_scale_mask = 1, 1, 1

        # TURN OFF SNAPPING THAT WAS NOT UNACTIVATED NORMALLY. PROBABLY WHEN RELESING DRAG NOT ON THE VIEWPORT
        if self._pre_snapping_mode is not None:
            ui.VIEWER.setSnappingMode(self._pre_snapping_mode)
            self._pre_snapping_mode = None

    def onExit(self, kwargs):
        with hou.undos.group("Modeler: Drag Pre Exit"):
            self.pre_exit()

        # TURN OFF SNAPPING THAT WAS NOT UNACTIVATED NORMALLY. PROBABLY AFTER VOLATILE DRAG JOB
        if self._pre_snapping_mode is not None:
            ui.VIEWER.setSnappingMode(self._pre_snapping_mode)
            self._pre_snapping_mode = None

    def pre_exit(self):
        pass

    def solve_snap(self, local_snap_pos):
        pass

    def drag_release(self):
        pass

    def get_wheel_parm(self):
        return None

    def onMouseWheelEvent(self, kwargs):
        device = kwargs["ui_event"].device()
        parm = self.get_wheel_parm()
        if parm is not None:
            value = parm.eval()
            if isinstance(value, int):
                value += (1 if device.mouseWheel() > 0 else -1)
            else:    
                value = value + (hou.hmath.sign(device.mouseWheel()) * value / 10.0) if value else 0.1
            parm.set(value)

    def onMouseEvent(self, kwargs):
        ui_event = kwargs["ui_event"]
        reason = ui_event.reason()

        # MOUSE DRAG
        if reason == hou.uiEventReason.Active and self._drag_parm is not None:
            device = ui_event.device()
            self.drag_is_horizontal = abs(device.mouseX() - self._start_mouse_x) > abs(device.mouseY() - self._start_mouse_y)

            # VECTOR (CAN BE SNAPPED)
            if self._drag_type == VECTOR_PARM_TYPE and self.allow_snapping:
                snap_dict = ui_event.snappingRay()
                o = snap_dict["origin_point"]
                d = snap_dict["direction"]

                # SNAPPED
                if snap_dict["snapped"]:
                    snap_type = snap_dict["geo_type"]

                    # GEO POINT
                    if snap_type == hou.snappingPriority.GeoPoint:
                        try:
                            node = hou.nodeBySessionId( snap_dict["node_id"] )
                        except KeyError:
                            x, y = self.viewport.mapToScreen(o)
                            node = self.viewport.queryNodeAtPixel(int(x), int(y))
                            if node is None:
                                return

                        node_xform = ui.modeler.ancestor_object(node).worldTransform()
                        global_snap_pos = node.geometry().point( snap_dict["point_index"] ).position() * node_xform

                    # MIDPOINT
                    elif snap_type == hou.snappingPriority.Midpoint:
                        try:
                            node = hou.nodeBySessionId( snap_dict["node_id"] )
                        except KeyError:
                            x, y = self.viewport.mapToScreen(o)
                            node = self.viewport.queryNodeAtPixel(int(x), int(y))
                            if node is None:
                                return
                        
                        node_xform = ui.modeler.ancestor_object(node).worldTransform()
                        node_geo = node.geometry()
                        pos1 = node_geo.point( snap_dict["edge_point_index1"] ).position()
                        pos2 = node_geo.point( snap_dict["edge_point_index2"] ).position()
                        mid_pos = (pos1 + pos2) / 2.0
                        global_snap_pos = mid_pos * node_xform

                    # PRIM
                    elif snap_type == hou.snappingPriority.GeoPrim:
                        try:
                            node = hou.nodeBySessionId( snap_dict["node_id"] )
                        except KeyError:
                            x, y = self.viewport.mapToScreen(o)
                            node = self.viewport.queryNodeAtPixel(int(x), int(y))
                            if node is None:
                                return
                        
                        node_xform = ui.modeler.ancestor_object(node).worldTransform()
                        node_geo = node.geometry()
                        tmp_vec = hou.Vector3()
                        node_snap_pos = hou.Vector3()
                        intersected = node_geo.intersect(o * node_xform.inverted(), d * node_xform.transposed(), node_snap_pos, tmp_vec, tmp_vec)
                        global_snap_pos = node_snap_pos * node_xform

                    # GRID POINT, GRID EDGE 
                    elif snap_type in (hou.snappingPriority.GridPoint, hou.snappingPriority.GridEdge):
                        global_snap_pos = snap_dict["grid_pos"]

                    # OTHER SNAPPING PRIORITY NOT SUPPORTED
                    else:
                        return

                    self.solve_snap(global_snap_pos * self._xform_inverted)

                # NOT SNAPPED
                else:
                    delta_vector = ui.modeler.intersect_plane(self._start_drag_pos,  self._current_viewport_plane_dir, *ui_event.ray()) - self._start_drag_pos
                    if self._project_dir is not None:
                        delta_vector = self._project_dir * delta_vector.dot(self._project_dir)
                    self._drag_parm.set( self._drag_parm_start_value + delta_vector )
            
            elif self._drag_type == VECTOR_PARM_TYPE:
                delta_vector = ui.modeler.intersect_plane(self._start_drag_pos,  self._current_viewport_plane_dir, *ui_event.ray()) - self._start_drag_pos
                if self._project_dir is not None:
                    delta_vector = self._project_dir * delta_vector.dot(self._project_dir)
                self._drag_parm.set( self._drag_parm_start_value + delta_vector )

            elif self._drag_type == DISTANCE_PARM_TYPE:
                delta_vector = ui.modeler.intersect_plane(self._start_drag_pos,  hou.Vector3(0.0, 0.0, 1.0) * self._viewport_xform_inverted_transposed * self._xform_transposed, *ui_event.ray()) - self._start_drag_pos
                self._drag_parm.set( self._drag_parm_start_value + delta_vector.dot(hou.Vector3(1.0, 0.0, 0.0) * self._viewport_xform_inverted_transposed * self._xform_transposed) )

            elif self._drag_type == FLOAT_PARM_TYPE:
                self._drag_parm.set( self._drag_parm_start_value + self._drag_scale * (ui_event.device().mouseX() - self._drag_start_x) )
                
            elif self._drag_type == INT_PARM_TYPE:
                value = int(self._drag_scale * (ui_event.device().mouseX() - self._drag_start_x)) + self._drag_parm_start_value
                
                if self.snap_value is not None:
                    value = ui.modeler.snap_value(value, self.snap_value)

                self._drag_parm.set(value)

            elif self._drag_type == SCALE_VECTOR_PARM_TYPE:
                delta_vector = ui.modeler.intersect_plane(self._start_drag_pos,  self._current_viewport_plane_dir, *ui_event.ray()) - self._start_drag_pos
                v =  delta_vector.dot(self._scale_vector_parm_dir) / (self._start_drag_pos - hou.Vector3(self.node.evalParmTuple("p"))).length()

                if self.snap_value is not None:
                    v = ui.modeler.snap_value(v, self.snap_value)

                scale = hou.Vector3(v, v, v)
                value = self._drag_parm_start_value + scale
                value = value[0] if self._drag_scale_mask[0] else 1, value[1] if self._drag_scale_mask[1] else 1, value[2] if self._drag_scale_mask[2] else 1
                self._drag_parm.set(value)

        # MOUSE PRESS
        elif reason == hou.uiEventReason.Start:
            device = ui_event.device()
            self._start_mouse_x = device.mouseX()
            self._start_mouse_y = device.mouseY()

            # PRE PRESS INTERSECTION WITH VIEWPORT
            self._start_drag_ray_origin, self._start_drag_ray_direction = ui_event.ray()

            hit_info = ui.modeler.hit_info(self._start_drag_ray_origin, self._start_drag_ray_direction, device.mouseX(), device.mouseY(), self.viewport, local=True)
            if hit_info is None:
                self._start_drag_pos = ui.modeler.intersect_plane(self.geo.boundingBox().center(), hou.Vector3(0.0, 0.0, 1.0) * self._viewport_xform_inverted_transposed * self._xform_transposed, self._start_drag_ray_origin, self._start_drag_ray_direction)
            else:
                self._start_drag_pos = hit_info["hit_pos"]
            
            self.is_mmb = device.isMiddleButton()
            self._drag_parm, self._drag_type = self.get_drag_parm(device.isCtrlKey(), device.isShiftKey())

            if self._drag_parm is not None:
                ui.VIEWER.beginStateUndo(self.__class__.__name__ + " Drag")

                if self._drag_type == VECTOR_PARM_TYPE:
                    self._drag_scale = (1, 1, 1)
                    self._drag_parm_start_value = hou.Vector3(self._drag_parm.eval())

                elif self._drag_type == SCALE_VECTOR_PARM_TYPE:
                    self._scale_vector_parm_dir = self._local_view_right_dir
                    self._drag_scale = (1, 1, 1)
                    self._drag_parm_start_value = hou.Vector3(self._drag_parm.eval())

                elif self._drag_type == DISTANCE_PARM_TYPE:
                    self._drag_scale = 1
                    self._drag_parm_start_value = self._drag_parm.eval()

                elif self._drag_type == FLOAT_PARM_TYPE:
                    self._drag_scale = self.drag_scale / self.viewport.size()[2] * 4
                    self._drag_start_x = device.mouseX()
                    self._drag_parm_start_value = self._drag_parm.eval()

                elif self._drag_type == INT_PARM_TYPE:
                    self._drag_scale = self.drag_scale / self.viewport.size()[2] * 20
                    self._drag_start_x = device.mouseX()
                    self._drag_parm_start_value = self._drag_parm.eval()

        # MOUSE RELEASE
        elif reason == hou.uiEventReason.Changed:
            if self._drag_parm is not None:
                ui.VIEWER.endStateUndo()

                self.drag_release()
                self.drag_scale = 1


class Polygons(StateTemplate):
    prompt = "LMB: fuse tolerance; Parm Slider: divisions"

    def get_geometry(self):
        return self.node.geometry()

    def get_drag_parm(self, ctrl, shift):
        return self.node.parm("fuse_tol"), 0

    def onExit(self, kwargs):
        ui.modeler._topo_fuse_tol = self.node.evalParm("fuse_tol")

def _Polygons():
    template = hou.ViewerStateTemplate("modeler::polygons", "Polygons", hou.sopNodeTypeCategory())
    template.bindFactory(Polygons)
    template.bindIcon("MODELER_polygons")
    return template


class QPrimitive(StateTemplate):
    prompt = "LMB: uniform scale; Ctrl+LMB: uniform resolution; Shift+LMB: crease; Wheel: uniform resolution."

    def get_geometry(self):
        return self.node.geometry()

    def get_drag_parm(self, ctrl, shift):
        if not ctrl and not shift:
            return self.node.parm("scale"), 0

        elif not ctrl and shift:
            return self.node.parm("crease"), 0

        elif ctrl and not shift:
            return self.node.parm("res"), 2
        
        elif ctrl and shift:
            return self.node.parm("type"), 2
        
        return None, None

    def get_wheel_parm(self):
        return self.node.parm("res")

def _QPrimitive():
    template = hou.ViewerStateTemplate("modeler::qprimitive", "QPrimitive", hou.sopNodeTypeCategory())
    template.bindFactory(QPrimitive)
    template.bindIcon("MODELER_box")
    return template


class ExtrudePoints(StateTemplate):
    prompt = "LMB: offset by view plane; Shift+LMB: horizontally; Ctrl+LMB: vertically; Ctrl+Shift+LMB: by closest view plane."

    def get_drag_parm(self, ctrl, shift):
        self.allow_snapping = True

        self._initial_offset = hou.Vector3(self.node.evalParmTuple("offset"))

        # VIEW
        if not ctrl and not shift:
            self._project_dir = None
            self._current_viewport_plane_dir = self._local_view_plane_dir

        # H
        elif not ctrl and shift:
            self._project_dir = self._hvd[0] * self._xform_transposed
            self._current_viewport_plane_dir = self._local_view_best_plane_dir
                    
        # V
        elif ctrl and not shift:
            self._project_dir = self._hvd[1] * self._xform_transposed
            self._current_viewport_plane_dir = self._local_view_best_plane_dir
        
        # BEST PLANE
        elif ctrl and shift:
            self._project_dir = None
            self._current_viewport_plane_dir = self._local_view_best_plane_dir

        else:
            return None, None

        return self.node.parmTuple("offset"), 3

    def solve_snap(self, local_snap_pos):
        if self._project_dir is not None:
            vec = self.node.geometry().pointBoundingBox(self.node.evalParm("group")).center() + self._initial_offset - local_snap_pos
            dot = vec.dot(self._project_dir)
            value = self._initial_offset - self._project_dir * dot
        else:
            pts_center = self.node.geometry().pointBoundingBox(self.node.evalParm("group")).center()
            value = local_snap_pos - pts_center

        self.node.parmTuple("offset").set(value)

def _ExtrudePoints():
    template = hou.ViewerStateTemplate("modeler::extrude_points", "Extrude Points", hou.sopNodeTypeCategory())
    template.bindFactory(ExtrudePoints)
    template.bindIcon("MODELER_extrude_points")
    return template


class FalloffTransform(StateTemplate):
    prompt = "LMB: move nearest limit point; Shift+LMB: horizontally; Ctrl+LMB: vertically; Ctrl+Shift+LMB: by closest view plane."

    def get_drag_parm(self, ctrl, shift):
        # VIEW
        if not ctrl and not shift:
            self._project_dir = None
            self._current_viewport_plane_dir = self._local_view_plane_dir

        # H
        elif not ctrl and shift:
            self._project_dir = self._hvd[0] * self._xform_transposed
            self._current_viewport_plane_dir = self._local_view_best_plane_dir
                    
        # V
        elif ctrl and not shift:
            self._project_dir = self._hvd[1] * self._xform_transposed
            self._current_viewport_plane_dir = self._local_view_best_plane_dir
        
        # BEST PLANE
        elif ctrl and shift:
            self._project_dir = None
            self._current_viewport_plane_dir = self._local_view_best_plane_dir
        
        else:
            return None, None

        pt0 = hou.Vector3( self.node.evalParmTuple("pt0") )
        pt1 = hou.Vector3( self.node.evalParmTuple("pt1") )
        vec = pt1 - pt0
    
        # SAME POSITIONS -> DRAW
        if vec.length() == 0.0:
            self.allow_snapping = False
            self.node.parmTuple("pt0").set(self._start_drag_pos)
            self.node.parmTuple("pt1").set(self._start_drag_pos)
            return self.node.parmTuple("pt1"), 3

        # DIFFERENT POSITIONS -> DRAG NEAREST POINT
        else:
            self.allow_snapping = True
            
            if self._start_drag_pos.distanceTo(pt0) < self._start_drag_pos.distanceTo(pt1):
                self._snap_center = pt0
                self._snap_parm = self.node.parmTuple("pt0")
                return self._snap_parm, 3
            else:
                self._snap_center = pt1
                self._snap_parm = self.node.parmTuple("pt1")
                return self._snap_parm, 3

    def solve_snap(self, local_snap_pos):
        if self._project_dir is not None:
            v = local_snap_pos - self._snap_center
            dot = v.dot(self._project_dir)
            value = self._snap_center + self._project_dir * dot
        else:
            value = local_snap_pos

        self._snap_parm.set(value)

    def get_wheel_parm(self):
        return self.node.parm("relax")

def _FalloffTransform():
    template = hou.ViewerStateTemplate("modeler::falloff_xform", "Falloff Transform", hou.sopNodeTypeCategory())
    template.bindFactory(FalloffTransform)
    template.bindIcon("MODELER_deform_falloff_xform")
    return template


class Grab(StateTemplate):
    override_command = None

    def get_compass_or_cplane_xform_if_visible(self):
        if ui.VIEWER.constructionPlane().isVisible():
            cplane = ui.VIEWER.constructionPlane()
            xform = cplane.transform()
            cplane.setIsVisible(False)
            return xform

        return None

    def get_geometry(self):
        return self.node.geometry()

    def get_drag_parm(self, ctrl, shift):
        self.allow_snapping = True

        self._compass_xform = self.get_compass_or_cplane_xform_if_visible()

        if self._compass_xform is None:
            self._project_dir = None
            self._current_viewport_plane_dir = self._local_view_plane_dir

            if self.__class__.override_command is not None:
                self.onCommand({"command": self.__class__.override_command})
                self.__class__.override_command = None

        else:
            self._project_dir = ( hou.Vector3(0, 0, 1) * self._compass_xform.inverted().transposed()  * self._xform_transposed )
            self._current_viewport_plane_dir = self._local_view_plane_dir
            xform1 = hou.Vector3(0, 1, 0).matrixToRotateTo( hou.Vector3(0, 0, 1) * self._compass_xform.inverted().transposed() ) * hou.hmath.buildTranslate(self._compass_xform.extractTranslates())
            show_guide_line3(xform1)
            hide_guide_line1()
            hide_guide_line2()

        return self.node.parmTuple("t"), 3
        
    def solve_snap(self, local_snap_pos):
        if self._project_dir is None:
            value = local_snap_pos - hou.Vector3(self.node.evalParmTuple("p"))
        else:
            value = local_snap_pos - hou.Vector3(self.node.evalParmTuple("p"))
            dot = value.dot(self._project_dir)
            value = self._project_dir * dot

        self.node.parmTuple("t").set(value)

    def pre_exit(self):
        try:
            self.node.cookCount()
        except hou.ObjectWasDeleted:
            return

        if self.node.evalParm("slideonsurface"):
            self.node.parm("apply").pressButton()
            self.node.parm("slideonsurface").set(False)
            self.node.parm("switcher1").set(0)
        
        if self.node.cookCount() < 3:
            inputs = self.node.inputs()
            self.node.destroy()
            inputs[0].setCurrent(True, True)
        
        hide_guide_lines()

    def onCommand(self, kwargs):
        if kwargs["command"] == "constraint_h_axis":
            self._project_dir = self._hvd[0] * self._xform_transposed
            self._current_viewport_plane_dir = self._local_view_best_plane_dir

            xform = hou.Vector3(0, 1, 0).matrixToRotateTo(self._hvd[0]) * hou.hmath.buildTranslate(hou.Vector3(self.node.evalParmTuple("p")) * self._xform)
            show_guide_line1(xform)
            hide_guide_line2()
            hide_guide_line3()

            self.node.parm("slideonsurface").set(False)

        elif kwargs["command"] == "constraint_v_axis":
            self._project_dir = self._hvd[1] * self._xform_transposed
            self._current_viewport_plane_dir = self._local_view_best_plane_dir

            xform = hou.Vector3(0, 1, 0).matrixToRotateTo(self._hvd[1]) * hou.hmath.buildTranslate(hou.Vector3(self.node.evalParmTuple("p")) * self._xform)
            show_guide_line2(xform)
            hide_guide_line1()
            hide_guide_line3()

            self.node.parm("slideonsurface").set(False)

        elif kwargs["command"] == "constraint_plane":
            self._project_dir = None

            if self._compass_xform is None:
                self._current_viewport_plane_dir = self._local_view_best_plane_dir
            else:
                self._current_viewport_plane_dir = hou.Vector3(0, 0, 1) * self._compass_xform.inverted().transposed() * self._xform_transposed

            xform1 = hou.Vector3(0, 1, 0).matrixToRotateTo(self._hvd[0]) * hou.hmath.buildTranslate(hou.Vector3(self.node.evalParmTuple("p")) * self._xform)
            xform2 = hou.Vector3(0, 1, 0).matrixToRotateTo(self._hvd[1]) * hou.hmath.buildTranslate(hou.Vector3(self.node.evalParmTuple("p")) * self._xform)
            show_guide_line1(xform1)
            show_guide_line2(xform2)
            hide_guide_line3()
            self.node.parm("slideonsurface").set(False)

        elif kwargs["command"] == "slide":
            if self.node.evalParm("grouptype") == 3:
                # GET FIRST POINT
                point = ui.modeler.last_selection.points(ui.modeler.last_selection_geo)[0]
                sel = hou.Selection( [point] )
                sel.convert(ui.modeler.last_selection_geo, hou.geometryType.Edges)

                # POINT WITHOUT EDGES
                if not sel.numSelected():
                    ui.prompt("First point has no edges to slide")
                    return

                edges = sel.edges(ui.modeler.last_selection_geo)
                offset = hou.Vector3( self.node.evalParmTuple("t") )
                target_dir = offset.normalized()
                initial_point_pos = point.position() - offset
                
                DOT = 0
                for edge in edges:
                    edge_pt1, edge_pt2 = edge.points()
                    if edge_pt1 == point:
                        nb_pos = edge_pt2.position()
                    else:
                        nb_pos = edge_pt1.position()
                
                    edge_dir = (nb_pos - initial_point_pos).normalized()

                    dot = edge_dir.dot(target_dir)

                    if dot > DOT:
                        self._project_dir = edge_dir
                        DOT = dot

                self._current_viewport_plane_dir = self._local_view_best_plane_dir

            self.node.parm("slideonsurface").set(True)
            hide_guide_lines()


class GrabUV(StateTemplate):
    prompt = "LMB: grab by view plane; Shift+LMB: horizontally; Ctrl+LMB: vertically."

    def get_geometry(self):
        return self.node.geometry()

    def get_drag_parm(self, ctrl, shift):
        self.allow_snapping = True
        
        self._project_dir = None
        self._current_viewport_plane_dir = self._local_view_plane_dir

        return self.node.parmTuple("t"), 3

    def solve_snap(self, local_snap_pos):
        if self._project_dir is None:
            value = local_snap_pos - hou.Vector3(self.node.evalParmTuple("p"))
        else:
            value = local_snap_pos - hou.Vector3(self.node.evalParmTuple("p"))
            dot = value.dot(self._project_dir)
            value = self._project_dir * dot

        self.node.parmTuple("t").set(value)

    def pre_exit(self):
        try:
            self.node.cookCount()
        except hou.ObjectWasDeleted:
            return

        if self.node.cookCount() < 3:
            inputs = self.node.inputs()
            self.node.destroy()
            inputs[0].setCurrent(True, True)

    def onCommand(self, kwargs):
        if kwargs["command"] == "constraint_h_axis":
            self._project_dir = self._hvd[0] * self._xform_transposed
            self._current_viewport_plane_dir = self._local_view_best_plane_dir

        elif kwargs["command"] == "constraint_v_axis":
            self._project_dir = self._hvd[1] * self._xform_transposed
            self._current_viewport_plane_dir = self._local_view_best_plane_dir


class GrabPeak(Grab):
    def get_drag_parm(self, ctrl, shift):
        return self.node.parm("dist"), 0


def register_grab():
    template = hou.ViewerStateTemplate("modeler::grab", "Grab", hou.sopNodeTypeCategory())
    template.bindFactory(Grab)
    template.bindIcon("MODELER_grab")
    hou.ui.registerViewerState(template)

def register_grab_uv():
    template = hou.ViewerStateTemplate("modeler::grab_uv", "Grab UV", hou.sopNodeTypeCategory())
    template.bindFactory(GrabUV)
    template.bindIcon("MODELER_grab")
    hou.ui.registerViewerState(template)

def register_grab_peak():
    template = hou.ViewerStateTemplate("modeler::grab_peak", "Grab Peak", hou.sopNodeTypeCategory())
    template.bindFactory(GrabPeak)
    template.bindIcon("MODELER_grab")
    hou.ui.registerViewerState(template)

register_grab()
register_grab_uv()
register_grab_peak()


_grab_objects = None
_grab_objects_translatemethod = None
_grab_state_name = None


def grab(state_name):
    global _grab_objects, _grab_objects_translatemethod, _grab_state_name

    state = ui.VIEWER.currentState()

    # FINISH SCRIPTSELECT
    if state == "scriptselect":
        return

    else:
        is_uv = ui.VIEWER.curViewport().type() == hou.geometryViewportType.UV
        sop, group, grouptype, empty = ui.modeler.selection(activate_one_object=True)
        if sop is not None:
            with hou.RedrawBlock() as rb:
                with hou.undos.group("Modeler: Grab"):
                    # UV GRAB
                    if is_uv:
                        group = group or "*"

                        if grouptype == hou.geometryType.Points:
                            grouptype = 3
                        
                        elif grouptype == hou.geometryType.Primitives:
                            grouptype = 4
                        
                        elif grouptype == hou.geometryType.Edges:
                            grouptype = 2
                        
                        else:
                            grouptype = 1

                        if sop.type().name() == "uvedit":
                            sop.parm("apply").pressButton()
                            node = sop
                            new = False
                        else:
                            node = sop.createOutputNode("uvedit")
                            ui.modeler.activate_sop_with_select_state(node)
                            new = True

                        node.setParms({ "group": group, "grouptype": grouptype })
                        
                        state_name = "modeler::grab_uv"
                        state_class = GrabUV
                        
                        if new:
                            hou.ui.waitUntil(lambda: True)
                        
                        ui.VIEWER.enterTranslateToolState()

                    # GEO GRAB
                    else:
                        if grouptype == hou.geometryType.Points:
                            items_center = ui.modeler.last_selection_geo.pointBoundingBox(group).center()
                            grouptype = 3
                        
                        elif grouptype == hou.geometryType.Primitives:
                            items_center = ui.modeler.last_selection_geo.primBoundingBox(group).center()
                            grouptype = 4
                        
                        elif grouptype == hou.geometryType.Edges:
                            sel = ui.modeler.last_selection.freeze()
                            sel.convert(ui.modeler.last_selection_geo, hou.geometryType.Points)
                            items_center = ui.modeler.last_selection_geo.pointBoundingBox(sel.selectionString(ui.modeler.last_selection_geo, force_numeric=True)).center()
                            grouptype = 2
                        
                        else:
                            ui.prompt(ui.PROMPT_OBJECTS_OR_COMPONENTS)
                            return

                        node = ui.modeler.get_edit_sop(sop)

                        # GRAB
                        if state_name in ("modeler::grab", "modeler::grab_rotate", "modeler::grab_scale"):
                            node.setParms({ "group": group, "grouptype": grouptype, "xformspace": 0,
                                                     "px": items_center[0], "py": items_center[1], "pz": items_center[2] })
                            
                            if state_name == "modeler::grab":
                                state_class = Grab

                            elif state_name == "modeler::grab_rotate":
                                state_class = GrabRotate

                            else:
                                state_class = GrabScale
                        
                        # Peak
                        else:
                            node.setParms({ "group": group, "grouptype": grouptype, "xformspace": 0, "switcher1": 1 })
                            state_class = GrabPeak

                        ui.symmetry.setup_edit_sop(node)

                    node.setRenderFlag(True)
                    node.setHighlightFlag(True)
                    node.setDisplayFlag(True)
                    node.setCurrent(True, True)
                    state_class._new_edit = node != sop
                    state_class.node = node
                    _grab_state_name = state_name
                    hou.ui.postEventCallback(_grab)

        else:
            ui.prompt(ui.PROMPT_OBJECTS_OR_COMPONENTS)

def _grab():
    ui.VIEWER.setCurrentState(_grab_state_name)


def Magnet():
    sop = ui.modeler.get_sop()
    if sop is not None:
        state = ui.VIEWER.currentState()

        with hou.RedrawBlock() as rb:
            with hou.undos.group("Modeler: Magnet"):
                ui.VIEWER.constructionPlane().setIsVisible(False)
            
                # UV BRUSH EDITING
                if ui.VIEWER.curViewport().type() == hou.geometryViewportType.UV:
                    if state != "uvbrush":
                        if sop.type().name() == "uvbrush":
                            sop.parm("flood").pressButton()
                            sop.parm("group").set("")
                            ui.VIEWER.enterCurrentNodeState()
                        else:
                            sop = sop.createOutputNode("uvbrush")
                            sop.setCurrent(True, True)
                            sop.setDisplayFlag(True)
                            sop.setRenderFlag(True)
                            ui.VIEWER.enterCurrentNodeState()        

                elif state != "modeler::magnet":
                    edit_sop = ui.modeler.get_edit_sop(sop)
                    edit_sop.setParms({ "grouptype": 3, "xformspace": 0, "slideonsurface": False, "switcher1": 0, "modeswitcher1": 0, "rad": hou.modeler.states.MagnetStateTemplate._radius, "distmetric": hou.modeler.states.MagnetStateTemplate._separate_move })
                    ui.symmetry.setup_edit_sop(edit_sop)
                    edit_sop.setCurrent(True, True)
                    edit_sop.setHighlightFlag(False)
                    edit_sop.setRenderFlag(True)
                    edit_sop.setDisplayFlag(True)
                    pwd = ui.modeler.ancestor_object(edit_sop)
                    hou.modeler.states.MagnetStateTemplate.sop = edit_sop
                    hou.modeler.states.MagnetStateTemplate.geo = edit_sop.geometry()
                    hou.modeler.states.MagnetStateTemplate.dirt = False
                    hou.modeler.states.MagnetStateTemplate.xform = pwd.worldTransform()
                    hou.modeler.states.MagnetStateTemplate.xform_inverted = hou.modeler.states.MagnetStateTemplate.xform.inverted()
                    hou.modeler.states.MagnetStateTemplate.xform_transposed = hou.modeler.states.MagnetStateTemplate.xform.transposed()
                    hou.ui.waitUntil(lambda: True)
                    ui.VIEWER.setCurrentState("modeler::magnet")
                    ui.VIEWER.runStateCommand("move_mode")
                    ui.shift_cursor()

class MagnetStateTemplate():
    _radius = 0.1
    _magnet_opacity = 0.5
    _smooth_opacity = 0.25
    _separate_move = 4
    hit_point = hit_point_string = hit_edge = hit_prim = None
    initial_separate_move = 4
    last_mouse_move_x = last_mouse_move_y = None

    # CREATE AND STORE DRAWABLE GEOMETRY OBJECTS
    radius_drawable_geo = hou.Geometry()    
    circle = hou.sopNodeTypeCategory().nodeVerb("circle")
    circle.setParms({ "type": 2 })
    circle.execute(radius_drawable_geo, [])
    del circle
    radius_drawable_params = { "color1": hou.Color(1, 0.9, 0.3), "style": hou.drawableGeometryLineStyle.Plain, "line_width": hou.ui.scaledSize(1) }

    def show_prompt_message(self):
        ui.VIEWER.setPromptMessage("LMB: move or smooth points; MMB: change radius")

    def __init__(self, scene_viewer, state_name):
        self.radius_drawable = hou.SimpleDrawable(ui.VIEWER, self.radius_drawable_geo, "mb_radius_circle")
        self.radius_drawable.enable(True)
        self.transform_mode = 0

    def onExit(self, kwargs):
        try:
            if self.sop.cookCount() < 4:
                self.sop.destroy()

        except hou.ObjectWasDeleted:
            pass

        self.radius_drawable.enable(False)

    def onGenerate(self, kwargs):
        self.viewport = ui.VIEWER.curViewport()
        self.show_prompt_message()

    def onInterrupt(self, kwargs):
        self.radius_drawable.show(False)
        ui.VIEWER.clearPromptMessage()

    def onResume(self, kwargs):
        self.viewport = ui.VIEWER.curViewport()
        hou.ui.postEventCallback(self.show_prompt_message)

    def hit(self):
        # GET CURRENT VIEWPORT AND IT'S NORMAL 
        xform_inverted_transposed = self.viewport.viewTransform().inverted().transposed()
        self._view_normal = hou.Vector3(0.0, 0.0, 1.0) * xform_inverted_transposed
        self._view_normal_local = self._view_normal * self.xform_transposed
        self._view_right = hou.Vector3(1.0, 0.0, 0.0) * xform_inverted_transposed 
        self._view_right_local = self._view_right * self.xform_transposed
        self.hit_point = self.hit_point_string = self.hit_edge = self.hit_prim = None
        self._cursor_origin, self._cursor_dir = self.event.ray()
        self.hit_normal = hou.Vector3()
        self.hit_uvw = hou.Vector3()
        self._start_intersection = hou.Vector3()
        intersected = self.geo.intersect(self._cursor_origin, self._cursor_dir, self._start_intersection, self.hit_normal, self.hit_uvw)

        if intersected > -1:
            self.hit_prim_int = intersected
            self.hit_pos = self._start_intersection
            self.hit_prim = self.geo.prim(intersected)
            prim_points = self.hit_prim.points()
            points_count = len(prim_points)
            
            # FIND NEAREST POINT
            d = 999999.0
            nearest_id = -1
            for i in range(points_count):
                pos = prim_points[i].position()
                d1 = self._start_intersection.distanceTo(pos)
                if d1 < d:
                    d = d1
                    nearest_id = i

            self.hit_point = prim_points[nearest_id]
            last_id = points_count - 1
            
            if nearest_id == 0:
                nb1 = last_id
                nb2 = 1
            elif nearest_id == last_id:
                nb1 = nearest_id - 1
                nb2 = 0
            else:
                nb1 = nearest_id - 1
                nb2 = nearest_id + 1

            hit_point_pos = self.hit_point.position()
            self.hit_point_string = str(self.hit_point.number())

            # FIND HIT EDGE ON CLOSED FACE
            if self.hit_prim.isClosed():
                nb1 = prim_points[nb1]
                nb2 = prim_points[nb2]
                nb1_pos = nb1.position()
                nb2_pos = nb2.position()
                d1 = self._start_intersection.distanceToSegment(hit_point_pos, nb1_pos)
                d2 = self._start_intersection.distanceToSegment(hit_point_pos, nb2_pos)
                if d1 < d2:
                    self.hit_edge = self.geo.findEdge(self.hit_point, nb1)
                else:
                    self.hit_edge = self.geo.findEdge(self.hit_point, nb2)

            self._peak_normal = self.geo.pointNormals((self.hit_point,))[0]

            # SYMMETRY ACTIVATED
            if self.sop.evalParm("doreflect"):
                sym_origin = hou.Vector3(self.sop.evalParmTuple("symorig"))
                self._sym_dir = hou.Vector3(self.sop.evalParmTuple("symaxis"))
                
                i = ui.modeler.intersect_plane(sym_origin, self._sym_dir, hit_point_pos, -self._sym_dir)
                d = i.distanceTo(hit_point_pos)

                dot = self._view_normal_local.dot(self._sym_dir)

                # ACTIVATE SYM PROJECT IN SOME CASES
                if d < 0.0001 or ( dot > 0.8 and (d < self.sop.evalParm("rad")) ):
                    self._is_sym =  True
                else:
                    self._is_sym =  False

            # SYMMETRY NOT ACTIVATED
            else:
                self._is_sym = False

        else:
            self.hit_point = None

        # REDRAW RADIUS DRAWABLE
        self._update_radius()

        self.mode = 0

    def onMouseEvent(self, kwargs):
        self.event = kwargs["ui_event"]
        reason = self.event.reason()

        # MOUSE MOVE
        if reason == hou.uiEventReason.Located:
            # CALCULATE ONLY ON MOUSE MOVE. MOUSE PRESS ALSO EMITS LOCATED EVENT.
            if self.event.device().mouseX() != self.last_mouse_move_x or self.event.device().mouseY() != self.last_mouse_move_y: 
                self.last_mouse_move_x = self.event.device().mouseX()
                self.last_mouse_move_y = self.event.device().mouseY()
                self.hit()

        # MOUSE DRAG
        elif reason == hou.uiEventReason.Active:
            
            # MOVE
            if self.mode == 1:
                o, d = self.event.ray()
                intersection = ui.modeler.intersect_plane(self._start_intersection, self._view_normal_local, o, d)

                if self._is_sym:
                    intersection = ui.modeler.intersect_plane(self._start_intersection, self._sym_dir, intersection, self._sym_dir)                    
            
                self.sop.parmTuple("t").set( (intersection - self._start_intersection) * self.__class__._magnet_opacity )

            # SMOOTH
            elif self.mode == 2:
                hit_normal = hou.Vector3()
                hit_uvw = hou.Vector3()
                hit_pos = hou.Vector3()
                prim_int = self.geo.intersect(*self.event.ray(), hit_pos, hit_normal, hit_uvw)
                if prim_int > -1:
                    self.sop.parmTuple("dir").set(hit_normal)
                    self.sop.parmTuple("hitpos").set(hit_pos)
                    self.sop.parm("hitprim").set(prim_int)
                    self.sop.parmTuple("hituvw").set(hit_uvw)

            # RADIUS
            elif self.mode == 3:
                o, d = self.event.ray()
                intersection = ui.modeler.intersect_plane(self._start_intersection, self._view_normal_local, o, d)
                offset = intersection - self._start_intersection
                self.__class__._radius = max(self._pre_radius + offset.dot(self._view_right_local), 0.0001)
                self._update_radius()

        # MOUSE PRESS
        elif reason == hou.uiEventReason.Start and self.hit_point is not None:
            device = self.event.device()

            # LMB: MOVE AND SMOOTH
            if device.isLeftButton():
                ui.VIEWER.beginStateUndo("Modeler: Move Operation")

                if kwargs['state_parms']["smooth_mode"]["value"]:
                    self.sop.setParms({ "modeswitcher1": 1, "group": "", "op": 1, "sculptrad": self.__class__._radius })
                    self.sop.parm("opacity").set( device.tabletPressure() * self.__class__._smooth_opacity )
                    self.sop.parmTuple("dir").set(self.hit_normal)
                    self.sop.parmTuple("hitpos").set(self._start_intersection)
                    self.sop.parm("hitprim").set(self.hit_prim_int)
                    self.sop.parmTuple("hituvw").set(self.hit_uvw)
                    self.sop.parm("event").set(1)
                    self.mode = 2
                else:
                    self.sop.setParms({ "group": self.hit_point_string, "rad": self.__class__._radius })
                    self.mode = 1

                self.radius_drawable.show(False)

            # MMB: RADIUS
            elif device.isMiddleButton():
                self._pre_radius = self.__class__._radius
                self.mode = 3

            else:
                self.mode = 0

        # MOUSE RELEASE
        elif reason == hou.uiEventReason.Changed:
            if self.mode == 1:
                self.sop.parm("apply").pressButton()
                self.sop.setParms({ "grouptype": 3, "switcher1": 0, "slideonsurface": False })
                ui.VIEWER.endStateUndo()
                self.dirt = True
            
            elif self.mode == 2:
                self.sop.setParms({ "event": 2, "event": 4, "modeswitcher1": 0 })
                ui.VIEWER.endStateUndo()
                self.dirt = True

            self.mode = 0

            self.hit()

    def onMouseWheelEvent(self, kwargs):
        if self.hit_point is not None:
            with hou.undos.disabler():
                self.__class__._radius = self.__class__._radius + hou.hmath.sign( kwargs["ui_event"].device().mouseWheel() ) * self.__class__._radius / 10.0
                self._update_radius()

    def _update_radius(self):
        if self.hit_point is not None:
            x, y = self.viewport.mapToScreen(self._start_intersection * self.xform + self._view_right * self.__class__._radius)
            cpos = (self._cursor_origin * self.xform + self._cursor_dir * self.xform_inverted.transposed() * 0.01)
            rot = hou.Vector3(0, 0, 1).matrixToRotateTo(self._view_normal_local * self.xform_inverted.transposed())
            viewport_rot_xform = hou.Matrix4(self.viewport.viewTransform().extractRotationMatrix3())
            d_, o_ = self.viewport.mapToWorld(x, y)
            scale = cpos.distanceTo(o_ + d_ * 0.01)
            xform = hou.hmath.identityTransform() * rot * viewport_rot_xform.inverted() * hou.hmath.buildScale(scale, scale, 0.0001) * viewport_rot_xform * hou.hmath.buildTranslate(cpos)
            self.radius_drawable.setTransform(xform)
            self.radius_drawable.show(True)
        else:
            self.radius_drawable.show(False)

    def onCommand(self, kwargs):
        if kwargs["command"] == "move_mode":
            kwargs['state_parms']["smooth_mode"]["value"] = False

    def onParmChangeEvent(self, kwargs):
        parm_name = kwargs['parm_name']
        state_parms = kwargs['state_parms']

        if parm_name == "move_intensity_0_25":
            state_parms["move_intensity"]["value"] = 0.25
            self.__class__._magnet_opacity = 0.25

        elif parm_name == "move_intensity_0_5":
            state_parms["move_intensity"]["value"] = 0.5
            self.__class__._magnet_opacity = 0.5

        elif parm_name == "move_intensity_0_75":
            state_parms["move_intensity"]["value"] = 0.75
            self.__class__._magnet_opacity = 0.75

        elif parm_name == "move_intensity_1":
            state_parms["move_intensity"]["value"] = 1.0
            self.__class__._magnet_opacity = 1.0

        elif parm_name == "smooth_intensity_0_25":
            state_parms["smooth_intensity"]["value"] = 0.25
            self.__class__._smooth_opacity = 0.25

        elif parm_name == "smooth_intensity_0_5":
            state_parms["smooth_intensity"]["value"] = 0.5
            self.__class__._smooth_opacity = 0.5

        elif parm_name == "smooth_intensity_0_75":
            state_parms["smooth_intensity"]["value"] = 0.75
            self.__class__._smooth_opacity = 0.75

        elif parm_name == "smooth_intensity_1":
            state_parms["smooth_intensity"]["value"] = 1.0
            self.__class__._smooth_opacity = 1.0

        elif parm_name == "move_intensity":
            self.__class__._magnet_opacity = kwargs['parm_value']

        elif parm_name == "smooth_intensity":
            self.__class__._smooth_opacity = kwargs['parm_value']

        elif parm_name == "separate_move":
            if kwargs["parm_value"]:
                self.__class__._separate_move = 4
            else:
                self.__class__._separate_move = 2

            self.sop.parm("distmetric").set(self.__class__._separate_move)

def register_magnet_state():
    template = hou.ViewerStateTemplate("modeler::magnet", "Magnet", hou.sopNodeTypeCategory())
    template.bindFactory(MagnetStateTemplate)
    template.bindIcon("MODELER_magnet")
    template.bindParameter( hou.parmTemplateType.Toggle, name="separate_move", label="Move Separately", default_value=MagnetStateTemplate._separate_move )
    template.bindParameter( hou.parmTemplateType.Float, name="move_intensity", label="Intensity", min_limit=0.0, max_limit=1.0, default_value=MagnetStateTemplate._magnet_opacity )
    template.bindParameter( hou.parmTemplateType.Button, name="move_intensity_0_25", label="0.25", align=True )
    template.bindParameter( hou.parmTemplateType.Button, name="move_intensity_0_5", label="0.5", align=True )
    template.bindParameter( hou.parmTemplateType.Button, name="move_intensity_0_75", label="0.75", align=True )
    template.bindParameter( hou.parmTemplateType.Button, name="move_intensity_1", label="1.0", align=True )
    template.bindParameter( hou.parmTemplateType.Toggle, name="smooth_mode", label="Smooth      ", default_value=False )
    template.bindParameter( hou.parmTemplateType.Float, name="smooth_intensity", label="Smooth Intensity", min_limit=0.0, max_limit=1.0, default_value=MagnetStateTemplate._smooth_opacity )
    template.bindParameter( hou.parmTemplateType.Button, name="smooth_intensity_0_25", label="0.25", align=True )
    template.bindParameter( hou.parmTemplateType.Button, name="smooth_intensity_0_5", label="0.5", align=True )
    template.bindParameter( hou.parmTemplateType.Button, name="smooth_intensity_0_75", label="0.75", align=True )
    template.bindParameter( hou.parmTemplateType.Button, name="smooth_intensity_1", label="1.0", align=True )
    hou.ui.registerViewerState(template)


def PolyPen():
    if ui.VIEWER.currentState() == "modeler::polypen":
        ui.VIEWER.runStateCommand("match_loop_profile")
    
    else:
        sop = ui.modeler.get_sop()
        if sop is not None:
            ui.VIEWER.constructionPlane().setIsVisible(False)

            with hou.RedrawBlock() as rb:
                PolyPenStateTemplate.subnet = sop.createOutputNode("subnet", "polypen1")
                PolyPenStateTemplate.subnet.setDisplayFlag(True)
                PolyPenStateTemplate.subnet.setRenderFlag(True)
                PolyPenStateTemplate.subnet.setCurrent(True, True)
                om = ui.modeler.topo_get_ref(sop.parent())

                # STD MODE
                if om is None:
                    PolyPenStateTemplate.connect_new_sop = PolyPenStateTemplate.connect_new_sop_std_mode
                    PolyPenStateTemplate.get_display_sop = PolyPenStateTemplate.get_display_sop_std_mode
                
                # TOPO MODE
                else:
                    PolyPenStateTemplate.connect_new_sop = PolyPenStateTemplate.connect_new_sop_topo_mode
                    PolyPenStateTemplate.get_display_sop = PolyPenStateTemplate.get_display_sop_topo_mode
                    PolyPenStateTemplate.subnet.setInput(1, om)
                    PolyPenStateTemplate.ray_sop = PolyPenStateTemplate.subnet.createNode("ray")
                    PolyPenStateTemplate.ray_sop.parm("method").set(0)
                    indirect_input1, indirect_input2, _, _ = PolyPenStateTemplate.subnet.indirectInputs()
                    PolyPenStateTemplate.ray_sop.setInput(0, indirect_input1)
                    PolyPenStateTemplate.ray_sop.setInput(1, indirect_input2)
                    PolyPenStateTemplate.ray_sop.setDisplayFlag(True)

                PolyPenStateTemplate.geo = PolyPenStateTemplate.subnet.geometry()
                hou.ui.waitUntil(lambda: True)
                ui.VIEWER.setCurrentState("modeler::polypen")
                ui.shift_cursor()


class PolyPenEventFilter(ui.qtc.QObject):
    def eventFilter(self, obj, event):
        # VIEW STATE -> IGNORE
        if event.type() == ui.qtc.QEvent.MouseButtonPress and event.modifiers() & ui.qt.AltModifier:
            return False

        # VIEW STATE -> IGNORE
        elif event.type() == ui.qtc.QEvent.MouseButtonRelease and event.modifiers() & ui.qt.AltModifier:
            return False
        
        # LMB PRESS
        elif event.type() == ui.qtc.QEvent.MouseButtonPress and event.button() == ui.qt.LeftButton:
            self.start_time = ui.time.time()
            self.start_x = event.x()
            self.start_y = event.y()
            pos = event.pos()
            x = pos.x()
            y = ui.VIEWER_WIDGET.height() - pos.y()
            cursor_node = ui.VIEWER.curViewport().queryNodeAtPixel(x, y)
            cur_node = ui.VIEWER.currentNode()
            is_node = ui.VIEWER.curViewport().queryPrimAtPixel(None, x, y) is not None
            self.in_space = not is_node and ( cursor_node is None or  (cursor_node is not None and ui.modeler.ancestor_object(cursor_node).type().name() == "modeler::backdrop" ) ) 
            return False
        
        # LMB RELEASE
        elif event.type() == ui.qtc.QEvent.MouseButtonRelease and event.button() == ui.qt.LeftButton and event.buttons() != ui.qt.MiddleButton:
            if ui.modeler.is_click(self.start_x, self.start_y, event.x(), event.y(), self.start_time):
                ui.VIEWER.runStateCommand("click")
            return False

        # RMB PRESS
        elif event.type() == ui.qtc.QEvent.MouseButtonPress and event.button() == ui.qt.RightButton:
            return False

        # RMB RELEASE
        elif event.type() == ui.qtc.QEvent.MouseButtonRelease and event.button() == ui.qt.RightButton:
            return False

        elif event.type() == ui.qtc.QEvent.MouseButtonDblClick:
            return True

        return False
        
polypen_ef = PolyPenEventFilter()


class PolyPenStateTemplate(object):
    ignore_backfacing = True
    slide = True
    freeslide = True
    move_edges = False
    cut_mode = True
    hit_point = hit_point_string = hit_edge = hit_prim = None
    last_mouse_move_x = last_mouse_move_y = None
    point_drawable_geo = hou.Geometry()
    sphere = hou.sopNodeTypeCategory().nodeVerb("sphere")
    sphere.setParms({ "type": 1, "scale": 0.000001 })
    sphere.execute(point_drawable_geo, [])
    del sphere
    edge_line_drawable_geo = hou.Geometry()
    line = hou.sopNodeTypeCategory().nodeVerb("line")
    line.execute(edge_line_drawable_geo, [])
    del line

    edge_line_drawable_params = {
        "style": hou.drawableGeometryLineStyle.Plain,
        "line_width": hou.ui.scaledSize(2),
    }                                                                                                

    cut_line_drawable_params = {
        "glow_width": hou.ui.scaledSize(1),
        "style": hou.drawableGeometryLineStyle.Plain,
    }                                                                                                

    perpendicular_line_drawable_params = {
        "glow_width": hou.ui.scaledSize(1),
        "style": hou.drawableGeometryLineStyle.Dot3,
        "highlight_mode": hou.drawableHighlightMode.Matte,
    }                                                                                                

    point_drawable_params = {
        "glow_width": hou.ui.scaledSize(2),
        "style": hou.drawableGeometryLineStyle.Plain,
        "highlight_mode": hou.drawableHighlightMode.Matte,
    }     


    def show_prompt_message(self):
        ui.VIEWER.setPromptMessage("LMB Drag: Cut; LMB Click: Delete; MMB Drag: Transform point or edge or Inset polygon; Press LMB|RMB while dragging MMB to move edge loop. \nTo Fill hole drag LMB from boundary point or edge to empty space. To Bridge edges drag LMB from edge to another one.")

    def __init__(self, scene_viewer, state_name):
        self.edge_line_drawable = hou.GeometryDrawable(ui.VIEWER, hou.drawableGeometryType.Line, "edge_line_drawable", params=self.edge_line_drawable_params)
        self.cut_line_drawable = hou.GeometryDrawable(ui.VIEWER, hou.drawableGeometryType.Line, "edge_cut_line_drawable", params=self.cut_line_drawable_params)
        self.perpendicular_line_drawable = hou.GeometryDrawable(ui.VIEWER, hou.drawableGeometryType.Line, "edge_perpendicular_line_drawable", params=self.perpendicular_line_drawable_params)
        self.point_drawable = hou.GeometryDrawable(ui.VIEWER, hou.drawableGeometryType.Line, "edge_point_drawable", params=self.point_drawable_params)
        self.tol = hou.ui.scaledSize(8)
        self.color = hou.Color((1.0, 0.9, 0.3))

        vp_point_marker_size = scene_viewer.curViewport().settings().pointMarkerSize() * 2.2
        vp_wire_width = scene_viewer.curViewport().settings().wireWidth() * 2

        self.point_drawable.setParams({ "line_width": vp_point_marker_size, "glow_width": vp_point_marker_size * 0.2, "color1": self.color, "color2": self.color })
        self.edge_line_drawable.setParams({ "line_width": vp_wire_width, "glow_width": vp_wire_width * 0.4, "color1": self.color, "color2": self.color })
        self.cut_line_drawable.setParams({ "line_width":vp_wire_width, "glow_width": vp_wire_width * 0.4, "color1": self.color, "color2": self.color })
        self.perpendicular_line_drawable.setParams({ "line_width": vp_wire_width, "glow_width": vp_wire_width * 0.4, "color1": self.color, "color2": self.color })
        self.edge_line_drawable.setGeometry(self.edge_line_drawable_geo)
        self.cut_line_drawable.setGeometry(self.edge_line_drawable_geo)
        self.perpendicular_line_drawable.setGeometry(self.edge_line_drawable_geo)
        self.point_drawable.setGeometry(self.point_drawable_geo)

        self.press = False
        self.snap_point = None

        # SET CURSOR BASED ONE INITIAL MODE
        if self.__class__.cut_mode:
            ui.VIEWER_WIDGET.unsetCursor()
        else:
            ui.VIEWER_WIDGET.setCursor(ui.qt.PointingHandCursor)

        ui.VIEWER_WIDGET.installEventFilter(polypen_ef)

    def onExit(self, kwargs):
        # HIDE POINT MARKERS
        if not self.is_showing_point_markers:
            for viewport in ui.VIEWER.viewports():
                viewport.settings().displaySet(hou.displaySetType.DisplayModel).showPointMarkers(False)
        ui.VIEWER_WIDGET.unsetCursor()
        ui.VIEWER_WIDGET.removeEventFilter(polypen_ef)

    def onGenerate(self, kwargs):
        self.viewport = ui.VIEWER.curViewport()

        # SHOW POINT MARKERS
        self.is_showing_point_markers = self.viewport.settings().displaySet(hou.displaySetType.DisplayModel).isShowingPointNumbers()
        if not self.is_showing_point_markers:
            for viewport in ui.VIEWER.viewports():
                viewport.settings().displaySet(hou.displaySetType.DisplayModel).showPointMarkers(True)
        self.show_prompt_message()

    def onMouseEvent(self, kwargs):
        self.event = kwargs["ui_event"]
        self.device = self.event.device()
        reason = self.event.reason()

        # MOUSE MOVE
        if reason == hou.uiEventReason.Located:
            x = self.device.mouseX()
            y = self.device.mouseY()

            # CALCULATE ONLY ON MOUSE MOVE. MOUSE PRESS ALSO EMITS LOCATED EVENT.
            if x != self.last_mouse_move_x or y != self.last_mouse_move_y:
                self.hit()
                self.last_mouse_move_x = x
                self.last_mouse_move_y = y

        # MOUSE DRAG
        elif reason == hou.uiEventReason.Active and self.press:
            x = self.device.mouseX()
            y = self.device.mouseY()
            
            # CONTINUE DRAG
            if self.drag:
                # CONTINUE MOVING
                if self.edit_sop is not None:
                    if self.can_snap:
                        # NOT BOUNDARY POINT CAN SNAP TO PREDEFINED NEIGHBOURS
                        snap_position = None

                        for snap_neighbour in self.point_snap_neighbours:
                            pos = snap_neighbour.position()
                            if self.is_position_near_cursor(pos, x, y):
                                snap_position = pos
                                self.snap_point = snap_neighbour
                                break

                        if snap_position is None:
                            (o, d) = self.event.ray()
                            tmp_vec = hou.Vector3()
                            hit_uvw = hou.Vector3()
                            hit_pos = hou.Vector3()
                            intersected = self.geo.intersect(o, d, hit_pos, tmp_vec, hit_uvw, pattern="!" + str(self.hit_prim.number()))

                            if intersected > -1:
                                hit_prim = self.geo.prim(intersected)
                                hit_normal = hit_prim.normal()     # HOUDINI BUG. THE INTERSECT METHOD CAN'T ALWAYS CALCULATE RIGHT NORMAL
                                prim_is_closed = hit_prim.isClosed()                                
                                if prim_is_closed and hit_normal.dot(self._view_normal_local) > 0:
                                    point = self.geo.nearestPoint(hit_pos, ptgroup="!" + self.group)
                                    pos = point.position()
                                    if self.is_position_near_cursor(pos, x, y):
                                        self.snap_point = point
                                        snap_position = pos

                        # MOVE TO SNAPED POINT
                        if snap_position is not None:
                            offset = snap_position - self.point_initial_pos
                            self.edit_sop.parmTuple("t").set(offset)
                            xform = self.xform_inverted * hou.hmath.buildTranslate(snap_position) * self.xform
                            self.point_drawable.setTransform(xform)
                            self.highlight_drawable(self.point_drawable, True)
                            self.point_drawable.show(True)
                            self.edge_line_drawable.show(False)
                            return
                        
                        self.highlight_drawable(self.point_drawable, False)

                    vec = ui.modeler.intersect_plane(self.hit_pos, self._view_normal_local, *self.event.ray()) - self.hit_pos
                    
                    if self.slide_point:
                        CLOSEST_VEC = None
                        CLOSEST_DOT = 0
                        CLOSEST_EDGE_NB_POS = None

                        for (slide_vec, nb_pos) in self.point_slide_vectors:
                            dot = vec.dot(slide_vec)
                            if dot > CLOSEST_DOT:
                                CLOSEST_DOT = dot
                                CLOSEST_VEC = slide_vec
                                CLOSEST_EDGE_NB_POS = nb_pos

                        if CLOSEST_VEC is None:
                            self.edge_line_drawable.show(False)
                        else:
                            vec = CLOSEST_VEC * CLOSEST_DOT
                            self.draw_line_drawable_at_positions(self.edge_line_drawable, self.point_initial_pos + vec, CLOSEST_EDGE_NB_POS)
                            self.edit_sop.parmTuple("t").set( vec )
                    
                    else:
                        self.edge_line_drawable.show(False)
                        self.edit_sop.parmTuple("t").set(vec)
    
                    self.snap_point = None
                    self.point_drawable.show(False)

                # CONTINUE SPLIT
                elif self.split_sop is not None:
                    self.hit()

                    # UPDATE SPLIT DRAWABLE
                    if self.is_on_surface:
                        if type(self.nearest_component) == hou.Edge:
                            (pt1, pt2) = self.nearest_component.points()
                            pos1 = pt1.position()
                            pos2 = pt2.position()
                            perpendicular_pos = self.split_start_hit_pos.pointOnSegment(pos1, pos2)
                            allow_perpendicular = perpendicular_pos != pos1 and perpendicular_pos != pos2
                            
                            if allow_perpendicular:
                                self.draw_line_drawable_at_positions(self.perpendicular_line_drawable, self.split_start_hit_pos, perpendicular_pos)
                                
                                if self.is_edge_center_highlighted:
                                    self.highlight_drawable(self.perpendicular_line_drawable, False)

                                elif self.is_position_near_cursor(perpendicular_pos, x, y):
                                    self.split_hit_pos = perpendicular_pos
                                    ratio = (self.split_hit_pos - pos1).length() / self.nearest_component.length()
                                    self.splitloc = self.nearest_component.edgeId() + ":" + str(ratio)

                                    self.cut_line_drawable.show(False)
                                    self.highlight_drawable(self.perpendicular_line_drawable, True)
                                    return
                                else:
                                    self.highlight_drawable(self.perpendicular_line_drawable, False)
                            else:
                                self.perpendicular_line_drawable.show(False)
                        else:
                            self.perpendicular_line_drawable.show(False)

                        self.draw_line_drawable_at_positions(self.cut_line_drawable, self.split_start_hit_pos, self.split_hit_pos)

                    else:
                        (o, d) =  self.event.ray()
                        end_pos = ui.modeler.intersect_plane(self.split_start_hit_pos, self._view_normal_local, o, d)
                        self.split_hit_pos = end_pos
                        self.perpendicular_line_drawable.show(False)
                        self.draw_line_drawable_at_positions(self.cut_line_drawable, self.split_start_hit_pos, end_pos) 

                # CONTINUE EXTRUDING
                elif self.inset_sop is not None:
                    vec = ui.modeler.intersect_plane(self.hit_pos, self._view_normal_local, *self.event.ray()) - self.hit_pos
                    self.inset_sop.parm("inset").set(vec.length())

            # FIRST DRAG
            elif self.is_on_surface and ( abs(x - self.last_mouse_move_x) > hou.ui.scaledSize(2) or abs(y - self.last_mouse_move_y) > hou.ui.scaledSize(2) ):
                # CUT
                if self.cut_mode:
                    self.start_split()
                else:
                    if self.grouptype == 4 and not self.move_edges:
                        return
                    
                    elif self.grouptype == 4 and self.freeslide:
                        return

                    elif type(self.nearest_component) == hou.Polygon:
                        self.start_polygon_inseting()
                    
                    else:
                        self.start_moving(slide=self.slide, freeslide=self.freeslide)
                
                self.drag = True

            return True

        # MOUSE PRESS
        elif reason == hou.uiEventReason.Start:
            self.cut_mode = not self.device.isMiddleButton()
            self.drag = False
            self.press = True
            self.press_x = self.device.mouseX()
            self.press_y = self.device.mouseY()
            self.edit_sop = None
            self.split_sop = None
            self.inset_sop = None
            self.group_sop = None
            self.point_drawable.show(False)
            self.edge_line_drawable.show(False)

        # MOUSE RELEASE
        elif reason == hou.uiEventReason.Changed and self.press:
            if self.drag:
                if self.edit_sop is not None:
                    # FUSE SOURCE AND TARGET POINTS
                    if self.snap_point is not None:
                        sop = self.connect_new_sop("fuse::2.0", {"querygroup": self.edit_sop.evalParm("group"), "usetargetgroup": True, "targetgroup": str(self.snap_point.number()), "usetol3d": False, "usepositionsnapmethod": False, "algorithm": 1})
                        self.point_drawable.show(False)
                    
                    elif self.edit_sop.evalParm("slideonsurface"):
                        with hou.RedrawBlock() as rb:
                            sop = self.connect_new_sop("fuse::2.0", {"tol3d": 0.00001})
                            if sop.inputGeometry(0).intrinsicValue("pointcount") == sop.geometry().intrinsicValue("pointcount"):
                                sop.destroy()

                    self.perpendicular_line_drawable.show(False)

                    ui.VIEWER.endStateUndo()

                # FINISH SPLIT
                elif self.split_sop is not None:
                    self.finish_split()
                
                # FINISH EXTRUDING
                elif self.inset_sop is not None:
                    ui.VIEWER.endStateUndo()

            self.drag = False
            self.press = False

        self.hit()

    def hit(self):
        if ui.VIEWER.isWorldSpaceLocal():
            self.xform = hou.hmath.identityTransform()
        else:
            self.xform = ui.modeler.ancestor_object(self.subnet).worldTransform()
        
        self.xform_inverted = self.xform.inverted()

        tmp_vec = hou.Vector3()
        hit_uvw = hou.Vector3()
        self.hit_pos = hou.Vector3()
        hit_prim_number = self.geo.intersect(*self.event.ray(), self.hit_pos, tmp_vec, hit_uvw)
        if hit_prim_number > -1:
            self.hit_pos = self.hit_pos
            self.hit_prim = self.geo.prim(hit_prim_number)
            if self.hit_prim is not None:
                hit_normal = self.hit_prim.normal()     # HOUDINI BUG. THE INTERSECT METHOD CAN'T ALWAYS CALCULATE RIGHT NORMAL
                
                self._view_normal_local = hou.Vector3(0, 0, 1) * self.viewport.viewTransform().inverted().transposed() * self.xform.transposed()

                if (self.__class__.ignore_backfacing and self._view_normal_local.dot(hit_normal) > 0.01) or not self.__class__.ignore_backfacing:
                    prim_is_closed = self.hit_prim.isClosed()

                    prim_points = self.hit_prim.points()
                    
                    if prim_is_closed:
                        prim_points.append(prim_points[0])

                    offset = self.viewport.windowToViewportTransform().extractTranslates()

                    # FIND NEAREST EDGE
                    x = self.device.mouseX()
                    y = self.device.mouseY()
                    
                    CURSOR_VEC2 = hou.Vector2(x + offset[0], y + offset[1])
                    MIN_DIST_TO_EDGE = 9999.9999
                    CLOSEST_EDGE_POINT1 = None
                    CLOSEST_EDGE_POINT2 = None
                    CLOSEST_EDGE_POINT1_POS = None
                    CLOSEST_EDGE_POINT2_POS = None

                    for i in range(len(prim_points) - 1):
                        edge_point1 = prim_points[i]
                        edge_point2 = prim_points[i+1]

                        edge_point1_pos = edge_point1.position()
                        edge_point2_pos = edge_point2.position()

                        edge_vec = edge_point1_pos - edge_point2_pos
                        point_on_edge = self.hit_pos.pointOnSegment(edge_point1_pos, edge_point2_pos)
                        
                        xy = self.viewport.mapToScreen(point_on_edge * self.xform)
                        dist_to_edge = CURSOR_VEC2.distanceTo(xy)

                        if dist_to_edge < MIN_DIST_TO_EDGE:
                            MIN_DIST_TO_EDGE = dist_to_edge

                            CLOSEST_EDGE_POINT1 = edge_point1
                            CLOSEST_EDGE_POINT2 = edge_point2
                            
                            CLOSEST_EDGE_POINT1_POS = edge_point1_pos
                            CLOSEST_EDGE_POINT2_POS = edge_point2_pos

                    # FIND NEAREST COMPONENT AND GET IT'S DATA
                    dist_to_point1 = CURSOR_VEC2.distanceTo( self.viewport.mapToScreen(CLOSEST_EDGE_POINT1_POS * self.xform) )
                    dist_to_point2 = CURSOR_VEC2.distanceTo( self.viewport.mapToScreen(CLOSEST_EDGE_POINT2_POS * self.xform) )

                    # POINT 1
                    if dist_to_point1 <= self.tol:
                        self.nearest_component = CLOSEST_EDGE_POINT1
                        self.point_initial_pos = CLOSEST_EDGE_POINT1_POS
                        self.group = str(self.nearest_component.number())
                        self.grouptype = 3
                    
                    # POINT 2
                    elif dist_to_point2 <= self.tol:
                        self.nearest_component = CLOSEST_EDGE_POINT2
                        self.point_initial_pos = CLOSEST_EDGE_POINT2_POS
                        self.group = str(self.nearest_component.number())
                        self.grouptype = 3
                    
                    # EDGE
                    elif MIN_DIST_TO_EDGE <= self.tol:
                        self.nearest_component = self.geo.findEdge(CLOSEST_EDGE_POINT1, CLOSEST_EDGE_POINT2)
                        self.group = self.nearest_component.edgeId()
                        self.grouptype = 2
                    
                    # PRIM
                    else:
                        self.nearest_component = self.hit_prim
                        self.group = str(self.nearest_component.number())
                        self.grouptype = 3


                    # UPDATE DRAWABLES
                    typ = type(self.nearest_component)

                    # POINT
                    if typ == hou.Point:
                        xform = self.xform_inverted * hou.hmath.buildTranslate(self.nearest_component.position()) * self.xform
                        
                        # SPLIT DATA
                        self.split_hit_pos = self.nearest_component.position()
                        for vtx in self.hit_prim.vertices():
                            if vtx.point() == self.nearest_component:
                                self.splitloc = str(self.hit_prim.number()) + "v" + str(vtx.number())

                        # GET SLIDE VECTORS
                        self.point_slide_vectors = []
                        sel = hou.Selection((self.nearest_component,))
                        sel.convert(self.geo, hou.geometryType.Edges)
                        for edge in sel.edges(self.geo):
                            edge_pt1, edge_pt2 = edge.points()
                            if edge_pt1 == self.nearest_component:
                                nb_pos = edge_pt2.position()
                            else:
                                nb_pos = edge_pt1.position()
                            self.point_slide_vectors.append( ((nb_pos - self.point_initial_pos).normalized(), nb_pos) )

                        # GET SNAP NEIGHBOURS
                        self.point_snap_neighbours = []
                        for prim in self.nearest_component.prims():
                            for prim_point in prim.points():
                                if prim_point != self.nearest_component:
                                    self.point_snap_neighbours.append(prim_point)

                        self.point_drawable.setTransform(xform)
                        self.point_drawable.show(True)
                        self.edge_line_drawable.show(False)
                        self.highlight_drawable(self.point_drawable, False)
                        self.highlight_drawable(self.perpendicular_line_drawable, False)
                        self.is_boundary = self.is_point_boundary(self.nearest_component)

                    # EDGE
                    elif typ == hou.Edge:
                        (point1, point2) = self.nearest_component.points()
                        pos1 = point1.position()
                        pos2 = point2.position()
                        edge_vec = ( pos2 - pos1).normalized()
                        edge_center = (pos1 + pos2) / 2.0
                        edge_length = self.nearest_component.length()
                        rot_xform = hou.Vector3(0, 1, 0).matrixToRotateTo(edge_vec)
                        xform = self.xform_inverted *  hou.hmath.buildScale((edge_length, edge_length, edge_length)) * rot_xform * hou.hmath.buildTranslate(point1.position()) * self.xform

                        self.is_edge_center_highlighted = self.is_position_near_cursor(edge_center, x, y)

                        # SPLIT DATA
                        if self.is_edge_center_highlighted:
                            self.split_hit_pos = edge_center
                            ratio = 0.5
                        else:
                            self.split_hit_pos = self.hit_pos.pointOnSegment(pos1, pos2)
                            ratio = (self.split_hit_pos - pos1).length() / self.nearest_component.length()
                        
                        self.splitloc = self.nearest_component.edgeId() + ":" + str(ratio)

                        self.edge_line_drawable.setTransform(xform)
                        self.edge_line_drawable.show(True)
                        self.draw_point_drawable_at_position(self.point_drawable, edge_center)
                        self.highlight_drawable(self.point_drawable, self.is_edge_center_highlighted)

                        self.is_boundary = len(self.nearest_component.prims()) == 1
            
                    # PRIM
                    else:
                        # SPLIT DATA
                        self.split_hit_pos = self.hit_pos
                        self.splitloc = str(hit_prim_number) + "f:" + str(hit_uvw[0]) + "," + str(hit_uvw[1])

                        self.point_drawable.show(False)
                        self.edge_line_drawable.show(False)

                        self.highlight_drawable(self.point_drawable, False)
                        self.highlight_drawable(self.perpendicular_line_drawable, False)

                        self.is_boundary = False
                        for edge in self.nearest_component.edges():
                            if len(edge.prims()) == 1:
                                self.is_boundary = True
                                break

                    self.is_on_surface = True

                    return

        self.is_on_surface = False
        
        # HIDE ALL DRAWABLES
        self.point_drawable.show(False)
        self.edge_line_drawable.show(False)

    def onInterrupt(self, kwargs):
        self.point_drawable.show(False)
        self.edge_line_drawable.show(False)
        ui.VIEWER.clearPromptMessage()

    def onResume(self, kwargs):
        self.viewport = ui.VIEWER.curViewport()
        hou.ui.postEventCallback(self.show_prompt_message)

    def start_split(self):
        self.split_sop = True
        self.split_start_splitloc = self.splitloc
        
        self.split_start_hit_pos = self.split_hit_pos
        self.split_start_component = self.nearest_component

        if type(self.nearest_component) == hou.Edge and len(self.nearest_component.prims()) == 1:
            self.bridge_start_edge = self.nearest_component.edgeId()
        else:
            self.bridge_start_edge = None

    def finish_split(self):
        # FILL UNSHARED POINT
        if not self.is_on_surface or self.hit_prim.normal().dot(self._view_normal_local) < 0:
            with hou.undos.group("Modeler: Edge Fill"):
                sel = hou.Selection((self.split_start_component,))
                sel.convert(self.geo, hou.geometryType.Edges)
                group = sel.selectionString(self.geo)
                sop = self.connect_new_sop("polyfill", {"group": group, "fillmode": 0})
                if sop.geometry() is None:
                    sop.destroy()

        elif self.is_on_surface:
            # BRIDGE
            if self.bridge_start_edge is not None and type(self.nearest_component) == hou.Edge and self.split_start_component.prims()[0] != self.nearest_component.prims()[0]:
                with hou.undos.group("Modeler: Bridge"):
                    self.connect_new_sop("polybridge", {"srcgroup": self.bridge_start_edge, "dstgroup": self.nearest_component.edgeId(), "divisions": 1, "spinetype": 0 })

            # REGULAR SPLIT
            else:
                splitloc = self.split_start_splitloc + " " + self.splitloc

                with hou.undos.group("Modeler: Edge Split"):
                    sop = self.connect_new_sop("polysplit::2.0", {"splitloc": splitloc})
                    if sop.geometry() is None:
                        sop.destroy()
                    else:
                        split = splitloc.split()
                        if len(split) and "f" in split[0] and "f" in split[1]:
                            a, b = int(split[0].split("f")[0]), int(split[1].split("f")[0])
                            if a != b:
                                sop.setParms({ "grouptoggle": True, "groupname": "__split_edges__"})
                                sop = self.connect_new_sop("attribwrangle", {"group": "__split_edges__", "grouptype": 2, "snippet": "if (neighbourcount(0, @ptnum) == 2) removepoint(0, @ptnum, 1);"})
                            
        self.perpendicular_line_drawable.show(False)
        self.cut_line_drawable.show(False)

    def start_moving(self, slide, freeslide):
        ui.VIEWER.beginStateUndo("Modeler: PolyPen Moving")
        
        sop = self.get_display_sop()
        
        if sop is not None and sop.type().name() == "edit":
            self.edit_sop = sop
            self.edit_sop.parm("apply").pressButton()
            self.edit_sop.setParms({ "group": self.group, "grouptype": self.grouptype,
                                     "xformspace": 0, "switcher1": 0, "modeswitcher1": 0,
                                     "slideonsurface": slide,
                                     "px": self.hit_pos[0], "py": self.hit_pos[1], "pz": self.hit_pos[2] })

        else:
            self.edit_sop = self.connect_new_sop("edit", {"group": self.group, "grouptype": self.grouptype,
                                                 "slideonsurface": slide,
                                                 "px": self.hit_pos[0], "py": self.hit_pos[1], "pz": self.hit_pos[2] })
        
        self.can_snap = self.grouptype == 3
        self.slide_point = self.grouptype == 3 and slide == True and not freeslide

    def start_polygon_inseting(self):
        ui.VIEWER.beginStateUndo("Modeler: PolyPen Polygon Inseting")
        sop = self.get_display_sop()
        self.inset_sop = self.connect_new_sop("polyextrude::2.0", {"group": self.group})

    def onDraw(self, kwargs):
        handle = kwargs["draw_handle"]
        self.edge_line_drawable.draw(handle)
        self.cut_line_drawable.draw(handle)
        self.perpendicular_line_drawable.draw(handle)
        self.point_drawable.draw(handle)

    def get_display_sop_std_mode(self):
        return self.subnet.displayNode()

    def get_display_sop_topo_mode(self):
        return self.ray_sop.inputs()[0]

    def connect_new_sop_std_mode(self, type_name, parms_dict):
        display = self.subnet.displayNode()
        if display is None:
            node = self.subnet.createNode(type_name)
            node.setParms(parms_dict)
            node.setInput(0, self.subnet.indirectInputs()[0])
        else:
            node = display.createOutputNode(type_name)
            node.setParms(parms_dict)
            node.setDisplayFlag(True)
            node.setRenderFlag(True)
        return node

    def connect_new_sop_topo_mode(self, type_name, parms_dict):
        ray_input = self.ray_sop.inputs()[0]
        indirect_input = self.subnet.indirectInputs()[0]
        if ray_input == indirect_input.input():
            node = self.subnet.createNode(type_name)
            node.setParms(parms_dict)
            node.setInput(0, indirect_input)
            self.ray_sop.setInput(0, node)
        else:
            node = ray_input.createOutputNode(type_name)
            node.setParms(parms_dict)
            self.ray_sop.setInput(0, node)
        return node

    def is_point_boundary(self, point):
        sel = hou.Selection((self.nearest_component,))
        sel.convert(self.geo, hou.geometryType.Edges)
        for edge in sel.edges(self.geo):
            if len(edge.prims()) == 1:
                return True
        return False

    def is_position_near_cursor(self, position, cursor_x, cursor_y):
        offset = self.viewport.windowToViewportTransform().extractTranslates()
        return (self.viewport.mapToScreen(position * self.xform)).distanceTo(hou.Vector2(cursor_x + offset[0], cursor_y + offset[1])) <= self.tol

    def draw_point_drawable_at_position(self, drawable, position):
        xform = self.xform_inverted * hou.hmath.buildTranslate(position) * self.xform
        drawable.setTransform(xform)
        drawable.show(True)

    def draw_line_drawable_at_positions(self, drawable, position1, position2):
        vec = (position2 - position1)
        length = vec.length()
        xform = self.xform_inverted *  hou.hmath.buildScale((length, length, length)) * hou.Vector3(0, 1, 0).matrixToRotateTo(vec) * hou.hmath.buildTranslate(position1) * self.xform
        drawable.setTransform(xform)
        drawable.show(True)

    def highlight_drawable(self, drawable, value):
        drawable.setParams({ "highlight_mode": hou.drawableHighlightMode.MatteOverGlow if value else hou.drawableHighlightMode.Matte })

    def onParmChangeEvent(self, kwargs):
        parm_name = kwargs['parm_name']
        state_parms = kwargs['state_parms']

        if parm_name == "ignore_backfacing":
            self.__class__.ignore_backfacing = state_parms["ignore_backfacing"]["value"]
        
        elif parm_name == "slide":
            self.__class__.slide = state_parms["slide"]["value"]

        elif parm_name == "freeslide":
            self.__class__.freeslide = state_parms["freeslide"]["value"]
        
        elif parm_name == "move_edges":
            self.__class__.move_edges = state_parms["move_edges"]["value"]

        elif parm_name == "apply_to_loop":
            sop = self.get_display_sop()
            typ = sop.type().name()
            if typ == "dissolve::2.0":
                group = sop.evalParm("group")
                if len(group.split("p")) == 2:
                    input_geo = sop.inputGeometry(0)
                    edge = input_geo.globEdges(group)[0]
                    loop = input_geo.edgeLoop((edge, edge), hou.componentLoopType.Extended, True, False, False)
                    group = " ".join([edge.edgeId() for edge in loop if edge is not None])
                    sop.setParms({ "group": group, "coltol": 180 })

            elif typ == "polysplit::2.0":
                sop.parm("pathtype").set( not sop.parm("pathtype").evalAsInt() )

            elif typ == "polyextrude::2.0":
                i = sop.inputs()
                if i[0].type().name() == "polyextrude::2.0":
                    sop.parm("inset").set( i[0].evalParm("inset") )

    def onCommand(self, kwargs):
        if kwargs['command'] == "click":
            # self.hit()
            if self.is_on_surface:
                with hou.undos.group("Modeler: Edge Delete"):
                    # DISSOLVE EDGE
                    if type(self.nearest_component) == hou.Edge:
                        sop = self.connect_new_sop("dissolve::2.0", { "group": self.nearest_component.edgeId(), "deldegeneratebridges": True, "coltol": 30, "reminlinepts": True })

                    # BLAST POINTS OR DISSOLVE POINT EDGES
                    elif type(self.nearest_component) == hou.Point:
                        # DISSOLVE POINT EDGES
                        if len(self.nearest_component.prims()) >= 3:
                            sel = hou.Selection((self.nearest_component,))
                            sel.convert(self.geo, hou.geometryType.Edges)
                            sop = self.connect_new_sop("dissolve::2.0", {"group": sel.selectionString(self.geo), "deldegeneratebridges": True, "reminlinepts": False})
                        
                        # BLAST POINT
                        else:
                            sop = self.connect_new_sop("blast", {"group": str(self.nearest_component.number()), "grouptype": 3})

                    # BLAST PRIM
                    else:
                        sop = self.connect_new_sop("blast", {"group": str(self.nearest_component.number())})
        
        elif kwargs['command'] == "toggle_slide":
            self.__class__.slide = not self.__class__.slide
            kwargs["state_parms"]["slide"]["value"] = self.__class__.slide

        elif kwargs['command'] == "move_loop":
            sop = self.get_display_sop()
            node_type = sop.type().name()

            if node_type == "edit":
                if type(self.nearest_component) == hou.Edge:
                    loop = self.geo.edgeLoop((self.nearest_component, self.nearest_component), hou.componentLoopType.Extended, True, False, False)
                    group = " ".join([edge.edgeId() for edge in loop if edge is not None])
                    sop.parm("group").set(group)

        elif kwargs['command'] == "match_loop_profile":
            sop = self.get_display_sop()
            if sop is not None and sop.type().name() == "polysplit::2.0":
                match = sop.evalParm("parallellooptoggle")
                if match:
                    flip = sop.evalParm("parallelfliptoggle")
                    if flip:
                        sop.parm("parallelfliptoggle").set(False)
                        sop.parm("parallellooptoggle").set(False)
                    else:
                        sop.parm("parallelfliptoggle").set(True)
                else:
                    sop.parm("parallellooptoggle").set(True)

                ui.shift_cursor()

def register_polypen_state():
    template = hou.ViewerStateTemplate("modeler::polypen", "PolyPen", hou.sopNodeTypeCategory())
    template.bindFactory(PolyPenStateTemplate)
    template.bindParameter( hou.parmTemplateType.Toggle, name="ignore_backfacing", label="Ignore Backfacing", default_value=PolyPenStateTemplate.ignore_backfacing )
    template.bindParameter( hou.parmTemplateType.Toggle, name="move_edges", label="Move Edges", default_value=PolyPenStateTemplate.move_edges )
    template.bindParameter( hou.parmTemplateType.Toggle, name="freeslide", label="Free Points Slide  |  Move Single Edge", default_value=PolyPenStateTemplate.freeslide )
    template.bindParameter( hou.parmTemplateType.Toggle, name="slide", label="Slide", default_value=PolyPenStateTemplate.slide )
    template.bindParameter( hou.parmTemplateType.Button, name="apply_to_loop", label="Apply To Loop", align=True )
    template.bindIcon("MODELER_polypen_cursor")
    hou.ui.registerViewerState(template)


def Knife():
    if ui.VIEWER.currentState() != "modeler::knife":
        sop, group, grouptype, empty = ui.modeler.selection()
        if sop is not None:
            with hou.RedrawBlock() as rb:    
                with hou.undos.group("Modeler: Knife"):
                    KnifeStateTemplate.subnet = sop.createOutputNode("subnet", "knife1")
                    KnifeStateTemplate.subnet.setDisplayFlag(True)
                    KnifeStateTemplate.subnet.setRenderFlag(True)
                    KnifeStateTemplate.subnet.setCurrent(True, True)
                    
                    if not empty and grouptype == hou.geometryType.Primitives:
                        KnifeStateTemplate.group = group
                    else:
                        KnifeStateTemplate.group = "!_3d_hidden_primitives"

                    KnifeStateTemplate.geo = KnifeStateTemplate.subnet.geometry()
                    KnifeStateTemplate.group_center = KnifeStateTemplate.geo.primBoundingBox(KnifeStateTemplate.group).center()
                    KnifeStateTemplate.xform = ui.modeler.ancestor_object(sop).worldTransform()
                    hou.ui.waitUntil(lambda: True)
                    ui.VIEWER.setCurrentState("modeler::knife")

                    ui.shift_cursor()
        else:
            ui.prompt("Polygon(s) must be selected")

class KnifeStateTemplate():
    hit_point = hit_point_string = hit_edge = hit_prim = None
    last_mouse_move_x = last_mouse_move_y = None
    edge_line_drawable_geo = hou.Geometry()
    line = hou.sopNodeTypeCategory().nodeVerb("line")
    line.execute(edge_line_drawable_geo, [])
    del line

    edge_line_drawable_params = {
        "color1": hou.Color(1, 0.9, 0.3),
        "style": hou.drawableGeometryLineStyle.Plain,
        "line_width": hou.ui.scaledSize(2),
        "fade_factor": 1.0,
    }                                                                                                

    def show_prompt_message(self):
        ui.VIEWER.setPromptMessage("LMB: cut; MMB: aligned cut.")

    def __init__(self, scene_viewer, state_name):
        self.edge_line_drawable = hou.GeometryDrawable(ui.VIEWER, hou.drawableGeometryType.Line, "edge_line_drawable", params=self.edge_line_drawable_params)
        self.edge_line_drawable.setGeometry(self.edge_line_drawable_geo)
        self.press = False

    def onExit(self, kwargs):
        try:
            sop = self.subnet.displayNode()
            if sop is not None:
                sop = sop.createOutputNode("groupdelete")
                sop.parm("group1").set("*")
                sop.setDisplayFlag(True)
        except hou.ObjectWasDeleted:
            pass      
        ui.qt_app.restoreOverrideCursor()

    def onGenerate(self, kwargs):
        self.show_prompt_message()

    def onInterrupt(self, kwargs):
        self.edge_line_drawable.show(False)
        ui.VIEWER.clearPromptMessage()

    def onResume(self, kwargs):
        hou.ui.postEventCallback(self.show_prompt_message)

    def onDraw(self, kwargs):
        handle = kwargs["draw_handle"]
        self.edge_line_drawable.draw(handle)

    def onMouseEvent(self, kwargs):
        # MOUSE DRAG
        if kwargs["ui_event"].reason() == hou.uiEventReason.Active and self.press:
            (o, d) = kwargs["ui_event"].ray()
            view_normal_local = hou.Vector3(0.0, 0.0, 1.0) * self.xform_inverted_transposed * self.xform.transposed()
            self.end_pos = ui.modeler.intersect_plane(self.group_center, view_normal_local, o, d)

            if self.align:
                vec = (self.start_pos - self.end_pos)

                vec1 = hou.Vector3(0.0, 1.0, 0.0) * self.xform1
                vec2 = hou.Vector3(1.0, 1.0, 0.0).normalized() * self.xform1
                vec3 = hou.Vector3(1.0, 0.0, 0.0) * self.xform1
                vec4 = hou.Vector3(1.0, -1.0, 0.0).normalized() * self.xform1
                vec5 = hou.Vector3(0.0, -1.0, 0.0) * self.xform1
                vec6 = hou.Vector3(-1.0, -1.0, 0.0).normalized() * self.xform1
                vec7 = hou.Vector3(-1.0, 0.0, 0.0) * self.xform1
                vec8 = hou.Vector3(-1.0, 1.0, 0.0).normalized() * self.xform1

                dot1 = vec.dot(vec1)
                dot2 = vec.dot(vec2)
                dot3 = vec.dot(vec3)
                dot4 = vec.dot(vec4)
                dot5 = vec.dot(vec5)
                dot6 = vec.dot(vec6)
                dot7 = vec.dot(vec7)
                dot8 = vec.dot(vec8)

                max_dot = max(dot1, dot2, dot3, dot4, dot5, dot6, dot7, dot8)

                if max_dot == dot1:
                    self.end_pos = self.start_pos - vec1 * dot1

                elif max_dot == dot2:
                    self.end_pos = self.start_pos - vec2 * dot2

                elif max_dot == dot3:
                    self.end_pos = self.start_pos - vec3 * dot3

                elif max_dot == dot4:
                    self.end_pos = self.start_pos - vec4 * dot4

                elif max_dot == dot5:
                    self.end_pos = self.start_pos - vec5 * dot5

                elif max_dot == dot6:
                    self.end_pos = self.start_pos - vec6 * dot6

                elif max_dot == dot7:
                    self.end_pos = self.start_pos - vec7 * dot7

                else:
                    self.end_pos = self.start_pos - vec8 * dot8

            self.draw_line_drawable_at_positions(self.edge_line_drawable, self.start_pos, self.end_pos)

        # MOUSE PRESS
        elif kwargs["ui_event"].reason() == hou.uiEventReason.Start:
            self.align = kwargs["ui_event"].device().isMiddleButton()
            (o, d) = kwargs["ui_event"].ray()
            self.xform_inverted_transposed = ui.VIEWER.curViewport().viewTransform().inverted().transposed()
            self.xform1 = self.xform_inverted_transposed * self.xform.transposed()
            view_normal_local = hou.Vector3(0.0, 0.0, 1.0) * self.xform_inverted_transposed * self.xform.transposed()
            self.start_pos = ui.modeler.intersect_plane(self.group_center, view_normal_local, o, d)

            self.press = True
            
        # MOUSE RELEASE
        elif kwargs["ui_event"].reason() == hou.uiEventReason.Changed and self.press:                
            self.edge_line_drawable.show(False)

            with hou.undos.group("Modeler: Knife"):
                display = self.subnet.displayNode()
                if display is None:
                    node = self.subnet.createNode("clip")
                    node.setParms({ "group": self.group, "clipop": 2, "newg": True, "above": "__above__", "below": "__below__" })
                    node.setInput(0, self.subnet.indirectInputs()[0])
                else:
                    node = display.createOutputNode("clip")
                    node.setParms({ "group": "__above__ __below__", "clipop": 2 })
                    node.setDisplayFlag(True)

                c = (self.end_pos + self.start_pos) / 2.0
                viewport = ui.VIEWER.curViewport()
                v = viewport.mapToScreen(c * self.xform)
                v = viewport.mapToWorld(*v)[0] * self.xform.transposed()
                up = (self.end_pos - self.start_pos).normalized()
                right_local = up.cross(v)
                node.parmTuple("dir").set(right_local)
                node.parmTuple("origin").set( c )
                self.press = False

    def draw_line_drawable_at_positions(self, drawable, position1, position2):
        vec = (position2 - position1)
        length = vec.length()
        xform = self.xform.inverted() *  hou.hmath.buildScale((length, length, length)) * hou.Vector3(0, 1, 0).matrixToRotateTo(vec) * hou.hmath.buildTranslate(position1) * self.xform
        drawable.setTransform(xform)
        drawable.show(True)

def register_knife_state():
    template = hou.ViewerStateTemplate("modeler::knife", "Knife", hou.sopNodeTypeCategory())
    template.bindFactory(KnifeStateTemplate)
    template.bindIcon("MODELER_knife")
    hou.ui.registerViewerState(template)

register_magnet_state()
register_polypen_state()
register_knife_state()