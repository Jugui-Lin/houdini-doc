import hou
import os.path
import shutil
import glob
import fileinput

def NodeNameFromFile(file):

    ext=''
    if (file[0:3]).lower()=="op:":

        return "_".join(file.replace(":","").split("/"))

    if file:
        return ext+os.path.splitext(os.path.basename(file))[0]
    return "";


def SetNodeFromFile(args):
    for node in args['items']:
        try:
            name=NodeNameFromFile(node.parm('tex0').eval())

            if name:
                node.setName(name, True);
        except:
            pass

def parm_exist(node, parm):
    return node.parmTuple(parm) != None

def LoadAllFromFile(args):
    node=args["node"]
    src=node.parm('tex0').eval()
 
    posy=1.5
    if src:
        
        name=NodeNameFromFile(node.parm('tex0').eval())
        node.setName(name, True);
        
        for file in glob.glob(os.path.dirname(src)+"/*.*"):
            if os.path.basename(file)!=os.path.basename(node.parm('tex0').eval()):
                if os.path.splitext(file)[1].lower()[1:] in ["jpg","exr","bmp","tga","tiff","jpeg","hdr","pic","png"]:	
                    tnp=False

                    typ = guessType(file)
                    if typ==False:
                        typ=["Diffuse"]

                    #if (typ[0]=="Normal"):
                    #	tmp=node.parent().createNode("redshift::NormalMap", NodeNameFromFile(file) )
                    
                    #else:
                    tmp=node.parent().createNode("redshift::TextureSampler", NodeNameFromFile(file) )
                    
                    tmp.parm('tex0').set(file.replace('/','/'))
                    tmp.setColor(node.color())
                    tmp.setPosition([node.position()[0],node.position()[1]-posy])
                    posy=posy+1.5

def ExploreTexture(args):
    for node in args['items']:
        try:
            src = node.evalParm('tex0')
            if os.path.isfile(src):
                os.startfile(src)	
        except:
            pass


def ReplaceByCop(args):
    for node in args['items']:
        if parm_exist(node, 'tex0') and node.evalParm('tex0')[0:3].lower()!="op:":
            comp=hou.node('/img').createNode('img', node.name())
            comp.moveToGoodPosition()
            file=comp.createNode('file')
            file.parm('linearize').set(False)   
            file.moveToGoodPosition()
            out=comp.createNode('null', 'output')
            out.moveToGoodPosition()
            out.setInput(0, file,0)
            file.parm('filename1').set(node.evalParm('tex0'))
            node.parm('tex0').set("op:"+comp.path()+"/"+out.name())
            node.setColor(hou.Color(0.996,0.933,0))
            try:
                name=NodeNameFromFile(node.parm('tex0').eval())
                if name:
                    node.setName(name, True);

            except:
                pass


def getContainerNode(node):
    while True:
        node=node.parent()
        if node==None:
            break

        if node.type().name()=="root":
            break
        
        if node.type().name()=="redshift_vopnet" or  node.type().name()=="matnet":
            break

    return node

def SetOGL( type, args, warning=True):

    parm_group = False
    vpname="OpenGL Viewport"

    for selItem in args['items']:
     
        if selItem.type().name()=="redshift::TextureSampler":
            
            nodes = getRelatedMaterials(selItem, args['ctrlclick'] or args['cmdclick'], warning)
 
            context=getMatContextType(selItem)

            for node in nodes:
                if node:
                 
                    mapParm=False
                    useParm=False

                    if type=="diffuse":
                        mapParm=node.parm("n_diffuse")
                 
                        node.parm("ogl_diffr").set(1)
                        node.parm("ogl_diffg").set(1)
                        node.parm("ogl_diffb").set(1)

                        node.parm("ogl_texuvset1").setExpression('chs("'+node.relativePathTo(selItem)+'/tspace_id")',  hou.exprLanguage.Hscript)
                        node.parm("ogl_tex_wrap1").setExpression('ifs( ch("'+node.relativePathTo(selItem)+'/wrapU"),"repeat","decal")',  hou.exprLanguage.Hscript)
                        node.parm("ogl_tex_vwrap1").setExpression('ifs(  ch("'+node.relativePathTo(selItem)+'/wrapV"),"repeat","decal")',  hou.exprLanguage.Hscript)


                    if type=="metallic":
                        mapParm=node.parm("ogl_metallicmap")
                        useParm=node.parm("ogl_use_metallicmap")
                        #node.parm("ogl_metallic").set(1)
                    
                    if type=="roughness":
                        mapParm=node.parm("ogl_roughmap")
                        useParm=node.parm("ogl_use_roughmap")


                    if type=="specular":
                        mapParm=node.parm("ogl_specmap")
                        useParm=node.parm("ogl_use_specmap")

                    if type=="normal":
 
                        mapParm=node.parm("ogl_normalmap")
                        useParm=node.parm("ogl_use_normalmap")	
                        try:
                            node.parm("ogl_normalmap_scale").setExpression('ch("'+ node.relativePathTo(selItem.outputs()[0])+'/scale")')  #fix this for shopnet
                        except:
                            pass


                    if type=="bump":
                        mapParm=node.parm("ogl_bumpmap")
                        useParm=node.parm("ogl_use_bumpmap")	
                        
                    if type=="displacement":
                     
                        try:
                            link=[] 
                            def recurLinks(n):
                                for i in n.outputs():
                                    if not i in link:
                                      link.append(i)
                                    recurLinks(i)
                                return link
                            res=recurLinks(selItem )

                            for item in res:
                                if item.type().name()=="redshift::Displacement":
                                    node.parm("ogl_displacescale").setExpression('ch("'+ node.relativePathTo( item )+'/scale")')
                                    break;
                        except:
                            pass

                        mapParm=node.parm("ogl_displacemap")
                        useParm=node.parm("ogl_use_displacemap")	

                    if type=="displacmentParms":
                        node.parm("ogl_displacescale").setExpression('ch("'+ node.relativePathTo(selItem)+'/scale")')
             

                    if type=="emission":
                        mapParm=node.parm("ogl_emissionmap")
                        useParm=node.parm("ogl_use_emissionmap")	

                    if type=="occlusion":
                        mapParm=node.parm("ogl_occlusionmap")
                        useParm=node.parm("ogl_use_occlusionmap")


                    if type=="emission":
                        mapParm=node.parm("ogl_emissionmap")
                        useParm=node.parm("ogl_use_emissionmap")


                    if type=="coat_int":
                        mapParm=node.parm("ogl_coat_intensity_map")
                        useParm=node.parm("ogl_use_coat_intensity_map")


                    if type=="coat_ruff":
                        mapParm=node.parm("ogl_coat_roughness_map")
                        useParm=node.parm("ogl_use_coat_roughness_map")


                    if useParm:
                        useParm.set(True)


                    if mapParm:
                        mapParm.setExpression('chs("'+node.relativePathTo(selItem)+'/tex0")',  hou.exprLanguage.Hscript)

                        if not (selItem.evalParm('tex0')[0:3]).lower()=="op:":
                            selItem.setColor( hou.Color(0.475, 0.812, 0.204) )
                        #useParm.set(True)


def unsetOGLAll(args):
    node=args['node']
    maps=["n_diffuse","ogl_metallicmap","ogl_roughmap","ogl_specmap","ogl_normalmap","ogl_bumpmap","ogl_displacemap","ogl_emissionmap","ogl_occlusionmap","ogl_emissionmap","ogl_coat_intensity_map","ogl_coat_roughness_map"]

    for item in getRelatedMaterials(node, args['ctrlclick'] or args['cmdclick']):
        for parm in maps:
            if item.evalParm(parm)== node.evalParm("tex0"):
                item.parm(parm).deleteAllKeyframes()
                item.parm(parm).set("");

def getBindTarget(node):

    tmp = filter(lambda x:(x.type().name()=="redshift::Material" or x.type().name()=="redshift::TextureSampler" or x.type().name()=="redshift::RSColorConstant"),  node.inputAncestors())
    out=None;

    for item in tmp:
        if out==None:
            out=item

        if item.type().name()=="redshift::Material" and (out.type().name()=="redshift::RSColorConstant" or out.type().name()=="redshift::TextureSampler"):
            out=item

        if item.type().name()=="redshift::TextureSampler" and out.type().name()=="redshift::RSColorConstant":
            out=item

    return out  		



def  SetOGLOverride(args):


    node=args['node']

    for item in getRelatedMaterials(node, args['ctrlclick'] or args['cmdclick'], True):
        try:
            item.parm("diff_override").set(node.evalParm("tex0"))
            item.parm("ogl_solo").set(1)
            item.parm('ogl_solo').pressButton();
        except:
            pass
                

def  UnsetOGLOverride(args):


    node=args['node']

    for item in getRelatedMaterials(node, args['ctrlclick'] or args['cmdclick'], True):
        try:
            item.parm("diff_override").set("")
            item.parm("ogl_solo").set(0)
            item.parm('ogl_solo').pressButton();
        except:
            pass
                
 


def findMat(n, justCheck=False):

    if n:
        targets = filter(lambda x:x.type().name()=="redshift::Material",  n.inputAncestors())

        trg=False

        if justCheck:
            return len(targets)>0

        if len(targets)==1:
            trg=targets[0]

        if len(targets)>1:
            opt=[] 
            nopt=[]
            for item in targets:
                opt.append(item.name())
                nopt.append(item)
                
                
            #res=hou.ui.selectFromList(opt, default_choices=(), exclusive=True, message="Select the Redshift Material to use for OpenGL", title=None, column_header="Materials", num_visible_rows=10, clear_on_cancel=False, width=0, height=0)
     
            for item in targets:
                if item.color() == n.color():
                    item.setColor(hou.Color(0.6,0.6,0.6))
                
        return trg 
    return False

def getMatContextType(node):
    if node.parent().path()=="/mat":
        return "matnet"

    return getContainerNode(node).type().name()


def InitOGL(n, srcMat=False):
    
    hou_node=False


    context=getMatContextType(n)
 

    if context=="matnet":
        hou_node=n
 
        if srcMat:
            srcMat.setColor( hou_node.color() )


    if context=="redshift_vopnet":
        hou_node = getContainerNode(n)
        if srcMat==False:
            srcMat=findMat(n)
    
        if srcMat:
            srcMat.setColor( n.color() )

    if hou_node:
        # Code for /obj/shopnet1/redshift_vopnet1

        hou_parm_template_group = hou.ParmTemplateGroup()

        hou_parm_template = hou.FolderParmTemplate("Redshift_SHOP_parmSwitcher3", "Redshift", folder_type=hou.folderType.Tabs, default_value=0, ends_tab_group=False)

        hou_parm_template2 = hou.IntParmTemplate("RS_matprop_ID", "Material ID", 1, default_value=([0]), min=0, max=100, min_is_strict=True, max_is_strict=False, naming_scheme=hou.parmNamingScheme.Base1, menu_items=([]), menu_labels=([]), icon_names=([]), item_generator_script="", item_generator_script_language=hou.scriptLanguage.Python, menu_type=hou.menuType.Normal, menu_use_token=False)
        hou_parm_template.addParmTemplate(hou_parm_template2)

        hou_parm_template2 = hou.SeparatorParmTemplate("sepparm5")
        hou_parm_template.addParmTemplate(hou_parm_template2)
        hou_parm_template_group.append(hou_parm_template)

        hou_parm_template = hou.FolderParmTemplate("Redshift_SHOP_parmSwitcher3_1", "OpenGL", folder_type=hou.folderType.Tabs, default_value=0, ends_tab_group=False)

        hou_parm_template2 = hou.FolderParmTemplate("fGlobal", "Global", folder_type=hou.folderType.Collapsible, default_value=0, ends_tab_group=False)
        hou_parm_template2.setTags({"group_type": "collapsible"})

        hou_parm_template3 = hou.ToggleParmTemplate("ogl_light", "OGL Use Lighting", default_value=True)
        hou_parm_template2.addParmTemplate(hou_parm_template3)

        hou_parm_template3 = hou.ToggleParmTemplate("ogl_lighttwoside", "Use Two Sided Lighting", default_value=False)
        hou_parm_template3.setHelp("None")
        hou_parm_template3.setTags({"cook_dependent": "1", "spare_category": "OpenGL"})
        hou_parm_template2.addParmTemplate(hou_parm_template3)

        hou_parm_template3 = hou.ToggleParmTemplate("ogl_use_geo_color", "Enable Geometry Color", default_value=False)
        hou_parm_template3.setHelp("When enabled, the color on the geometry (Cd) is multiplied by the material color. When off, it is ignored.")
        hou_parm_template3.setTags({"cook_dependent": "1", "ogl_use_geo_color": "0", "spare_category": "OpenGL"})
        hou_parm_template2.addParmTemplate(hou_parm_template3)

        hou_parm_template3 = hou.ToggleParmTemplate("ogl_use_packed_color", "Enable Packed Color", default_value=False)
        hou_parm_template3.setHelp("When enabled, the color on the packed primitive (Cd) is multiplied by the material color. When off, it is ignored.")
        hou_parm_template3.setTags({"cook_dependent": "1", "spare_category": "OpenGL"})
        hou_parm_template2.addParmTemplate(hou_parm_template3)

        hou_parm_template3 = hou.ToggleParmTemplate("ogl_disable_tex", "Disable All Textures", default_value=False)
        hou_parm_template3.setScriptCallback("import hou;tmp=not hou.pwd().evalParm('ogl_disable_tex');hou.pwd().parm(\"ogl_use_metallicmap\").set(tmp);hou.pwd().parm(\"ogl_use_roughmap\").set(tmp);hou.pwd().parm(\"ogl_use_specmap\").set(tmp);hou.pwd().parm(\"ogl_use_normalmap\").set(tmp);hou.pwd().parm(\"ogl_use_bumpmap\").set(tmp);hou.pwd().parm(\"ogl_use_opacitymap\").set(tmp);hou.pwd().parm(\"ogl_use_emissionmap\").set(tmp);hou.pwd().parm(\"ogl_use_occlusionmap\").set(tmp);hou.pwd().parm(\"ogl_use_coat_intensity_map\").set(tmp);hou.pwd().parm(\"ogl_use_coat_roughness_map\").set(tmp);")
        hou_parm_template3.setScriptCallbackLanguage(hou.scriptLanguage.Python)
        hou_parm_template3.setTags({"script_callback": "import hou;tmp=not hou.pwd().evalParm('ogl_disable_tex');hou.pwd().parm(\"ogl_use_metallicmap\").set(tmp);hou.pwd().parm(\"ogl_use_roughmap\").set(tmp);hou.pwd().parm(\"ogl_use_specmap\").set(tmp);hou.pwd().parm(\"ogl_use_normalmap\").set(tmp);hou.pwd().parm(\"ogl_use_bumpmap\").set(tmp);hou.pwd().parm(\"ogl_use_opacitymap\").set(tmp);hou.pwd().parm(\"ogl_use_emissionmap\").set(tmp);hou.pwd().parm(\"ogl_use_occlusionmap\").set(tmp);hou.pwd().parm(\"ogl_use_coat_intensity_map\").set(tmp);hou.pwd().parm(\"ogl_use_coat_roughness_map\").set(tmp);", "script_callback_language": "python"})
        hou_parm_template2.addParmTemplate(hou_parm_template3)

        hou_parm_template3 = hou.SeparatorParmTemplate("sepparm3")
        hou_parm_template2.addParmTemplate(hou_parm_template3)

        hou_parm_template3 = hou.StringParmTemplate("diff_override", "Override", 1, default_value=([""]), naming_scheme=hou.parmNamingScheme.Base1, string_type=hou.stringParmType.FileReference, menu_items=([]), menu_labels=([]), icon_names=([]), item_generator_script="", item_generator_script_language=hou.scriptLanguage.Python, menu_type=hou.menuType.StringReplace)
        hou_parm_template3.setConditional(hou.parmCondType.DisableWhen, "{ ogl_solo == 0 }")
        hou_parm_template3.setJoinWithNext(True)
        hou_parm_template2.addParmTemplate(hou_parm_template3)

        hou_parm_template3 = hou.ToggleParmTemplate("ogl_solo", "Enable", default_value=False)
        hou_parm_template3.setScriptCallback("import hou; r=hou.pwd(); r.parm('ogl_disable_tex').set(r.evalParm('ogl_solo')); r.parm('ogl_disable_tex').pressButton();")
        hou_parm_template3.setScriptCallbackLanguage(hou.scriptLanguage.Python)
        hou_parm_template3.setTags({"export_disable": "1", "script_callback": "import threading; import hou; r=hou.pwd(); r.parm('ogl_disable_tex').set(r.evalParm('ogl_solo')); r.parm('ogl_disable_tex').pressButton(); threading.Timer(0.01, lambda:r.parm('ogl_use_geo_color').pressButton() ).start() ", "script_callback_language": "python"})
        hou_parm_template2.addParmTemplate(hou_parm_template3)
        hou_parm_template.addParmTemplate(hou_parm_template2)

        hou_parm_template2 = hou.FolderParmTemplate("fDiffuse", "Diffuse", folder_type=hou.folderType.Collapsible, default_value=0, ends_tab_group=False)
        hou_parm_template2.setTags({"group_type": "collapsible"})

        hou_parm_template3 = hou.SeparatorParmTemplate("sepparm4")
        hou_parm_template2.addParmTemplate(hou_parm_template3)

        hou_parm_template3 = hou.FloatParmTemplate("ogl_diff", "OGL Diffuse", 3, default_value=([1, 1, 1]), min=0, max=10, min_is_strict=False, max_is_strict=False, look=hou.parmLook.ColorSquare, naming_scheme=hou.parmNamingScheme.RGBA)
        hou_parm_template2.addParmTemplate(hou_parm_template3)

        hou_parm_template3 = hou.StringParmTemplate("n_diffuse", "Diffuse Map 1", 1, default_value=([""]), naming_scheme=hou.parmNamingScheme.Base1, string_type=hou.stringParmType.FileReference, menu_items=([]), menu_labels=([]), icon_names=([]), item_generator_script="", item_generator_script_language=hou.scriptLanguage.Python, menu_type=hou.menuType.StringReplace)
        hou_parm_template3.setConditional(hou.parmCondType.DisableWhen, "{ ogl_solo == 1 }")
        hou_parm_template2.addParmTemplate(hou_parm_template3)

        hou_parm_template3 = hou.FloatParmTemplate("ogl_diff_intensity", "Diffuse Intensity", 1, default_value=([1]), min=0, max=2, min_is_strict=False, max_is_strict=False, look=hou.parmLook.Regular, naming_scheme=hou.parmNamingScheme.Base1)
        hou_parm_template3.setHelp("The diffuse intensity multiplies the Diffuse color, allowing it to be easily adjusted without affecting the its hue or saturation.")
        hou_parm_template3.setTags({"cook_dependent": "1", "spare_category": "OpenGL"})
        hou_parm_template2.addParmTemplate(hou_parm_template3)

        hou_parm_template3 = hou.FloatParmTemplate("ogl_diff_rough", "Diffuse Roughness", 1, default_value=([0.2]), min=0, max=1, min_is_strict=False, max_is_strict=False, look=hou.parmLook.Regular, naming_scheme=hou.parmNamingScheme.Base1)
        hou_parm_template3.setHelp("The diffuse roughness determines the falloff of the Oren-Nader shading model used for diffuse lighting.")
        hou_parm_template3.setTags({"cook_dependent": "1", "spare_category": "OpenGL"})
        hou_parm_template2.addParmTemplate(hou_parm_template3)

        hou_parm_template3 = hou.ToggleParmTemplate("ogl_use_diff", "Enable Diffuse", default_value=True)
        hou_parm_template3.setHelp("Toggles contribution of the diffuse color. When off, the material will have no diffuse lighting.")
        hou_parm_template3.setTags({"cook_dependent": "1", "spare_category": "OpenGL"})
        hou_parm_template2.addParmTemplate(hou_parm_template3)

        hou_parm_template3 = hou.ToggleParmTemplate("ogl_use_diffuse_map_alpha", "Use Diffuse Map Alpha", default_value=True)
        hou_parm_template3.setHelp("When enabled, the alpha channel of the base diffuse map is used to determine\n    the surface's opacity. When disabled, it is ignored.")
        hou_parm_template3.setTags({"cook_dependent": "1", "spare_category": "OpenGL"})
        hou_parm_template2.addParmTemplate(hou_parm_template3)

        hou_parm_template3 = hou.FolderParmTemplate("ogl_numtex", "Diffuse Texture Layers", folder_type=hou.folderType.MultiparmBlock, default_value=0, ends_tab_group=False)
        hou_parm_template3.setTags({"spare_category": "OpenGL"})

        hou_parm_template4 = hou.ToggleParmTemplate("ogl_use_tex#", "Use Diffuse Map #", default_value=True)
        hou_parm_template4.setHelp("None")
        hou_parm_template4.setTags({"cook_dependent": "1", "locked": "1", "spare_category": "OpenGL"})
        hou_parm_template3.addParmTemplate(hou_parm_template4)

        hou_parm_template4 = hou.StringParmTemplate("ogl_tex#", "Texture #", 1, default_value=([""]), naming_scheme=hou.parmNamingScheme.Base1, string_type=hou.stringParmType.FileReference, menu_items=([]), menu_labels=([]), icon_names=([]), item_generator_script="", item_generator_script_language=hou.scriptLanguage.Python, menu_type=hou.menuType.StringReplace)
        hou_parm_template4.setHelp("None")
        hou_parm_template4.setTags({"cook_dependent": "1", "filechooser_mode": "read", "spare_category": "OpenGL"})
        hou_parm_template3.addParmTemplate(hou_parm_template4)

        hou_parm_template4 = hou.StringParmTemplate("ogl_texuvset#", "UV Set", 1, default_value=([""]), naming_scheme=hou.parmNamingScheme.Base1, string_type=hou.stringParmType.Regular, menu_items=(["uv","uv2","uv3","uv4","uv5","uv6","uv7","uv8"]), menu_labels=(["uv","uv2","uv3","uv4","uv5","uv6","uv7","uv8"]), icon_names=([]), item_generator_script="", item_generator_script_language=hou.scriptLanguage.Python, menu_type=hou.menuType.StringReplace)
        hou_parm_template4.setHelp("None")
        hou_parm_template4.setTags({"cook_dependent": "1", "spare_category": "OpenGL"})
        hou_parm_template3.addParmTemplate(hou_parm_template4)

        hou_parm_template4 = hou.StringParmTemplate("ogl_tex_min_filter#", "Minification Filter", 1, default_value=(["GL_LINEAR_MIPMAP_LINEAR"]), naming_scheme=hou.parmNamingScheme.Base1, string_type=hou.stringParmType.Regular, menu_items=(["GL_NEAREST","GL_LINEAR","GL_NEAREST_MIPMAP_NEAREST","GL_LINEAR_MIPMAP_NEAREST","GL_NEAREST_MIPMAP_LINEAR","GL_LINEAR_MIPMAP_LINEAR"]), menu_labels=(["No filtering (very poor)","Bilinear (poor)","No filtering, Nearest Mipmap (poor)","Bilinear, Nearest Mipmap (okay)","No filtering, Blend Mipmaps (good)","Trilinear (best)"]), icon_names=([]), item_generator_script="", item_generator_script_language=hou.scriptLanguage.Python, menu_type=hou.menuType.Normal)
        hou_parm_template4.setHelp("None")
        hou_parm_template4.setTags({"cook_dependent": "1", "spare_category": "OpenGL"})
        hou_parm_template3.addParmTemplate(hou_parm_template4)

        hou_parm_template4 = hou.StringParmTemplate("ogl_tex_mag_filter#", "Magnification Filter", 1, default_value=(["GL_LINEAR"]), naming_scheme=hou.parmNamingScheme.Base1, string_type=hou.stringParmType.Regular, menu_items=(["GL_NEAREST","GL_LINEAR"]), menu_labels=(["No filtering","Bilinear"]), icon_names=([]), item_generator_script="", item_generator_script_language=hou.scriptLanguage.Python, menu_type=hou.menuType.Normal)
        hou_parm_template4.setHelp("None")
        hou_parm_template4.setTags({"cook_dependent": "1", "spare_category": "OpenGL"})
        hou_parm_template3.addParmTemplate(hou_parm_template4)

        hou_parm_template4 = hou.StringParmTemplate("ogl_tex_wrap#", "Texture Wrap", 1, default_value=(["repeat"]), naming_scheme=hou.parmNamingScheme.Base1, string_type=hou.stringParmType.Regular, menu_items=(["repeat","clamp","decal","mirror"]), menu_labels=(["Repeat","Streak","Decal","Mirror"]), icon_names=([]), item_generator_script="", item_generator_script_language=hou.scriptLanguage.Python, menu_type=hou.menuType.Normal)
        hou_parm_template4.setHelp("None")
        hou_parm_template4.setTags({"cook_dependent": "1", "spare_category": "OpenGL"})
        hou_parm_template3.addParmTemplate(hou_parm_template4)

        hou_parm_template4 = hou.StringParmTemplate("ogl_tex_vwrap#", "Texture V Wrap", 1, default_value=(["repeat"]), naming_scheme=hou.parmNamingScheme.Base1, string_type=hou.stringParmType.Regular, menu_items=(["repeat","clamp","decal","mirror"]), menu_labels=(["Repeat","Streak","Decal","Mirror"]), icon_names=([]), item_generator_script="", item_generator_script_language=hou.scriptLanguage.Python, menu_type=hou.menuType.Normal)
        hou_parm_template4.setHelp("None")
        hou_parm_template4.setTags({"cook_dependent": "1", "spare_category": "OpenGL"})
        hou_parm_template3.addParmTemplate(hou_parm_template4)
        hou_parm_template2.addParmTemplate(hou_parm_template3)
        hou_parm_template.addParmTemplate(hou_parm_template2)

        hou_parm_template2 = hou.FolderParmTemplate("fMetalness", "Metalness", folder_type=hou.folderType.Collapsible, default_value=0, ends_tab_group=False)
        hou_parm_template2.setTags({"group_type": "collapsible"})

        hou_parm_template3 = hou.FloatParmTemplate("ogl_metallic", "Metallic", 1, default_value=([0]), min=0, max=10, min_is_strict=False, max_is_strict=False, look=hou.parmLook.Regular, naming_scheme=hou.parmNamingScheme.Base1)
        hou_parm_template3.setHelp("Metallic factor, from 0-1. The more metallic a surface is (approaching 1), \n    the less diffuse and more reflection the material will have. A metallic\n    factor closer to zero behaves more like a dielectric material. ")
        hou_parm_template3.setTags({"cook_dependent": "1", "spare_category": "OpenGL"})
        hou_parm_template2.addParmTemplate(hou_parm_template3)

        hou_parm_template3 = hou.ToggleParmTemplate("ogl_use_metallicmap", "Use Metallic Map", default_value=True)
        hou_parm_template3.setHelp("When enabled, use the map specified in ogl_metallicmap for the\n    metallic map. If this property is not present, it is assumed to be\n    enabled.")
        hou_parm_template3.setTags({"cook_dependent": "1", "ogl_use_metallicmap": "1", "spare_category": "OpenGL"})
        hou_parm_template2.addParmTemplate(hou_parm_template3)

        hou_parm_template3 = hou.StringParmTemplate("ogl_metallicmap", "Metallic Map", 1, default_value=([""]), naming_scheme=hou.parmNamingScheme.Base1, string_type=hou.stringParmType.FileReference, menu_items=([]), menu_labels=([]), icon_names=([]), item_generator_script="", item_generator_script_language=hou.scriptLanguage.Python, menu_type=hou.menuType.StringReplace)
        hou_parm_template3.setHelp("Texture map for Metallic. The GL Metallic parameter is multiplied by the\n    texture map value.")
        hou_parm_template3.setTags({"cook_dependent": "1", "filechooser_mode": "read", "spare_category": "OpenGL"})
        hou_parm_template2.addParmTemplate(hou_parm_template3)

        hou_parm_template3 = hou.IntParmTemplate("ogl_metallicmap_comp", "Metallic Channel", 1, default_value=([0]), min=0, max=4, min_is_strict=False, max_is_strict=False, naming_scheme=hou.parmNamingScheme.Base1, menu_items=(["0","1","2","3","4"]), menu_labels=(["Luminance","Red","Green","Blue","Alpha"]), icon_names=([]), item_generator_script="", item_generator_script_language=hou.scriptLanguage.Python, menu_type=hou.menuType.Normal, menu_use_token=False)
        hou_parm_template3.setConditional(hou.parmCondType.DisableWhen, "{ ogl_metallicmap == ///////\"///////\" }")
        hou_parm_template3.setHelp("Channel of the metallic texture map to sample (luminance, red, green, blue,\n    alpha).")
        hou_parm_template3.setTags({"cook_dependent": "1", "spare_category": "OpenGL"})
        hou_parm_template2.addParmTemplate(hou_parm_template3)

        hou_parm_template3 = hou.FloatParmTemplate("ogl_metallic_edge", "Metallic Edge", 3, default_value=([0, 0, 0]), min=0, max=1, min_is_strict=False, max_is_strict=False, look=hou.parmLook.ColorSquare, naming_scheme=hou.parmNamingScheme.RGBA)
        hou_parm_template3.setHelp("Metallic edge tint for metallic materials. At grazing angles, metallic\n    objects reflect with the tint rather than their specular tint.")
        hou_parm_template3.setTags({"cook_dependent": "1", "spare_category": "OpenGL"})
        hou_parm_template2.addParmTemplate(hou_parm_template3)

        hou_parm_template3 = hou.FloatParmTemplate("ogl_ior", "Index of Refraction", 1, default_value=([1.33]), min=0, max=10, min_is_strict=False, max_is_strict=False, look=hou.parmLook.Regular, naming_scheme=hou.parmNamingScheme.Base1)
        hou_parm_template3.setHelp("Index of refraction of the material, used for fresnel calculations and\n    reflection.")
        hou_parm_template3.setTags({"cook_dependent": "1", "spare_category": "OpenGL"})
        hou_parm_template2.addParmTemplate(hou_parm_template3)
        hou_parm_template.addParmTemplate(hou_parm_template2)

        hou_parm_template2 = hou.FolderParmTemplate("fRoughness", "Roughness", folder_type=hou.folderType.Collapsible, default_value=0, ends_tab_group=False)
        hou_parm_template2.setTags({"group_type": "collapsible"})

        hou_parm_template3 = hou.ToggleParmTemplate("ogl_use_roughmap", "Use Roughness Map", default_value=True)
        hou_parm_template3.setHelp("When enabled, use the map specified in ogl_roughmap for the\n    roughness map. If this property is not present, it is assumed to be\n    enabled.")
        hou_parm_template3.setTags({"cook_dependent": "1", "spare_category": "OpenGL"})
        hou_parm_template2.addParmTemplate(hou_parm_template3)

        hou_parm_template3 = hou.StringParmTemplate("ogl_roughmap", "Roughness Map", 1, default_value=([""]), naming_scheme=hou.parmNamingScheme.Base1, string_type=hou.stringParmType.FileReference, menu_items=([]), menu_labels=([]), icon_names=([]), item_generator_script="", item_generator_script_language=hou.scriptLanguage.Python, menu_type=hou.menuType.StringReplace)
        hou_parm_template3.setHelp("Texture map for Roughness. Rougher surfaces have larger but dimmer specular highlights. This overrides the constant ogl_rough.")
        hou_parm_template3.setTags({"cook_dependent": "1", "filechooser_mode": "read", "spare_category": "OpenGL"})
        hou_parm_template2.addParmTemplate(hou_parm_template3)

        hou_parm_template3 = hou.ToggleParmTemplate("ogl_invertroughmap", "Invert Roughness Map (Glossiness)", default_value=False)
        hou_parm_template3.setConditional(hou.parmCondType.DisableWhen, "{ ogl_roughmap == ///////\"///////\" }")
        hou_parm_template3.setHelp("Invert the roughness map so that it is interpreted as a gloss map - \n    zero is no gloss (dull), one is very glossy (shiny).")
        hou_parm_template3.setTags({"cook_dependent": "1", "spare_category": "OpenGL"})
        hou_parm_template2.addParmTemplate(hou_parm_template3)

        hou_parm_template3 = hou.IntParmTemplate("ogl_roughmap_comp", "Roughness Channel", 1, default_value=([0]), min=0, max=4, min_is_strict=False, max_is_strict=False, naming_scheme=hou.parmNamingScheme.Base1, menu_items=(["0","1","2","3","4"]), menu_labels=(["Luminance","Red","Green","Blue","Alpha"]), icon_names=([]), item_generator_script="", item_generator_script_language=hou.scriptLanguage.Python, menu_type=hou.menuType.Normal, menu_use_token=False)
        hou_parm_template3.setConditional(hou.parmCondType.DisableWhen, "{ ogl_roughmap == ///////\"///////\" }")
        hou_parm_template3.setHelp("Texture component used for Roughness within the Roughness texture map, \n    which can be the luminance of RGB, red, green, blue or alpha. This allows\n    roughness to be sourced from packed texture maps which contain parameters \n    in the other texture channels.")
        hou_parm_template3.setTags({"cook_dependent": "1", "spare_category": "OpenGL"})
        hou_parm_template2.addParmTemplate(hou_parm_template3)

        hou_parm_template3 = hou.FloatParmTemplate("ogl_rough", "OGL Roughness", 1, default_value=([0.05]), min=0, max=10, min_is_strict=False, max_is_strict=False, look=hou.parmLook.Regular, naming_scheme=hou.parmNamingScheme.Base1)
        hou_parm_template2.addParmTemplate(hou_parm_template3)
        hou_parm_template.addParmTemplate(hou_parm_template2)

        hou_parm_template2 = hou.FolderParmTemplate("fSpecular", "Specular", folder_type=hou.folderType.Collapsible, default_value=0, ends_tab_group=False)
        hou_parm_template2.setTags({"group_type": "collapsible"})

        hou_parm_template3 = hou.ToggleParmTemplate("ogl_use_spec", "Enable Specular", default_value=True)
        hou_parm_template3.setHelp("Toggles contribution of the specular color. When off, no specular highlights will appear.")
        hou_parm_template3.setTags({"cook_dependent": "1", "spare_category": "OpenGL"})
        hou_parm_template2.addParmTemplate(hou_parm_template3)

        hou_parm_template3 = hou.FloatParmTemplate("ogl_spec", "OGL Specular", 3, default_value=([0.2, 0.2, 0.2]), min=0, max=10, min_is_strict=False, max_is_strict=False, look=hou.parmLook.ColorSquare, naming_scheme=hou.parmNamingScheme.RGBA)
        hou_parm_template2.addParmTemplate(hou_parm_template3)

        hou_parm_template3 = hou.FloatParmTemplate("ogl_spec_intensity", "Specular Intensity", 1, default_value=([1]), min=0, max=2, min_is_strict=False, max_is_strict=False, look=hou.parmLook.Regular, naming_scheme=hou.parmNamingScheme.Base1)
        hou_parm_template3.setHelp("The specular intensity multiplies the Specular color, allowing it to be easily adjusted without affecting the its hue or saturation.")
        hou_parm_template3.setTags({"cook_dependent": "1", "spare_category": "OpenGL"})
        hou_parm_template2.addParmTemplate(hou_parm_template3)

        hou_parm_template3 = hou.ToggleParmTemplate("ogl_use_specmap", "Use Specular Map", default_value=True)
        hou_parm_template3.setHelp("When enabled, use the map specified in ogl_specmap for the\n    specular map. If this property is not present, it is assumed to be\n    enabled.")
        hou_parm_template3.setTags({"cook_dependent": "1", "spare_category": "OpenGL"})
        hou_parm_template2.addParmTemplate(hou_parm_template3)

        hou_parm_template3 = hou.StringParmTemplate("ogl_specmap", "Specular Map", 1, default_value=([""]), naming_scheme=hou.parmNamingScheme.Base1, string_type=hou.stringParmType.FileReference, menu_items=([]), menu_labels=([]), icon_names=([]), item_generator_script="", item_generator_script_language=hou.scriptLanguage.Python, menu_type=hou.menuType.StringReplace)
        hou_parm_template3.setHelp("The image file to use for modifying specular reflections. The RGB values of\n    the file are multiplied by the specular colors of lights when shading.")
        hou_parm_template3.setTags({"cook_dependent": "1", "filechooser_mode": "read", "spare_category": "OpenGL"})
        hou_parm_template2.addParmTemplate(hou_parm_template3)

        hou_parm_template3 = hou.StringParmTemplate("ogl_spec_model", "Specular Model", 1, default_value=(["phong"]), naming_scheme=hou.parmNamingScheme.Base1, string_type=hou.stringParmType.Regular, menu_items=(["phong","blinn","ggx"]), menu_labels=(["Phong","Blinn","GGX"]), icon_names=([]), item_generator_script="", item_generator_script_language=hou.scriptLanguage.Python, menu_type=hou.menuType.Normal)
        hou_parm_template3.setHelp("Specifies the model to use for specular highlights on the material: phong,\n    blinn or ggx. Phong and Blinn are quick approximations, GGX is a more\n    realistic and computationally expensive specular model. This can also be\n    set to lambert to remove specular highlights altogether.")
        hou_parm_template3.setTags({"cook_dependent": "1", "spare_category": "OpenGL"})
        hou_parm_template2.addParmTemplate(hou_parm_template3)

        hou_parm_template3 = hou.FloatParmTemplate("ogl_spectint", "Specular Tint", 1, default_value=([1]), min=0, max=1, min_is_strict=False, max_is_strict=False, look=hou.parmLook.Regular, naming_scheme=hou.parmNamingScheme.Base1)
        hou_parm_template3.setHelp("Amount to tint the specular reflection with the Specular material color.\n    This controls how the material reacts to specular highlights,\n    by multiplying specular highlights on the material. Decreasing this value\n    will desaturate the specular highlight to (1,1,1).")
        hou_parm_template3.setTags({"cook_dependent": "1", "spare_category": "OpenGL"})
        hou_parm_template2.addParmTemplate(hou_parm_template3)

        hou_parm_template3 = hou.IntParmTemplate("ogl_speclayer", "Specular Layer", 1, default_value=([0]), min=0, max=15, min_is_strict=False, max_is_strict=False, naming_scheme=hou.parmNamingScheme.Base1, menu_items=([]), menu_labels=([]), icon_names=([]), item_generator_script="", item_generator_script_language=hou.scriptLanguage.Python, menu_type=hou.menuType.Normal, menu_use_token=False)
        hou_parm_template3.setConditional(hou.parmCondType.DisableWhen, "{ ogl_specmap == ///////\"///////\" }")
        hou_parm_template3.setHelp("The texture layer that the UV coordinates for the specular map are sourced \n    from.")
        hou_parm_template3.setTags({"cook_dependent": "1", "spare_category": "OpenGL"})
        hou_parm_template2.addParmTemplate(hou_parm_template3)
        hou_parm_template.addParmTemplate(hou_parm_template2)

        hou_parm_template2 = hou.FolderParmTemplate("FNandB", "Normal and Bump", folder_type=hou.folderType.Collapsible, default_value=0, ends_tab_group=False)
        hou_parm_template2.setTags({"group_type": "collapsible"})

        hou_parm_template3 = hou.StringParmTemplate("ogl_normalmap_style", "Normal Map Style", 1, default_value=(["normal"]), naming_scheme=hou.parmNamingScheme.Base1, string_type=hou.stringParmType.Regular, menu_items=(["bump","normal"]), menu_labels=(["Bump Map","Normal Map"]), icon_names=([]), item_generator_script="", item_generator_script_language=hou.scriptLanguage.Python, menu_type=hou.menuType.Normal)
        hou_parm_template3.setHelp("Selects between using a Bump Map or a Normal Map for perturbing\n    geometric normals. The default is to use a normal map.")
        hou_parm_template3.setTags({"cook_dependent": "1", "spare_category": "OpenGL"})
        hou_parm_template2.addParmTemplate(hou_parm_template3)

        hou_parm_template3 = hou.ToggleParmTemplate("ogl_use_normalmap", "Use Normal Map", default_value=True)
        hou_parm_template3.setHelp("When enabled, use the map specified in ogl_normalmap for the\n    normal map. If this property is not present, it is assumed to be\n    enabled.")
        hou_parm_template3.setTags({"cook_dependent": "1", "spare_category": "OpenGL"})
        hou_parm_template2.addParmTemplate(hou_parm_template3)

        hou_parm_template3 = hou.StringParmTemplate("ogl_normalmap", "Normal Map", 1, default_value=([""]), naming_scheme=hou.parmNamingScheme.Base1, string_type=hou.stringParmType.FileReference, menu_items=([]), menu_labels=([]), icon_names=([]), item_generator_script="", item_generator_script_language=hou.scriptLanguage.Python, menu_type=hou.menuType.StringReplace)
        hou_parm_template3.setHelp("Use a normal map to specify normals instead of interpolating normals \n    across a polygon. The RGB values are used for the normal's XYZ vector.")
        hou_parm_template3.setTags({"cook_dependent": "1", "filechooser_mode": "read", "spare_category": "OpenGL"})
        hou_parm_template2.addParmTemplate(hou_parm_template3)

        hou_parm_template3 = hou.StringParmTemplate("ogl_normalmap_type", "Normal Map Type", 1, default_value=(["uvtangent"]), naming_scheme=hou.parmNamingScheme.Base1, string_type=hou.stringParmType.Regular, menu_items=(["uvtangent","world","object"]), menu_labels=(["Tangent Space","World Space","Object Space"]), icon_names=([]), item_generator_script="", item_generator_script_language=hou.scriptLanguage.Python, menu_type=hou.menuType.Normal)
        hou_parm_template3.setHelp("Specifies the space that the normal map operates in: UV Tangent,\n    World, or Object space.")
        hou_parm_template3.setTags({"cook_dependent": "1", "spare_category": "OpenGL"})
        hou_parm_template2.addParmTemplate(hou_parm_template3)

        hou_parm_template3 = hou.IntParmTemplate("ogl_normalbias", "Normal Map Range", 1, default_value=([0]), min=0, max=10, min_is_strict=False, max_is_strict=False, naming_scheme=hou.parmNamingScheme.Base1, menu_items=(["0","1"]), menu_labels=(["0 to 1","-1 to 1"]), icon_names=([]), item_generator_script="", item_generator_script_language=hou.scriptLanguage.Python, menu_type=hou.menuType.Normal, menu_use_token=False)
        hou_parm_template3.setConditional(hou.parmCondType.DisableWhen, "{ ogl_normalmap == ///////\"///////\" }")
        hou_parm_template3.setHelp("The range of the normal map is either 0-1 (8b map) or -1 to 1 (floating\n    point map). This bias must match the type of normal map used.")
        hou_parm_template3.setTags({"cook_dependent": "1", "spare_category": "OpenGL"})
        hou_parm_template2.addParmTemplate(hou_parm_template3)

        hou_parm_template3 = hou.FloatParmTemplate("ogl_normalmap_scale", "Normal Scale", 1, default_value=([1]), min=0, max=10, min_is_strict=False, max_is_strict=False, look=hou.parmLook.Regular, naming_scheme=hou.parmNamingScheme.Base1)
        hou_parm_template3.setConditional(hou.parmCondType.DisableWhen, "{ ogl_normalmap == ///////\"///////\" }")
        hou_parm_template3.setHelp("Scales the X and Y components of a tangent normal map to increase or decrease the effect the normal map has on the normals.")
        hou_parm_template3.setTags({"cook_dependent": "1", "spare_category": "OpenGL"})
        hou_parm_template2.addParmTemplate(hou_parm_template3)

        hou_parm_template3 = hou.ToggleParmTemplate("ogl_normalflipx", "Flip Normal Map X", default_value=False)
        hou_parm_template3.setConditional(hou.parmCondType.DisableWhen, "{ ogl_normalmap == ///////\"///////\" }")
        hou_parm_template3.setHelp("Flip the normal's X direction when applying the normal map. This may be \n    needed for normal maps generated by other applications. ")
        hou_parm_template3.setTags({"cook_dependent": "1", "spare_category": "OpenGL"})
        hou_parm_template2.addParmTemplate(hou_parm_template3)

        hou_parm_template3 = hou.ToggleParmTemplate("ogl_normalflipy", "Flip Normal Map Y", default_value=False)
        hou_parm_template3.setConditional(hou.parmCondType.DisableWhen, "{ ogl_normalmap == ///////\"///////\" }")
        hou_parm_template3.setHelp("Flip the normal's Y direction when applying the normal map. This may be \n    needed for normal maps generated by other applications. ")
        hou_parm_template3.setTags({"cook_dependent": "1", "spare_category": "OpenGL"})
        hou_parm_template2.addParmTemplate(hou_parm_template3)

        hou_parm_template3 = hou.IntParmTemplate("ogl_normallayer", "Normal Layer", 1, default_value=([0]), min=0, max=15, min_is_strict=False, max_is_strict=False, naming_scheme=hou.parmNamingScheme.Base1, menu_items=([]), menu_labels=([]), icon_names=([]), item_generator_script="", item_generator_script_language=hou.scriptLanguage.Python, menu_type=hou.menuType.Normal, menu_use_token=False)
        hou_parm_template3.setConditional(hou.parmCondType.DisableWhen, "{ ogl_normalmap == ///////\"///////\" }")
        hou_parm_template3.setHelp("The texture layer that the UV coordinates for the normal map are sourced \n    from.")
        hou_parm_template3.setTags({"cook_dependent": "1", "spare_category": "OpenGL"})
        hou_parm_template2.addParmTemplate(hou_parm_template3)

        hou_parm_template3 = hou.SeparatorParmTemplate("sepparm")
        hou_parm_template2.addParmTemplate(hou_parm_template3)

        hou_parm_template3 = hou.ToggleParmTemplate("ogl_use_bumpmap", "Use Bump Map", default_value=True)
        hou_parm_template3.setHelp("When enabled, use the map specified in ogl_bumpmap for the\n    bump map. If this property is not present, it is assumed to be\n    enabled.")
        hou_parm_template3.setTags({"cook_dependent": "1", "spare_category": "OpenGL"})
        hou_parm_template2.addParmTemplate(hou_parm_template3)

        hou_parm_template3 = hou.StringParmTemplate("ogl_bumpmap", "Bump Map", 1, default_value=([""]), naming_scheme=hou.parmNamingScheme.Base1, string_type=hou.stringParmType.FileReference, menu_items=([]), menu_labels=([]), icon_names=([]), item_generator_script="", item_generator_script_language=hou.scriptLanguage.Python, menu_type=hou.menuType.StringReplace)
        hou_parm_template3.setHelp("Use a bump map to perturb normals to give the illusion of depth to a flat\n    polygon. ")
        hou_parm_template3.setTags({"cook_dependent": "1", "filechooser_mode": "read", "spare_category": "OpenGL"})
        hou_parm_template2.addParmTemplate(hou_parm_template3)

        hou_parm_template3 = hou.FloatParmTemplate("ogl_bumpscale", "Bump Scale", 1, default_value=([1]), min=0, max=10, min_is_strict=False, max_is_strict=False, look=hou.parmLook.Regular, naming_scheme=hou.parmNamingScheme.Base1)
        hou_parm_template3.setConditional(hou.parmCondType.DisableWhen, "{ ogl_bumpmap == ///////\"///////\" }")
        hou_parm_template3.setHelp("Scales the bumps to increase or decrease the apparent size of the bumps.")
        hou_parm_template3.setTags({"cook_dependent": "1", "spare_category": "OpenGL"})
        hou_parm_template2.addParmTemplate(hou_parm_template3)

        hou_parm_template3 = hou.IntParmTemplate("ogl_bumplayer", "Bump Layer", 1, default_value=([0]), min=0, max=15, min_is_strict=False, max_is_strict=False, naming_scheme=hou.parmNamingScheme.Base1, menu_items=([]), menu_labels=([]), icon_names=([]), item_generator_script="", item_generator_script_language=hou.scriptLanguage.Python, menu_type=hou.menuType.Normal, menu_use_token=False)
        hou_parm_template3.setConditional(hou.parmCondType.DisableWhen, "{ ogl_bumpmap == ///////\"///////\" }")
        hou_parm_template3.setHelp("The texture layer that the UV coordinates for the bump map are sourced \n    from.")
        hou_parm_template3.setTags({"cook_dependent": "1", "spare_category": "OpenGL"})
        hou_parm_template2.addParmTemplate(hou_parm_template3)

        hou_parm_template3 = hou.ToggleParmTemplate("ogl_bumpinvert", "Invert Bumps", default_value=False)
        hou_parm_template3.setConditional(hou.parmCondType.DisableWhen, "{ ogl_bumpmap == ///////\"///////\" }")
        hou_parm_template3.setHelp("Inverts the bumps so that they appear to be going into the object instead of out. ")
        hou_parm_template3.setTags({"cook_dependent": "1", "spare_category": "OpenGL"})
        hou_parm_template2.addParmTemplate(hou_parm_template3)
        hou_parm_template.addParmTemplate(hou_parm_template2)

        hou_parm_template2 = hou.FolderParmTemplate("fDisplacement", "Displacement", folder_type=hou.folderType.Collapsible, default_value=0, ends_tab_group=False)
        hou_parm_template2.setTags({"group_type": "collapsible"})

        hou_parm_template3 = hou.ToggleParmTemplate("ogl_use_displacemap", "Use Displacement Map", default_value=True)
        hou_parm_template3.setHelp("When enabled, use the map specified in ogl_displacemap for displacement\n    mapping.")
        hou_parm_template3.setTags({"cook_dependent": "1", "spare_category": "OpenGL"})
        hou_parm_template2.addParmTemplate(hou_parm_template3)

        hou_parm_template3 = hou.StringParmTemplate("ogl_displacemap", "Displacement Map", 1, default_value=([""]), naming_scheme=hou.parmNamingScheme.Base1, string_type=hou.stringParmType.FileReference, menu_items=([]), menu_labels=([]), icon_names=([]), item_generator_script="", item_generator_script_language=hou.scriptLanguage.Python, menu_type=hou.menuType.StringReplace)
        hou_parm_template3.setHelp("The image file that defines a height-based displacement. The surface \n    will be tessellated and displaced along the normal by the height when\n    this map is valid.")
        hou_parm_template3.setTags({"cook_dependent": "1", "filechooser_mode": "read", "spare_category": "OpenGL"})
        hou_parm_template2.addParmTemplate(hou_parm_template3)

        hou_parm_template3 = hou.FloatParmTemplate("ogl_displacescale", "Displace Scale", 1, default_value=([1]), min=0, max=2, min_is_strict=False, max_is_strict=False, look=hou.parmLook.Regular, naming_scheme=hou.parmNamingScheme.Base1)
        hou_parm_template3.setConditional(hou.parmCondType.DisableWhen, "{ ogl_displacemap == ///////\"///////\" }")
        hou_parm_template3.setHelp("Factor applied to the height sampled from the displacement map, after\n    ogl_displaceoffset has been added. This affects the scale of the \n    displacement.")
        hou_parm_template3.setTags({"cook_dependent": "1", "spare_category": "OpenGL"})
        hou_parm_template2.addParmTemplate(hou_parm_template3)

        hou_parm_template3 = hou.FloatParmTemplate("ogl_displaceoffset", "Displace Offset", 1, default_value=([0]), min=-1, max=1, min_is_strict=False, max_is_strict=False, look=hou.parmLook.Regular, naming_scheme=hou.parmNamingScheme.Base1)
        hou_parm_template3.setConditional(hou.parmCondType.DisableWhen, "{ ogl_displacemap == ///////\"///////\" }")
        hou_parm_template3.setHelp("Value added to the height sampled from the displacement map. Usual values\n    are 0 and -0.5, depending on whether the height in the map is centered\n    around 0 or 0.5.")
        hou_parm_template3.setTags({"cook_dependent": "1", "spare_category": "OpenGL"})
        hou_parm_template2.addParmTemplate(hou_parm_template3)

        hou_parm_template3 = hou.StringParmTemplate("ogl_displace_method", "Displace Method", 1, default_value=(["disp"]), naming_scheme=hou.parmNamingScheme.Base1, string_type=hou.stringParmType.Regular, menu_items=(["disp","vectordisp"]), menu_labels=(["Along Normal","Vector"]), icon_names=([]), item_generator_script="", item_generator_script_language=hou.scriptLanguage.Python, menu_type=hou.menuType.Normal)
        hou_parm_template3.setConditional(hou.parmCondType.DisableWhen, "{ ogl_displacemap == ///////\"///////\" }")
        hou_parm_template3.setHelp("Displacement can be done along the surface normal (\"Along Normal\") or using\n    full vector displacement (\"Vector\").")
        hou_parm_template3.setTags({"cook_dependent": "1", "spare_category": "OpenGL"})
        hou_parm_template2.addParmTemplate(hou_parm_template3)

        hou_parm_template3 = hou.StringParmTemplate("ogl_displace_space", "Displace Vector Space", 1, default_value=(["uvtangent"]), naming_scheme=hou.parmNamingScheme.Base1, string_type=hou.stringParmType.Regular, menu_items=(["uvtangent","object","world"]), menu_labels=(["UV Tangent","Object Space","World Space"]), icon_names=([]), item_generator_script="", item_generator_script_language=hou.scriptLanguage.Python, menu_type=hou.menuType.Normal)
        hou_parm_template3.setConditional(hou.parmCondType.DisableWhen, "{ ogl_displacemap == ///////\"///////\" } { ogl_displace_method == disp }")
        hou_parm_template3.setHelp("For full vector displacement, the vector can be relative to the UV tangent\n    space, object space, or world space.")
        hou_parm_template3.setTags({"cook_dependent": "1", "spare_category": "OpenGL"})
        hou_parm_template2.addParmTemplate(hou_parm_template3)

        hou_parm_template3 = hou.StringParmTemplate("ogl_displace_up", "Displace Up Vector", 1, default_value=(["xyz"]), naming_scheme=hou.parmNamingScheme.Base1, string_type=hou.stringParmType.Regular, menu_items=(["xyz","xzy"]), menu_labels=(["XYZ (Y Up)","XZY (Z Up)"]), icon_names=([]), item_generator_script="", item_generator_script_language=hou.scriptLanguage.Python, menu_type=hou.menuType.Normal)
        hou_parm_template3.setConditional(hou.parmCondType.DisableWhen, "{ ogl_displacemap == ///////\"///////\" } { ogl_displace_method == disp }")
        hou_parm_template3.setHelp("Allows the vector to be interpreted as XYZ or XZY. Some applications export\n    vector displacement in XZY order. Houdini uses XYZ by default.")
        hou_parm_template3.setTags({"cook_dependent": "1", "spare_category": "OpenGL"})
        hou_parm_template2.addParmTemplate(hou_parm_template3)
        hou_parm_template.addParmTemplate(hou_parm_template2)

        hou_parm_template2 = hou.FolderParmTemplate("o_Opacity", "Opacity", folder_type=hou.folderType.Collapsible, default_value=0, ends_tab_group=False)
        hou_parm_template2.setTags({"group_type": "collapsible"})

        hou_parm_template3 = hou.FloatParmTemplate("ogl_alpha", "OGL Alpha", 1, default_value=([1]), min=0, max=10, min_is_strict=False, max_is_strict=False, look=hou.parmLook.Regular, naming_scheme=hou.parmNamingScheme.Base1)
        hou_parm_template2.addParmTemplate(hou_parm_template3)

        hou_parm_template3 = hou.ToggleParmTemplate("ogl_use_opacitymap", "Use Opacity Map", default_value=True)
        hou_parm_template3.setHelp("When enabled, use the map specified in ogl_opacitymap for the\n    opacity map. If this property is not present, it is assumed to be\n    enabled.")
        hou_parm_template3.setTags({"cook_dependent": "1", "spare_category": "OpenGL"})
        hou_parm_template2.addParmTemplate(hou_parm_template3)

        hou_parm_template3 = hou.StringParmTemplate("ogl_opacitymap", "Opacity Map", 1, default_value=([""]), naming_scheme=hou.parmNamingScheme.Base1, string_type=hou.stringParmType.FileReference, menu_items=([]), menu_labels=([]), icon_names=([]), item_generator_script="", item_generator_script_language=hou.scriptLanguage.Python, menu_type=hou.menuType.StringReplace)
        hou_parm_template3.setHelp("The image file to use for the opacity of the material. Only the alpha \n    channel is used in an RGBA image file. The map values are multiplied by\n    both ogl_alpha or ogl_transparency, and point/vertex alpha,\n    if present.")
        hou_parm_template3.setTags({"cook_dependent": "1", "filechooser_mode": "read", "spare_category": "OpenGL"})
        hou_parm_template2.addParmTemplate(hou_parm_template3)

        hou_parm_template3 = hou.ToggleParmTemplate("ogl_opacitymap_invert", "Invert Opacity Map", default_value=False)
        hou_parm_template3.setHelp("Invert the values of the opacity map so that zero is opaque and one is\n    completely transparent. When off, zero is completely transparent and one\n    is opaque.")
        hou_parm_template3.setTags({"cook_dependent": "1", "spare_category": "OpenGL"})
        hou_parm_template2.addParmTemplate(hou_parm_template3)

        hou_parm_template3 = hou.ToggleParmTemplate("ogl_use_alpha_transparency", "Enable Alpha and Transparency", default_value=True)
        hou_parm_template3.setHelp("When disabled, Alpha, Alpha Parallel, and Transparency will\n    have no effect. When enabled, Transparency is respected, and if not\n    present, then Alpha and Alpha Parallel. This has no effect on\n    Shader Alpha.")
        hou_parm_template3.setTags({"cook_dependent": "1", "spare_category": "OpenGL"})
        hou_parm_template2.addParmTemplate(hou_parm_template3)

        hou_parm_template3 = hou.FloatParmTemplate("ogl_alpha_para", "Alpha Parallel", 1, default_value=([1]), min=0, max=1, min_is_strict=False, max_is_strict=False, look=hou.parmLook.Regular, naming_scheme=hou.parmNamingScheme.Base1)
        hou_parm_template3.setHelp("Opacity of the surface when the surface is parallel to the viewing direction\n    Opaque surfaces have an opacity of 1. Decreasing the value will make the \n    material more translucent, and a value of 0 will cause it to disappear \n    entirely.")
        hou_parm_template3.setTags({"cook_dependent": "1", "spare_category": "OpenGL"})
        hou_parm_template2.addParmTemplate(hou_parm_template3)

        hou_parm_template3 = hou.FloatParmTemplate("ogl_transparency", "Transparency", 1, default_value=([0]), min=0, max=1, min_is_strict=False, max_is_strict=False, look=hou.parmLook.Regular, naming_scheme=hou.parmNamingScheme.Base1)
        hou_parm_template3.setHelp("Defines the transparency of the surface, which overrides the Alpha and \n    Alpha Parallel properties if it is present. A value of zero means the\n    surface has no transparency and is thus completely opaque. A value of one\n    means that it is completely transparent and only reflections based on the\n    Index of Refraction will be seen.")
        hou_parm_template3.setTags({"cook_dependent": "1", "spare_category": "OpenGL"})
        hou_parm_template2.addParmTemplate(hou_parm_template3)

        hou_parm_template3 = hou.IntParmTemplate("ogl_opacitylayer", "Opacity Layer", 1, default_value=([0]), min=0, max=15, min_is_strict=False, max_is_strict=False, naming_scheme=hou.parmNamingScheme.Base1, menu_items=([]), menu_labels=([]), icon_names=([]), item_generator_script="", item_generator_script_language=hou.scriptLanguage.Python, menu_type=hou.menuType.Normal, menu_use_token=False)
        hou_parm_template3.setConditional(hou.parmCondType.DisableWhen, "{ ogl_opacitymap == ///\"///\" }")
        hou_parm_template3.setHelp("The texture layer that the UV coordinates for the opacity map are sourced \n    from.")
        hou_parm_template3.setTags({"cook_dependent": "1", "spare_category": "OpenGL"})
        hou_parm_template2.addParmTemplate(hou_parm_template3)
        hou_parm_template.addParmTemplate(hou_parm_template2)

        hou_parm_template2 = hou.FolderParmTemplate("fEmission", "Emission", folder_type=hou.folderType.Collapsible, default_value=0, ends_tab_group=False)
        hou_parm_template2.setTags({"group_type": "collapsible"})

        hou_parm_template3 = hou.FloatParmTemplate("ogl_emit_intensity", "Emission Intensity", 1, default_value=([1]), min=0, max=2, min_is_strict=False, max_is_strict=False, look=hou.parmLook.Regular, naming_scheme=hou.parmNamingScheme.Base1)
        hou_parm_template3.setHelp("The emission intensity multiplies the Emission color, allowing it to be easily adjusted without affecting the its hue or saturation.")
        hou_parm_template3.setTags({"cook_dependent": "1", "spare_category": "OpenGL"})
        hou_parm_template2.addParmTemplate(hou_parm_template3)

        hou_parm_template3 = hou.ToggleParmTemplate("ogl_use_emit", "Enable Emission", default_value=False)
        hou_parm_template3.setHelp("Toggles contribution of the emission color. When off, the material will not be emissive.")
        hou_parm_template3.setTags({"cook_dependent": "1", "spare_category": "OpenGL"})
        hou_parm_template2.addParmTemplate(hou_parm_template3)

        hou_parm_template3 = hou.ToggleParmTemplate("ogl_use_emissionmap", "Use Emission Map", default_value=True)
        hou_parm_template3.setHelp("When enabled, use the map specified in ogl_emissionmap for emission. \n    If this property is not present, it is assumed to be enabled.")
        hou_parm_template3.setTags({"cook_dependent": "1", "spare_category": "OpenGL"})
        hou_parm_template2.addParmTemplate(hou_parm_template3)

        hou_parm_template3 = hou.StringParmTemplate("ogl_emissionmap", "Emission Map", 1, default_value=([""]), naming_scheme=hou.parmNamingScheme.Base1, string_type=hou.stringParmType.FileReference, menu_items=([]), menu_labels=([]), icon_names=([]), item_generator_script="", item_generator_script_language=hou.scriptLanguage.Python, menu_type=hou.menuType.StringReplace)
        hou_parm_template3.setHelp("An image file used for emission texturing. Unlike a diffuse map, the \n    emission map is not affected by lighting and appears constant. The RGB\n    values of the emission map are multiplied by the ogl_emit color which\n    defaults to (0,0,0), so this should be set to (1,1,1) if an emission map\n    is used. The alpha of an emission map is ignored.")
        hou_parm_template3.setTags({"cook_dependent": "1", "filechooser_mode": "read", "spare_category": "OpenGL"})
        hou_parm_template2.addParmTemplate(hou_parm_template3)

        hou_parm_template3 = hou.FloatParmTemplate("ogl_emit", "OGL Emission", 3, default_value=([0, 0, 0]), min=0, max=10, min_is_strict=False, max_is_strict=False, look=hou.parmLook.ColorSquare, naming_scheme=hou.parmNamingScheme.RGBA)
        hou_parm_template2.addParmTemplate(hou_parm_template3)
        hou_parm_template.addParmTemplate(hou_parm_template2)

        hou_parm_template2 = hou.FolderParmTemplate("fOccluson", "Occlusion", folder_type=hou.folderType.Collapsible, default_value=0, ends_tab_group=False)
        hou_parm_template2.setTags({"group_type": "collapsible"})

        hou_parm_template3 = hou.ToggleParmTemplate("ogl_use_occlusionmap", "Use Occlusion Map", default_value=True)
        hou_parm_template3.setHelp("When enabled, use the map specified in ogl_occlusionmap for the\n    occlusion map. If this property is not present, it is assumed to be\n    enabled.")
        hou_parm_template3.setTags({"cook_dependent": "1", "spare_category": "OpenGL"})
        hou_parm_template2.addParmTemplate(hou_parm_template3)

        hou_parm_template3 = hou.StringParmTemplate("ogl_occlusionmap", "Occlusion Map", 1, default_value=([""]), naming_scheme=hou.parmNamingScheme.Base1, string_type=hou.stringParmType.FileReference, menu_items=([]), menu_labels=([]), icon_names=([]), item_generator_script="", item_generator_script_language=hou.scriptLanguage.Python, menu_type=hou.menuType.StringReplace)
        hou_parm_template3.setHelp("Texture map for Occlusion. The diffuse color is multiplied by the \n    occlusion.")
        hou_parm_template3.setTags({"cook_dependent": "1", "filechooser_mode": "read", "spare_category": "OpenGL"})
        hou_parm_template2.addParmTemplate(hou_parm_template3)

        hou_parm_template3 = hou.IntParmTemplate("ogl_occlusionmap_comp", "Occlusion Channel", 1, default_value=([0]), min=0, max=4, min_is_strict=False, max_is_strict=False, naming_scheme=hou.parmNamingScheme.Base1, menu_items=(["0","1","2","3","4"]), menu_labels=(["Luminance","Red","Green","Blue","Alpha"]), icon_names=([]), item_generator_script="", item_generator_script_language=hou.scriptLanguage.Python, menu_type=hou.menuType.Normal, menu_use_token=False)
        hou_parm_template3.setConditional(hou.parmCondType.DisableWhen, "{ ogl_occlusionmap == ///\"///\" }")
        hou_parm_template3.setHelp("Channel of the occlusion texture map to sample (luminance, red, green, blue,\n    alpha).")
        hou_parm_template3.setTags({"cook_dependent": "1", "spare_category": "OpenGL"})
        hou_parm_template2.addParmTemplate(hou_parm_template3)
        hou_parm_template.addParmTemplate(hou_parm_template2)

        hou_parm_template2 = hou.FolderParmTemplate("fCoat", "Coat", folder_type=hou.folderType.Collapsible, default_value=0, ends_tab_group=False)
        hou_parm_template2.setTags({"group_type": "collapsible"})

        hou_parm_template3 = hou.FloatParmTemplate("ogl_coat_intensity", "Coat Intensity", 1, default_value=([0.5]), min=0, max=1, min_is_strict=True, max_is_strict=True, look=hou.parmLook.Regular, naming_scheme=hou.parmNamingScheme.Base1)
        hou_parm_template3.setHelp("Intensity of coat specular reflections. If the intensity is\n    zero, the material does not have a coat. Coat reflections are only \n    supported in High Quality Lighting.")
        hou_parm_template3.setTags({"cook_dependent": "1", "spare_category": "OpenGL"})
        hou_parm_template2.addParmTemplate(hou_parm_template3)

        hou_parm_template3 = hou.FloatParmTemplate("ogl_coat_rough", "Coat Roughness", 1, default_value=([0.05]), min=0, max=1, min_is_strict=False, max_is_strict=False, look=hou.parmLook.Regular, naming_scheme=hou.parmNamingScheme.Base1)
        hou_parm_template3.setHelp("None")
        hou_parm_template3.setTags({"cook_dependent": "1", "spare_category": "OpenGL"})
        hou_parm_template2.addParmTemplate(hou_parm_template3)

        hou_parm_template3 = hou.StringParmTemplate("ogl_coat_model", "Coat Specular Model", 1, default_value=(["ggx"]), naming_scheme=hou.parmNamingScheme.Base1, string_type=hou.stringParmType.Regular, menu_items=(["phong","blinn","ggx"]), menu_labels=(["Phong","Blinn","GGX"]), icon_names=([]), item_generator_script="", item_generator_script_language=hou.scriptLanguage.Python, menu_type=hou.menuType.Normal)
        hou_parm_template3.setHelp("Specular model of the coat layer, which can be Phong, Blinn, or GGX.")
        hou_parm_template3.setTags({"cook_dependent": "1", "spare_category": "OpenGL"})
        hou_parm_template2.addParmTemplate(hou_parm_template3)

        hou_parm_template3 = hou.ToggleParmTemplate("ogl_use_coat_intensity_map", "Use Coat Intensity Map", default_value=True)
        hou_parm_template3.setHelp("When enabled, use the map specified in ogl_coat_intensity_map for the\n    coat intensity. If this property is not present, it is assumed to be\n    enabled.")
        hou_parm_template3.setTags({"cook_dependent": "1", "spare_category": "OpenGL"})
        hou_parm_template2.addParmTemplate(hou_parm_template3)

        hou_parm_template3 = hou.StringParmTemplate("ogl_coat_intensity_map", "Coat Intensity Map", 1, default_value=([""]), naming_scheme=hou.parmNamingScheme.Base1, string_type=hou.stringParmType.FileReference, menu_items=([]), menu_labels=([]), icon_names=([]), item_generator_script="", item_generator_script_language=hou.scriptLanguage.Python, menu_type=hou.menuType.StringReplace)
        hou_parm_template3.setHelp("Texture map to modulate coat intensity. The texture map value is \n    multiplied by the Coat Intensity to produce the final coat intensity \n    value.")
        hou_parm_template3.setTags({"cook_dependent": "1", "filechooser_mode": "read", "spare_category": "OpenGL"})
        hou_parm_template2.addParmTemplate(hou_parm_template3)

        hou_parm_template3 = hou.IntParmTemplate("ogl_coat_intensity_comp", "Coat Intensity Channel", 1, default_value=([0]), min=0, max=4, min_is_strict=False, max_is_strict=False, naming_scheme=hou.parmNamingScheme.Base1, menu_items=(["0","1","2","3","4"]), menu_labels=(["Luminance","Red","Green","Blue","Alpha"]), icon_names=([]), item_generator_script="", item_generator_script_language=hou.scriptLanguage.Python, menu_type=hou.menuType.Normal, menu_use_token=False)
        hou_parm_template3.setConditional(hou.parmCondType.DisableWhen, "{ ogl_coat_intensity_map == ///////\"///////\" }")
        hou_parm_template3.setHelp("The channel of Coat Intensity Map from which coat intensity is selected,\n    either the luminance of the color or one of the red, green, blue, or alpha\n    channels.")
        hou_parm_template3.setTags({"cook_dependent": "1", "spare_category": "OpenGL"})
        hou_parm_template2.addParmTemplate(hou_parm_template3)

        hou_parm_template3 = hou.ToggleParmTemplate("ogl_use_coat_roughness_map", "Use Coat Roughness Map", default_value=True)
        hou_parm_template3.setHelp("When enabled, use the map specified in ogl_coat_roughness_map for the\n    coat roughness. If this property is not present, it is assumed to be\n    enabled.")
        hou_parm_template3.setTags({"cook_dependent": "1", "spare_category": "OpenGL"})
        hou_parm_template2.addParmTemplate(hou_parm_template3)

        hou_parm_template3 = hou.StringParmTemplate("ogl_coat_roughness_map", "Coat Roughness Map", 1, default_value=([""]), naming_scheme=hou.parmNamingScheme.Base1, string_type=hou.stringParmType.FileReference, menu_items=([]), menu_labels=([]), icon_names=([]), item_generator_script="", item_generator_script_language=hou.scriptLanguage.Python, menu_type=hou.menuType.StringReplace)
        hou_parm_template3.setHelp("Texture map to modulate coat roughness. The texture map value is \n    multiplied by the Coat Roughness to produce the final coat roughness \n    value.")
        hou_parm_template3.setTags({"cook_dependent": "1", "filechooser_mode": "read", "spare_category": "OpenGL"})
        hou_parm_template2.addParmTemplate(hou_parm_template3)

        hou_parm_template3 = hou.IntParmTemplate("ogl_coat_roughness_comp", "Coat Roughness Channel", 1, default_value=([0]), min=0, max=4, min_is_strict=False, max_is_strict=False, naming_scheme=hou.parmNamingScheme.Base1, menu_items=(["0","1","2","3","4"]), menu_labels=(["Luminance","Red","Green","Blue","Alpha"]), icon_names=([]), item_generator_script="", item_generator_script_language=hou.scriptLanguage.Python, menu_type=hou.menuType.Normal, menu_use_token=False)
        hou_parm_template3.setConditional(hou.parmCondType.DisableWhen, "{ ogl_coat_roughness_map == ///////\"///////\" }")
        hou_parm_template3.setHelp("The channel of Coat Roughness Map from which coat roughness is selected, \n    either the luminance of the color or one of the red, green, blue, or alpha\n    channels.")
        hou_parm_template3.setTags({"cook_dependent": "1", "spare_category": "OpenGL"})
        hou_parm_template2.addParmTemplate(hou_parm_template3)
        hou_parm_template.addParmTemplate(hou_parm_template2)
        hou_parm_template_group.append(hou_parm_template)
        hou_node.setParmTemplateGroup(hou_parm_template_group)	 

        hou_node.parm("ogl_numtex").set(1)
        hou_node.parm("ogl_tex1").lock(True)

        if srcMat:
            if srcMat.type().name()=="redshift::Material":
                wireMatOGL(hou_node, srcMat)

            if srcMat.type().name()=="redshift::TextureSampler":
         

                hou_node.parm("ogl_use_tex1").setExpression("ch('ogl_solo') || !ch('ogl_disable_tex')\n", hou.exprLanguage.Hscript)
                hou_node.parm("ogl_tex1").lock(False)
                hou_node.parm("ogl_tex1").setExpression("ifs(ch('ogl_solo'), chs('diff_override'), chs('n_diffuse'))", hou.exprLanguage.Hscript)
                hou_node.parm("ogl_tex1").lock(True)


            if srcMat.type().name()=="redshift::RSColorConstant":
                relMatPath = hou_node.relativePathTo(srcMat)
                hou_node.parmTuple("ogl_diff")[0].setExpression( "ch('"+relMatPath+"/colorr')", hou.exprLanguage.Hscript)
                hou_node.parmTuple("ogl_diff")[1].setExpression( "ch('"+relMatPath+"/colorg')", hou.exprLanguage.Hscript)
                hou_node.parmTuple("ogl_diff")[2].setExpression( "ch('"+relMatPath+"/colorb')", hou.exprLanguage.Hscript)


            

    else:
        print("no valid node/src found")

def wireMatOGL(hou_node, srcMat):

    if not srcMat:
        hou.ui.displayMessage("No connected 'RS Material' found!")
        return False

    if (srcMat.parm('refl_fresnel_mode').eval()!="2"):
     
        if hou.ui.displayConfirmation("Switch to 'Metalness' Fresnel Type?"):
         
            srcMat.parm('refl_fresnel_mode').set("2")
    
    relMatPath = hou_node.relativePathTo(srcMat)

    if hou_node:

        hou_node.parm("ogl_use_emit").setExpression("if(ch('"+relMatPath+"/emission_weight')>0,1,0 )", hou.exprLanguage.Hscript)


        hou_node.parmTuple("ogl_emit")[0].setExpression("if (ch('ogl_solo'), 0.0, if( ch('ogl_use_emissionmap') && strcmp( chs('ogl_emissionmap'), ''), 1.0, ch('"+relMatPath+"/emission_colorr')))", hou.exprLanguage.Hscript)
        hou_node.parmTuple("ogl_emit")[1].setExpression("if (ch('ogl_solo'), 0.0, if( ch('ogl_use_emissionmap') && strcmp( chs('ogl_emissionmap'), ''), 1.0, ch('"+relMatPath+"/emission_colorg')))", hou.exprLanguage.Hscript)
        hou_node.parmTuple("ogl_emit")[2].setExpression("if (ch('ogl_solo'), 0.0, if( ch('ogl_use_emissionmap') && strcmp( chs('ogl_emissionmap'), ''), 1.0, ch('"+relMatPath+"/emission_colorb')))", hou.exprLanguage.Hscript)
        
        hou_node.parmTuple("ogl_spec")[0].setExpression("if (ch('ogl_solo'), 0.0, if(ch('ogl_use_specmap') && strcmp( chs('ogl_specmap') ,'' ), 1.0, (ch('"+relMatPath+"/refl_reflectivityr')*(1-ch('"+relMatPath+"/refl_metalness')))))", hou.exprLanguage.Hscript)
        hou_node.parmTuple("ogl_spec")[1].setExpression("if (ch('ogl_solo'), 0.0, if(ch('ogl_use_specmap') && strcmp( chs('ogl_specmap') ,'' ), 1.0, (ch('"+relMatPath+"/refl_reflectivityg')*(1-ch('"+relMatPath+"/refl_metalness')))))", hou.exprLanguage.Hscript)
        hou_node.parmTuple("ogl_spec")[2].setExpression("if (ch('ogl_solo'), 0.0, if(ch('ogl_use_specmap') && strcmp( chs('ogl_specmap') ,'' ), 1.0, (ch('"+relMatPath+"/refl_reflectivityb')*(1-ch('"+relMatPath+"/refl_metalness')))))", hou.exprLanguage.Hscript)
        
        hou_node.parm("ogl_rough").setExpression("if (ch('ogl_solo'), 1.0, if( strcmp( chs('ogl_roughmap') ,'') && ch('ogl_use_roughmap'), 1.0  , ch('"+relMatPath+"/refl_roughness')  ))", hou.exprLanguage.Hscript)
        hou_node.parm("ogl_diff_intensity").setExpression("(if(ch('ogl_solo'), 1.0, ch('"+relMatPath+"/diffuse_weight')))", hou.exprLanguage.Hscript)
        hou_node.parm("ogl_diff_rough").setExpression("ch('"+relMatPath+"/diffuse_roughness')", hou.exprLanguage.Hscript)

        hou_node.parm("ogl_use_tex1").setExpression("ch('ogl_solo') || !ch('ogl_disable_tex')\n", hou.exprLanguage.Hscript)
        hou_node.parm("ogl_tex1").lock(False)
        hou_node.parm("ogl_tex1").setExpression("ifs(ch('ogl_solo'), chs('diff_override'), chs('n_diffuse'))", hou.exprLanguage.Hscript)
        hou_node.parm("ogl_tex1").lock(True)

        hou_node.parm("ogl_metallic").setExpression("if ( ch('ogl_solo'), 0.0, if( strcmp( chs('ogl_metallicmap') ,'') && ch('ogl_use_metallicmap'), 1.0  , ch('"+relMatPath+"/refl_metalness')  ))", hou.exprLanguage.Hscript)

        hou_node.parm("ogl_ior").setExpression("if ( ch('ogl_solo')==1  , 1.0 , ch('"+relMatPath+"/refl_ior')  )", hou.exprLanguage.Hscript)

        hou_node.parm("ogl_spec_intensity").setExpression("(if(ch('ogl_solo'),0.0,1.0))", hou.exprLanguage.Hscript)
        hou_node.parm("ogl_emit_intensity").setExpression("if (ch('ogl_solo'), 0.0,  ch('"+relMatPath+"/emission_weight')  )", hou.exprLanguage.Hscript)
        hou_node.parm("ogl_coat_intensity").setExpression("ch('"+relMatPath+"/coat_weight') * (if(ch('ogl_solo'),0.0,1.0))", hou.exprLanguage.Hscript)

        hou_node.parm("ogl_coat_rough").setExpression("ch('"+relMatPath+"/coat_roughness')* (if(ch('ogl_solo'),0.0,1.0))", hou.exprLanguage.Hscript)

        hou_node.parmTuple("ogl_diff")[0].setExpression( "ch('"+relMatPath+"/diffuse_colorr')", hou.exprLanguage.Hscript)
        hou_node.parmTuple("ogl_diff")[1].setExpression( "ch('"+relMatPath+"/diffuse_colorg')", hou.exprLanguage.Hscript)
        hou_node.parmTuple("ogl_diff")[2].setExpression( "ch('"+relMatPath+"/diffuse_colorb')", hou.exprLanguage.Hscript)

        hou_node.parm("ogl_metallic_edger").setExpression(  "(((ch('ogl_metallic' ) *0.5 +  ch('ogl_rough' )*0.5 )+(ch('"+relMatPath+"/refl_reflectivityr') * (1-ch('ogl_metallic'))) )) * ch('ogl_diffr')" , hou.exprLanguage.Hscript  )
        hou_node.parm("ogl_metallic_edgeg").setExpression(  "(((ch('ogl_metallic' ) *0.5 +  ch('ogl_rough' )*0.5 )+(ch('"+relMatPath+"/refl_reflectivityg') * (1-ch('ogl_metallic'))) )) * ch('ogl_diffg')", hou.exprLanguage.Hscript  )
        hou_node.parm("ogl_metallic_edgeb").setExpression(  "(((ch('ogl_metallic' ) *0.5 +  ch('ogl_rough' )*0.5 )+(ch('"+relMatPath+"/refl_reflectivityb') * (1-ch('ogl_metallic'))) )) * ch('ogl_diffb')" , hou.exprLanguage.Hscript  )





        #to avoid update issue with single channel PNGs
        hou_node.parm("ogl_metallicmap_comp").set(1)
        hou_node.parm("ogl_occlusionmap_comp").set(1)
        hou_node.parm("ogl_roughmap_comp").set(1)
 


def notes():

    #n.parm('ogl_disable_tex').set(1)
    #t.pressButton()
    #targets = filter(lambda x:x.type().name()=="redshift::Material",  n.inputAncestors())

    #cb:  import hou;tmp=not hou.pwd().evalParm('ogl_disable_tex');hou.pwd().parm("ogl_use_metallicmap").set(tmp);hou.pwd().parm("ogl_use_roughmap").set(tmp);hou.pwd().parm("ogl_use_specmap").set(tmp);hou.pwd().parm("ogl_use_normalmap").set(tmp);hou.pwd().parm("ogl_use_bumpmap").set(tmp);hou.pwd().parm("ogl_use_opacitymap").set(tmp);hou.pwd().parm("ogl_use_emissionmap").set(tmp);hou.pwd().parm("ogl_use_occlusionmap").set(tmp);hou.pwd().parm("ogl_use_coat_intensity_map").set(tmp);hou.pwd().parm("ogl_use_coat_roughness_map").set(tmp);
 

 # hou.ui.selectFromList(["waa","eerte","ERTR"], default_choices=(), exclusive=True, message="Select a Redshift Material to show this Map on", title=None, column_header="Materials", num_visible_rows=10, clear_on_cancel=False, width=0, height=0)
    
        

    pass

def EnableSolo(args):

    node=args['node']

    for item in getRelatedMaterials(node):
        try:
            if item.evalParm("diff_override")!=node.evalParm("tex0"):
                return True
        except:
            pass
    return False


def EnableUnSolo(args):

    node=args['node']

    for item in getRelatedMaterials(node):
        try:
            if item.evalParm("ogl_solo"):
                return True
        except:
            pass
    return False


def getRelatedMaterials(n, specific=False, warning=False):
     
    if not n:
        return False
    context=getMatContextType(n)
 
  
    out=[]
     
    if context=="redshift_vopnet":
        tmp=getContainerNode(n)
        try:
            if tmp.evalParm('ogl_solo')==True or tmp.evalParm('ogl_solo')==False:
                out.append(tmp)
        except:
            pass

    if context=="matnet":
         
        link=[] 
        def recurLinks(n):
            for i in n.outputs():
                if not i in link:
                  link.append(i)
                recurLinks(i)
            return link
        res=recurLinks(n)

        opt=[]
        optn=[]
   
        for item in res:
            if item.type().name()=="redshift_material":
                try:
                    if len( item.parm("ogl_diffr").rawValue().split("/"))>1:
                        opt.append( item.parm("ogl_diffr").rawValue().split("/")[1]  )
                    else:
                        opt.append(None)
                    optn.append( item )
                except:
                    pass

        if len(opt)==0 and warning:
            hou.ui.displayMessage("This map is not connected to an OpenGL enabled material")

        if len(opt)==1 or not specific:
            out=optn

        if len(opt)>1 and specific:
            tmp=hou.ui.selectFromList(opt, default_choices=(), exclusive=False, message="Select a Redshift Material to show this TextureMap on", title=None, column_header="Materials", num_visible_rows=10, clear_on_cancel=False, width=0, height=0)
            if len(tmp)!=0:
                for ind in tmp:
                    out.append(optn[ind])
 
    return out


def getRelatedOutputs(n, specific=False, warning=False):
     
    if not n:
        return False
    context=getMatContextType(n) 

    out=[]
     
    link=[] 
    def recurLinks(n):
        for i in n.outputs():
            if not i in link:
              link.append(i)
            recurLinks(i)
        return link
    res=recurLinks(n)

    optn=[]

    for item in res:
        if item.type().name()=="redshift_material":
            optn.append( item )


    return optn



def usedMaps(args):

    maps=getMaps()
    out=[]

    for node in args['items']:

        context=getMatContextType(node)

        for m in maps:

            ogl_node=node
            if context=="redshift_vopnet":
                ogl_node=getContainerNode(node)
            try:
                if ogl_node.evalParm(m[4])!='':
                    out.append( [m,  ogl_node.parm(m[4]).path()]  )
            except:
                pass	
    return out


def getMaps():

    types=[]
    types.append(["Diffuse", ["basecolor", "diff","albedo"], 'diffuse_color', "Diffuse", 'n_diffuse'])
    types.append(["Roughness", ["rough"], 'refl_roughness' ,"Roughness",'ogl_roughmap'])
    types.append(["Metallic", ["metal"], 'refl_metalness' ,"Metallic",'ogl_metallicmap'])
    types.append(["Normal", ["normal"], 'Bump Map' , "Normal Map", 'ogl_normalmap'])
    types.append(["Displacement", ["displace", "height"] , 'texMap' ,"Displacement", 'ogl_displacemap'])
    types.append(["Emission",["emission"], 'emission_color' ,"Emission", 'ogl_emissionmap'])
    types.append(["Specular",["spec"], 'no_auto' ,"Specular", 'ogl_specmap'])
    types.append(["Bump",["bump"], 'Bump Map' ,"Bump", 'ogl_bumpmap'])
    types.append(["Coat_int",["coat_int"], 'coat_color' ,"Coat Intensity", 'ogl_coat_intensity_map'])
    types.append(["Coat_ruff",["coat_ruff"], 'coat_roughness',"Coat Roughness", 'ogl_coat_roughness_map'])

    return types

def guessType(name):

    name=os.path.basename(name).lower()

    types=getMaps()

    for item in types:
        for sub in item[1]:
            if sub in name:
 
                return item
                break
    return False



def adobeColor(args, check=False):
    from xml.dom.minidom import parse, parseString
    from PySide2 import QtCore, QtGui, QtWidgets
    import hou

    
    clipboard = QtWidgets.QApplication.clipboard()

    d=clipboard.text()
    
    out=[]
    try:
        tree = parseString(d)
        if len(tree.getElementsByTagName('color'))==5:
            for item in tree.getElementsByTagName('color'):
                r=(int(item.attributes['r'].value)/255.0)
                g=(int(item.attributes['g'].value)/255.0)
                b=(int(item.attributes['b'].value)/255.0)
                out.append( [item.attributes['name'].value, hou.Color(r,g,b) ])
        else:
            return False
 
    except:
        return False
 
    if len(out)==5 and len( args['items'])==5:
        if check: 
            return True

        else:

            args['items'].sort( key=lambda a:a.position()[1], reverse=True )

            i=0;
            for item in  args['items']:
                item.setColor( out[i][1] )
         
                item.setName( out[i][0], True)

                item.parm('diffuse_colorr').set(out[i][1].rgb()[0])
                item.parm('diffuse_colorg').set(out[i][1].rgb()[1])
                item.parm('diffuse_colorb').set(out[i][1].rgb()[2])


                i=i+1

    else:
        return False


def autoConnect(args, testValid=False):

    tex=[]
    mat=[]
    out=[]

    allNodes=args['items'] 


    for item in args['items']:
        if item.type().name()=="redshift::Material" or item.type().name()=="redshift::Displacement":
            mat.append(item)
          

        if item.type().name()=="redshift::TextureSampler":
            tex.append(item)

        if item.type().name()=="redshift_material":
            out.append(item) 

    if testValid:
        return len(mat)>0 and len(tex)>0        
   
    for item in tex:
        try:
            res= guessType(item.evalParm('tex0')) 
 
            if res!=False:
              
                for m in mat:
                    
                    if m.inputIndex(res[2])!=-1:
                        m.setInput(m.inputIndex(res[2]) , item)
 
                    else:
 
                        for o in getRelatedOutputs(m):
                            if o in out:
                                if o.inputIndex(res[2])!=-1 and res[0]!="Normal":
                                    o.setInput(o.inputIndex(res[2]) , item)        
                                
                                if (res[0]=="Normal"): 
                                    if True:
                                        disp=o.inputConnectors()[2]  
                                      
                                         
                                        if len(disp)==0:
                                            disp=False
                                           
                                            for q in item.outputs():
                                                if q.type().name()=="redshift::BumpMap":
                                                     
                                                    disp=q
                                                    o.setInput( o.inputIndex("Bump Map")  , disp) 
                                                    break
                                            if disp==False:    
                                                
                                                disp=item.parent().createNode("redshift::BumpMap")
                                                allNodes.append(disp)
                                                o.setInput( o.inputIndex("Bump Map")  , disp) 
                                        else:
                                             
                                            disp=disp[0].inputItem()
                                        if disp.inputIndex("input")!=-1:
                                           disp.setInput( disp.inputIndex("input"), item)

                                if (res[0]=="Displacement"):
                                    if True:
                                        disp=o.inputConnectors()[1]  
                                        
                                        if len(disp)==0:
                                            disp=False
                                            for q in item.outputs():
                                                if q.type().name()=="redshift::Displacement":
                                                    disp=q
                                                    o.setInput( o.inputIndex("Displacement")  , disp) 
                                                    break
                                            if disp==False:    
                                                disp=item.parent().createNode("redshift::Displacement")
                                                allNodes.append(disp)
                                                o.setInput( o.inputIndex("Displacement")  , disp) 
                                        else:
                                            disp=disp[0].inputItem()
                                        if disp.inputIndex("texMap")!=-1:
                                            disp.setInput( disp.inputIndex("texMap"), item)
 
                args["items"]=[item]  
                
                SetOGL(res[0].lower(), args, False)
        except:
            pass   
    
    allNodes[0].parent().layoutChildren(allNodes)


def checkSel(args, types):

    out=True
    for item in args['items']:
 
        if item.type().name() not in types:
 
                out=False
                break

    return out

 