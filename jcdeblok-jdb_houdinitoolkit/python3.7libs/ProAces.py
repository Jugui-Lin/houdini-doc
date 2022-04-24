import hou
import os
import imghdr
import re

setComment=True


def AcesActive():
    if (hou.getenv("OCIO")==None):
        return False
    if not os.path.exists(hou.getenv("OCIO")):
        return False
    return True

def enum(**enums):
    return type('Enum', (), enums)

TexType = enum(NotManaged = 0,  Color = 1, Data = 2, HDR = 3, Exact = 4, Manual=5)

def setComment(node, comment):
    if bool(hou.getenv("PROACES_ADD_COMMENTS", "1" )):
        node.setComment(comment)
        node.setGenericFlag(hou.nodeFlag.DisplayComment,True)  

def isAces(fileParm):
    tmp=fileParm.eval().lower()
    return "aces" in tmp and ".exr" in tmp

def isImage(parm):
    tmp=parm.eval()
    if os.path.exists(tmp):
        try:
            chk=hou.imageResolution(tmp)
            if len(chk)==2:
                return True
        except:
            return False


            
    return False

def addProAcesParms(node):
   
    parm_group = node.parmTemplateGroup()
    if not parm_group.findFolder("ProACES"):
        parm_folder = hou.FolderParmTemplate("folder", "ProACES")
        parm_folder.addParmTemplate(hou.StringParmTemplate("proaces_orig", "Original", 1))
        parm_folder.addParmTemplate(hou.ToggleParmTemplate("proaces_auto", "Auto Manage", bool(hou.getenv("PROACES_AUTO_CONVERT", "1" )) ))
        parm_group.append(parm_folder)
        parm_group.hideFolder("ProACES", True)
        node.setParmTemplateGroup(parm_group)

def Revert(fileParm):
    origFile=GetOrigFile(fileParm)
    if origFile:
        if os.path.exists(hou.expandString( origFile)):
            tmp= GetAutoAces(fileParm)
            SetAutoAces(fileParm, False)
            fileParm.set(origFile)
            setComment(fileParm.node(),"")
            SetAutoAces(fileParm, tmp)

def GetAutoSpace(fileParm):

    imageFile=fileParm.eval()
    filename= os.path.basename(imageFile)
    ext= os.path.splitext(filename)[1].lower()


    datatype=TexType.Color   #assume color as default

    ignore=[".psd","op:"]
    color=["basecolor", "diff","albedo", "emission", "coat", "refl" ]
    data = ["rough", "ruff", "metal", "normal", "displace", "height", "spec", "bump","opacity", "AO"]
    hdr= [".hdr"]

    if any(x in filename.lower() for x in ignore) or (ext in ignore):
          datatype = TexType.NotManaged
    else:

        if any(x in filename.lower() for x in color):
            datatype=TexType.Color

        if any(x in filename.lower() for x in data):
            datatype=TexType.Data

        if any(x in filename.lower() for x in hdr) or ext in hdr:
            datatype=TexType.HDR      
   
    return datatype

def SetAutoAces(fileParm, mode):
    node = fileParm.node()
    addProAcesParms(node)
    if node.parm("proaces_auto"):
        node.parm("proaces_auto").set(mode)

def GetAutoAces(fileParm):
    node = fileParm.node()
    if node.parm("proaces_auto"):
        return node.parm("proaces_auto").eval()
    return False

def cleanName(name):
    return re.sub("[^0-9a-zA-Z\.]+", "_", name)

def GetOrigFile(fileParm, checkRevertable=False):
    node = fileParm.node()
    if node.parm("proaces_orig"):

        if checkRevertable:
            try:
                ofilename= os.path.basename(node.parm("proaces_orig").rawValue())
                oparts= os.path.splitext(ofilename) 

                cfilename= os.path.basename(fileParm.rawValue())
                cparts= os.path.splitext(cfilename) 

                return  oparts[0] in cparts[0] and oparts[0]!=cparts[0]  
            except:
                return False     

        return node.parm("proaces_orig").rawValue()
    return False

def SetOrigFile(fileParm, file):
 
    node = fileParm.node()
    addProAcesParms(node)
    if node.parm("proaces_orig"):
        if os.path.exists(hou.expandString(file)):
            node.parm("proaces_orig").set(file)


def Convert(fileParm, datatype, forcespace=None):
   
    node = fileParm.node()
  
    addProAcesParms(node)
    SetAutoAces(fileParm, datatype!=TexType.Manual)

    imageFile=fileParm.eval()
    if not os.path.exists(imageFile):
        return False

    filename= os.path.basename(imageFile)
    ext= os.path.splitext(filename)[1].lower()

    if isAces(fileParm):
        origFile=hou.expandString( GetOrigFile(fileParm) )
        
        if origFile!=False:
            if not os.path.exists(origFile):
                hou.ui.displayMessage("Aborting due to missing original image file:\n"+origFile)
            else:
                imageFile=origFile
                filename= os.path.basename(imageFile)
                ext= os.path.splitext(filename)[1].lower()  
    else:
        SetOrigFile(fileParm, fileParm.rawValue())

    if datatype==TexType.NotManaged:
        setComment(node,"Not ACES managed")
        return False

    #Perform actions based on datatype 
    if datatype==TexType.Data:
        if fileParm.name()=="tex0" and node.type().name()=="redshift::TextureSampler":
            node.parm("tex0_gammaoverride").set(1)
            node.parm("tex0_srgb").set(0)
            node.parm("tex0_gamma").set(1)
        setComment(node, "Data - Linear\nNo ACES conversion")

        return False

    if datatype==TexType.Color or datatype==TexType.HDR or datatype==TexType.Manual or datatype==TexType.Exact:
        cop=createCOP(node.name()+"_ACES_helper")
        
        cop.node('IN_image').parm("filename1").set(imageFile)
        tmp=os.path.basename(imageFile).split(".")[:-1]
        tmp[0]=tmp[0]+"_ACEScg"
        outFile=os.path.dirname(imageFile)+"/"+".".join(tmp)+".exr"

        cop.node('OUT_image').parm("copoutput").set(outFile)
        
        if datatype==TexType.Color:
            cop.node('colorspace_transform/ocio_transform1').parm("fromspace").set("Utility - sRGB - Texture")
            cop.node('IN_image').parm("linearize").set(0)
            setComment(node, "ACEScg\nOrig: "+ext+"\nAuto: Utility - sRGB - Texture")

        if datatype==TexType.HDR:
            cop.node('colorspace_transform/ocio_transform1').parm("fromspace").set("Utility - Linear - sRGB")
            cop.node('IN_image').parm("linearize").set(0)
            setComment(node, "ACEScg\nOrig: "+ext+"\nAuto: Utility - Linear - sRGB")

        if datatype==TexType.Manual:
            cop.node('colorspace_transform/ocio_transform1').parm("fromspace").set(forcespace[0])
            cop.node('IN_image').parm("linearize").set(0)
            setComment(node, "ACEScg\nOrig: "+ext+"\n"+forcespace[1])


        if datatype==TexType.Exact:
            cop.node('colorspace_transform/ocio_transform1').parm("fromspace").set(forcespace[0])
            cop.node('IN_image').parm("linearize").set(0)
            setComment(node, "ACEScg\nOrig: "+ext+"\n"+forcespace[1])

        cop.node('colorspace_transform/ocio_transform1').parm("tospace").set("ACES - ACEScg")
        
        if fileParm.name()=="tex0" and node.type().name()=="redshift::TextureSampler":
            node.parm("tex0_gammaoverride").set(0)
        
        cop.node('OUT_image').parm("trange").set(0)
        cop.node('OUT_image').parm("execute").pressButton()

        tmp =  GetAutoAces(fileParm)
        SetAutoAces(fileParm, False)
        fileParm.set(outFile)
        cop.destroy()
        SetAutoAces(fileParm, tmp)          
        
        return True


def UpdateEventHandler(  **kwargs):

    if not AcesActive():
        return False

    fileParm = kwargs['parm_tuple'][0]
    node = kwargs['node']



    if fileParm.name()=="tex0" and node.type().name()=="redshift::TextureSampler":

        imageFile=fileParm.eval()

        filename= os.path.basename(imageFile)
        ext= os.path.splitext(filename)[1].lower()
        try:
            pass
            #node.setName(cleanName(os.path.splitext(filename)[0]), True )
        except:
            pass

        if not GetAutoAces(fileParm):
            return False

        if not isAces(fileParm):
            SetOrigFile(fileParm, fileParm.rawValue())

        #checkif already aces
        if isAces(fileParm):
       
            if hou.node("/img/"+node.name()+"_ACES_helper"):
                hou.node("/img/"+node.name()+"_ACES_helper").destroy()
            else:
                setComment(node,"ACEScg (assumed)")    
            return True

        else:
            setComment(node,"")  
            Convert(fileParm,  GetAutoSpace(fileParm) )


def createCOP(name):

    if hou.node("/img/"+name):
        return hou.node("/img/"+name)

    hou_parent = hou.node("/img")
    # Code for /img/ProAces
    hou_node = hou_parent.createNode("img", name, run_init_scripts=False, load_contents=True, exact_type_name=True)
    out = hou_node
 
    hou_node.move(hou.Vector2(-1.29591, -0.369939))
    hou_node.hide(False)
    hou_node.setSelected(True)
    hou_node.setExpressionLanguage(hou.exprLanguage.Hscript)

    if hasattr(hou_node, "syncNodeVersionIfNeeded"):
        hou_node.syncNodeVersionIfNeeded("18.0.416")
    # Update the parent node.
    hou_parent = hou_node

    # Code for /img/waa/colorspace_transform
    hou_node = hou_parent.createNode("vopcop2filter", "colorspace_transform", run_init_scripts=False, load_contents=True, exact_type_name=True)
    hou_node.move(hou.Vector2(-5.57182, -1.15515))
    hou_node.bypass(False)
    hou_node.setDisplayFlag(True)
    hou_node.setCompressFlag(False)
    hou_node.hide(False)
    hou_node.setSelected(False)
    hou_node.setRenderFlag(True)
    hou_node.setTemplateFlag(False)

    hou_parm_template_group = hou.ParmTemplateGroup()
    # Code for parameter template
    hou_parm_template = hou.FolderParmTemplate("stdswitcher", "Compiler", folder_type=hou.folderType.Tabs, default_value=0, ends_tab_group=False)
    # Code for parameter template
    hou_parm_template2 = hou.StringParmTemplate("vop_compiler", "Compiler", 1, default_value=(["vcc -q $VOP_INCLUDEPATH -o $VOP_OBJECTFILE -e $VOP_ERRORFILE $VOP_SOURCEFILE"]), naming_scheme=hou.parmNamingScheme.Base1, string_type=hou.stringParmType.Regular, menu_items=([]), menu_labels=([]), icon_names=([]), item_generator_script="", item_generator_script_language=hou.scriptLanguage.Python, menu_type=hou.menuType.Normal)
    hou_parm_template.addParmTemplate(hou_parm_template2)
    # Code for parameter template
    hou_parm_template2 = hou.ButtonParmTemplate("vop_forcecompile", "Force Compile")
    hou_parm_template.addParmTemplate(hou_parm_template2)
    hou_parm_template_group.append(hou_parm_template)
    # Code for parameter template
    hou_parm_template = hou.FolderParmTemplate("stdswitcher_1", "Mask", folder_type=hou.folderType.Tabs, default_value=0, ends_tab_group=False)
    # Code for parameter template
    hou_parm_template2 = hou.FloatParmTemplate("effectamount", "Effect Amount", 1, default_value=([1]), min=0, max=1, min_is_strict=False, max_is_strict=False, look=hou.parmLook.Regular, naming_scheme=hou.parmNamingScheme.Base1)
    hou_parm_template.addParmTemplate(hou_parm_template2)
    # Code for parameter template
    hou_parm_template2 = hou.MenuParmTemplate("maskinput", "Operation Mask", menu_items=(["first","mask","off"]), menu_labels=(["First Input","Mask Input","Off"]), default_value=1, icon_names=([]), item_generator_script="", item_generator_script_language=hou.scriptLanguage.Python, menu_type=hou.menuType.Normal, menu_use_token=False, is_button_strip=False, strip_uses_icons=False)
    hou_parm_template2.setJoinWithNext(True)
    hou_parm_template.addParmTemplate(hou_parm_template2)
    # Code for parameter template
    hou_parm_template2 = hou.StringParmTemplate("maskplane", "", 1, default_value=(["A"]), naming_scheme=hou.parmNamingScheme.Base1, string_type=hou.stringParmType.Regular, menu_items=([]), menu_labels=([]), icon_names=([]), item_generator_script="", item_generator_script_language=hou.scriptLanguage.Python, menu_type=hou.menuType.Normal)
    hou_parm_template2.hideLabel(True)
    hou_parm_template.addParmTemplate(hou_parm_template2)
    # Code for parameter template
    hou_parm_template2 = hou.ToggleParmTemplate("maskresize", "Resize Mask to Fit Image", default_value=False)
    hou_parm_template.addParmTemplate(hou_parm_template2)
    # Code for parameter template
    hou_parm_template2 = hou.ToggleParmTemplate("maskinvert", "Invert Mask", default_value=False)
    hou_parm_template.addParmTemplate(hou_parm_template2)
    # Code for parameter template
    hou_parm_template2 = hou.IntParmTemplate("scopergba", "Plane Scope", 1, default_value=([15]), min=0, max=10, min_is_strict=False, max_is_strict=False, naming_scheme=hou.parmNamingScheme.Base1, menu_items=([]), menu_labels=([]), icon_names=([]), item_generator_script="", item_generator_script_language=hou.scriptLanguage.Python, menu_type=hou.menuType.Normal, menu_use_token=False)
    hou_parm_template2.setJoinWithNext(True)
    hou_parm_template.addParmTemplate(hou_parm_template2)
    # Code for parameter template
    hou_parm_template2 = hou.StringParmTemplate("pscope", "", 1, default_value=(["*"]), naming_scheme=hou.parmNamingScheme.Base1, string_type=hou.stringParmType.Regular, menu_items=([]), menu_labels=([]), icon_names=([]), item_generator_script="", item_generator_script_language=hou.scriptLanguage.Python, menu_type=hou.menuType.StringToggle)
    hou_parm_template2.hideLabel(True)
    hou_parm_template.addParmTemplate(hou_parm_template2)
    hou_parm_template_group.append(hou_parm_template)
    # Code for parameter template
    hou_parm_template = hou.FolderParmTemplate("stdswitcher_2", "Frame Scope", folder_type=hou.folderType.Tabs, default_value=0, ends_tab_group=False)
    # Code for parameter template
    hou_parm_template2 = hou.MenuParmTemplate("fscope", "Frame Scope", menu_items=(["all","inside","outside","even","odd","specific"]), menu_labels=(["All Frames","Inside Range","Outside Range","Even Frames","Odd Frames","Specific Frames"]), default_value=0, icon_names=([]), item_generator_script="", item_generator_script_language=hou.scriptLanguage.Python, menu_type=hou.menuType.Normal, menu_use_token=False, is_button_strip=False, strip_uses_icons=False)
    hou_parm_template.addParmTemplate(hou_parm_template2)
    # Code for parameter template
    hou_parm_template2 = hou.FloatParmTemplate("frange", "Frame Range", 2, default_value=([1, 1]), min=0, max=10, min_is_strict=False, max_is_strict=False, look=hou.parmLook.Regular, naming_scheme=hou.parmNamingScheme.Base1)
    hou_parm_template.addParmTemplate(hou_parm_template2)
    # Code for parameter template
    hou_parm_template2 = hou.FloatParmTemplate("fdropoff", "Frame Dropoff", 2, default_value=([0, 0]), min=0, max=10, min_is_strict=True, max_is_strict=False, look=hou.parmLook.Regular, naming_scheme=hou.parmNamingScheme.Base1)
    hou_parm_template2.setJoinWithNext(True)
    hou_parm_template.addParmTemplate(hou_parm_template2)
    # Code for parameter template
    hou_parm_template2 = hou.MenuParmTemplate("fdropfunc", "", menu_items=(["linear","easein","easeout","easeinout"]), menu_labels=(["Linear","Ease In","Ease Out","Ease In Ease Out"]), default_value=0, icon_names=([]), item_generator_script="", item_generator_script_language=hou.scriptLanguage.Python, menu_type=hou.menuType.Normal, menu_use_token=False, is_button_strip=False, strip_uses_icons=False)
    hou_parm_template2.hideLabel(True)
    hou_parm_template.addParmTemplate(hou_parm_template2)
    # Code for parameter template
    hou_parm_template2 = hou.FloatParmTemplate("foutside", "Non-scoped Effect", 1, default_value=([0]), min=0, max=1, min_is_strict=False, max_is_strict=False, look=hou.parmLook.Regular, naming_scheme=hou.parmNamingScheme.Base1)
    hou_parm_template.addParmTemplate(hou_parm_template2)
    # Code for parameter template
    hou_parm_template2 = hou.StringParmTemplate("flist", "Frame List", 1, default_value=(["*"]), naming_scheme=hou.parmNamingScheme.Base1, string_type=hou.stringParmType.Regular, menu_items=([]), menu_labels=([]), icon_names=([]), item_generator_script="", item_generator_script_language=hou.scriptLanguage.Python, menu_type=hou.menuType.Normal)
    hou_parm_template2.setJoinWithNext(True)
    hou_parm_template.addParmTemplate(hou_parm_template2)
    # Code for parameter template
    hou_parm_template2 = hou.MenuParmTemplate("fmenu", "", menu_items=(["scopeall","scopecur","scopetocur","scopefromcur","unscopeall","unscopecur","unscopetocur","unscopefromcur"]), menu_labels=(["Scope All Frames","Scope Current Frame","Scope From Start To Current","Scope From Current To End","Unscope All Frames","Unscope Current Frame","Unscope From Start To Current","Unscope From Current To End"]), default_value=0, icon_names=([]), item_generator_script="", item_generator_script_language=hou.scriptLanguage.Python, menu_type=hou.menuType.Mini, menu_use_token=False, is_button_strip=False, strip_uses_icons=False)
    hou_parm_template.addParmTemplate(hou_parm_template2)
    # Code for parameter template
    hou_parm_template2 = hou.ToggleParmTemplate("fautoadjust", "Automatically Adjust for Length Changes", default_value=True)
    hou_parm_template.addParmTemplate(hou_parm_template2)
    # Code for parameter template
    hou_parm_template2 = hou.IntParmTemplate("currange", "", 1, default_value=([1]), min=0, max=10, min_is_strict=False, max_is_strict=False, naming_scheme=hou.parmNamingScheme.Base1, menu_items=([]), menu_labels=([]), icon_names=([]), item_generator_script="", item_generator_script_language=hou.scriptLanguage.Python, menu_type=hou.menuType.Normal, menu_use_token=False)
    hou_parm_template2.hide(True)
    hou_parm_template.addParmTemplate(hou_parm_template2)
    hou_parm_template_group.append(hou_parm_template)
    hou_node.setParmTemplateGroup(hou_parm_template_group)
    # Code for /img/waa/colorspace_transform/stdswitcher1 parm 
    if locals().get("hou_node") is None:
        hou_node = hou.node("/img/waa/colorspace_transform")
    hou_parm = hou_node.parm("stdswitcher1")
    hou_parm.set(1)


    # Code for /img/waa/colorspace_transform/scopergba parm 
    if locals().get("hou_node") is None:
        hou_node = hou.node("/img/waa/colorspace_transform")
    hou_parm = hou_node.parm("scopergba")
    hou_parm.set(7)


    # Code for /img/waa/colorspace_transform/currange parm 
    if locals().get("hou_node") is None:
        hou_node = hou.node("/img/waa/colorspace_transform")
    hou_parm = hou_node.parm("currange")
    hou_parm.set("2000")


    hou_node.setColor(hou.Color([0.7, 0.5, 0.7]))
    hou_node.setExpressionLanguage(hou.exprLanguage.Hscript)

    if hasattr(hou_node, "syncNodeVersionIfNeeded"):
        hou_node.syncNodeVersionIfNeeded("18.0.416")
    # Update the parent node.
    hou_parent = hou_node

    # Code for /img/waa/colorspace_transform/global1
    hou_node = hou_parent.createNode("global", "global1", run_init_scripts=False, load_contents=True, exact_type_name=True)
    hou_node.move(hou.Vector2(0.225765, 0.384168))
    hou_node.setDebugFlag(False)
    hou_node.setDetailLowFlag(False)
    hou_node.setDetailMediumFlag(False)
    hou_node.setDetailHighFlag(True)
    hou_node.bypass(False)
    hou_node.setCompressFlag(True)
    hou_node.hide(False)
    hou_node.setSelected(False)

    # Code for /img/waa/colorspace_transform/global1/contexttype parm 
    if locals().get("hou_node") is None:
        hou_node = hou.node("/img/waa/colorspace_transform/global1")
    hou_parm = hou_node.parm("contexttype")
    hou_parm.set("cop2")


    hou_node.setExpressionLanguage(hou.exprLanguage.Hscript)

    if hasattr(hou_node, "syncNodeVersionIfNeeded"):
        hou_node.syncNodeVersionIfNeeded("18.0.416")
    # Update the parent node.
    hou_parent = hou_node


    # Restore the parent and current nodes.
    hou_parent = hou_parent.parent()
    hou_node = hou_node.parent()

    # Code for /img/waa/colorspace_transform/output1
    hou_node = hou_parent.createNode("output", "output1", run_init_scripts=False, load_contents=True, exact_type_name=True)
    hou_node.move(hou.Vector2(13.2165, -0.104538))
    hou_node.setDebugFlag(False)
    hou_node.setDetailLowFlag(False)
    hou_node.setDetailMediumFlag(False)
    hou_node.setDetailHighFlag(True)
    hou_node.bypass(False)
    hou_node.setCompressFlag(True)
    hou_node.hide(False)
    hou_node.setSelected(False)

    # Code for /img/waa/colorspace_transform/output1/contexttype parm 
    if locals().get("hou_node") is None:
        hou_node = hou.node("/img/waa/colorspace_transform/output1")
    hou_parm = hou_node.parm("contexttype")
    hou_parm.set("cop2")


    # Code for /img/waa/colorspace_transform/output1/outputcodelast parm 
    if locals().get("hou_node") is None:
        hou_node = hou.node("/img/waa/colorspace_transform/output1")
    hou_parm = hou_node.parm("outputcodelast")
    hou_parm.set(1)


    hou_node.setExpressionLanguage(hou.exprLanguage.Hscript)

    if hasattr(hou_node, "syncNodeVersionIfNeeded"):
        hou_node.syncNodeVersionIfNeeded("18.0.416")
    # Update the parent node.
    hou_parent = hou_node


    # Restore the parent and current nodes.
    hou_parent = hou_parent.parent()
    hou_node = hou_node.parent()

    # Code for /img/waa/colorspace_transform/vectofloat1
    hou_node = hou_parent.createNode("vectofloat", "vectofloat1", run_init_scripts=False, load_contents=True, exact_type_name=True)
    hou_node.move(hou.Vector2(9.53072, 1.36417))
    hou_node.setDebugFlag(False)
    hou_node.setDetailLowFlag(False)
    hou_node.setDetailMediumFlag(False)
    hou_node.setDetailHighFlag(True)
    hou_node.bypass(False)
    hou_node.setCompressFlag(True)
    hou_node.hide(False)
    hou_node.setSelected(False)

    hou_node.setExpressionLanguage(hou.exprLanguage.Hscript)

    if hasattr(hou_node, "syncNodeVersionIfNeeded"):
        hou_node.syncNodeVersionIfNeeded("")
    # Update the parent node.
    hou_parent = hou_node


    # Restore the parent and current nodes.
    hou_parent = hou_parent.parent()
    hou_node = hou_node.parent()

    # Code for /img/waa/colorspace_transform/floattovec1
    hou_node = hou_parent.createNode("floattovec", "floattovec1", run_init_scripts=False, load_contents=True, exact_type_name=True)
    hou_node.move(hou.Vector2(3.54803, 1.18134))
    hou_node.setDebugFlag(False)
    hou_node.setDetailLowFlag(False)
    hou_node.setDetailMediumFlag(False)
    hou_node.setDetailHighFlag(True)
    hou_node.bypass(False)
    hou_node.setCompressFlag(True)
    hou_node.hide(False)
    hou_node.setSelected(False)

    hou_node.setExpressionLanguage(hou.exprLanguage.Hscript)

    if hasattr(hou_node, "syncNodeVersionIfNeeded"):
        hou_node.syncNodeVersionIfNeeded("")
    # Update the parent node.
    hou_parent = hou_node


    # Restore the parent and current nodes.
    hou_parent = hou_parent.parent()
    hou_node = hou_node.parent()

    # Code for /img/waa/colorspace_transform/ocio_transform1
    hou_node = hou_parent.createNode("ocio_transform", "ocio_transform1", run_init_scripts=False, load_contents=True, exact_type_name=True)
    hou_node.move(hou.Vector2(6.61323, 1.18134))
    hou_node.setDebugFlag(False)
    hou_node.setDetailLowFlag(False)
    hou_node.setDetailMediumFlag(False)
    hou_node.setDetailHighFlag(True)
    hou_node.bypass(False)
    hou_node.setCompressFlag(True)
    hou_node.hide(False)
    hou_node.setSelected(False)

    # Code for /img/waa/colorspace_transform/ocio_transform1/fromspace parm 
    if locals().get("hou_node") is None:
        hou_node = hou.node("/img/waa/colorspace_transform/ocio_transform1")
    hou_parm = hou_node.parm("fromspace")
    hou_parm.set("Utility - Curve - sRGB")


    # Code for /img/waa/colorspace_transform/ocio_transform1/tospace parm 
    if locals().get("hou_node") is None:
        hou_node = hou.node("/img/waa/colorspace_transform/ocio_transform1")
    hou_parm = hou_node.parm("tospace")
    hou_parm.set("ACES - ACEScg")


    hou_node.setExpressionLanguage(hou.exprLanguage.Hscript)

    if hasattr(hou_node, "syncNodeVersionIfNeeded"):
        hou_node.syncNodeVersionIfNeeded("")
    # Update the parent node.
    hou_parent = hou_node


    # Restore the parent and current nodes.
    hou_parent = hou_parent.parent()
    hou_node = hou_node.parent()

    # Code to establish connections for /img/waa/colorspace_transform/output1
    hou_node = hou_parent.node("output1")
    if hou_parent.node("vectofloat1") is not None:
        hou_node.setInput(0, hou_parent.node("vectofloat1"), 0)
    if hou_parent.node("vectofloat1") is not None:
        hou_node.setInput(1, hou_parent.node("vectofloat1"), 1)
    if hou_parent.node("vectofloat1") is not None:
        hou_node.setInput(2, hou_parent.node("vectofloat1"), 2)
    if hou_parent.node("global1") is not None:
        hou_node.setInput(3, hou_parent.node("global1"), 6)
    # Code to establish connections for /img/waa/colorspace_transform/vectofloat1
    hou_node = hou_parent.node("vectofloat1")
    if hou_parent.node("ocio_transform1") is not None:
        hou_node.setInput(0, hou_parent.node("ocio_transform1"), 0)
    # Code to establish connections for /img/waa/colorspace_transform/floattovec1
    hou_node = hou_parent.node("floattovec1")
    if hou_parent.node("global1") is not None:
        hou_node.setInput(0, hou_parent.node("global1"), 3)
    if hou_parent.node("global1") is not None:
        hou_node.setInput(1, hou_parent.node("global1"), 4)
    if hou_parent.node("global1") is not None:
        hou_node.setInput(2, hou_parent.node("global1"), 5)
    # Code to establish connections for /img/waa/colorspace_transform/ocio_transform1
    hou_node = hou_parent.node("ocio_transform1")
    if hou_parent.node("floattovec1") is not None:
        hou_node.setInput(0, hou_parent.node("floattovec1"), 0)

    # Restore the parent and current nodes.
    hou_parent = hou_parent.parent()
    hou_node = hou_node.parent()

    # Code for /img/waa/IN_image
    hou_node = hou_parent.createNode("file", "IN_image", run_init_scripts=False, load_contents=True, exact_type_name=True)
    hou_node.move(hou.Vector2(-4.57182, 4.22253))
    hou_node.bypass(False)
    hou_node.setDisplayFlag(False)
    hou_node.setCompressFlag(False)
    hou_node.hide(False)
    hou_node.setSelected(False)
    hou_node.setRenderFlag(False)
    hou_node.setTemplateFlag(False)

    # Code for /img/waa/IN_image/filename parm tuple
    if locals().get("hou_node") is None:
        hou_node = hou.node("/img/waa/IN_image")
    hou_parm_tuple = hou_node.parmTuple("filename")
    hou_parm_tuple.set(("", "cinspace lin cinlut \"\" cinwhite 685 cingamma 0.6"))


    # Code for /img/waa/IN_image/nodename parm 
    if locals().get("hou_node") is None:
        hou_node = hou.node("/img/waa/IN_image")
    hou_parm = hou_node.parm("nodename")
    hou_parm.set("userdef")


    # Code for /img/waa/IN_image/size parm tuple
    if locals().get("hou_node") is None:
        hou_node = hou.node("/img/waa/IN_image")
    hou_parm_tuple = hou_node.parmTuple("size")
    hou_parm_tuple.set((7092, 3546))


    # Code for /img/waa/IN_image/aspect parm 
    if locals().get("hou_node") is None:
        hou_node = hou.node("/img/waa/IN_image")
    hou_parm = hou_node.parm("aspect")

    # Code for first keyframe.
    # Code for keyframe.
    hou_keyframe = hou.Keyframe()
    hou_keyframe.setTime(0)
    hou_keyframe.interpretAccelAsRatio(False)
    hou_keyframe.setExpression("$CPIXA", hou.exprLanguage.Hscript)
    hou_parm.setKeyframe(hou_keyframe)

    # Code for last keyframe.
    # Code for keyframe.
    hou_keyframe = hou.Keyframe()
    hou_keyframe.setTime(0)
    hou_keyframe.interpretAccelAsRatio(False)
    hou_keyframe.setExpression("$CPIXA", hou.exprLanguage.Hscript)
    hou_parm.setKeyframe(hou_keyframe)

    # Code for keyframe.
    hou_keyframe = hou.Keyframe()
    hou_keyframe.setTime(0)
    hou_keyframe.interpretAccelAsRatio(False)
    hou_keyframe.setExpression("$CPIXA", hou.exprLanguage.Hscript)
    hou_parm.setKeyframe(hou_keyframe)

    # Code for keyframe.
    hou_keyframe = hou.Keyframe()
    hou_keyframe.setTime(0)
    hou_keyframe.interpretAccelAsRatio(False)
    hou_keyframe.setExpression("$CPIXA", hou.exprLanguage.Hscript)
    hou_parm.setKeyframe(hou_keyframe)


    # Code for /img/waa/IN_image/linearize parm 
    if locals().get("hou_node") is None:
        hou_node = hou.node("/img/waa/IN_image")
    hou_parm = hou_node.parm("linearize")
    hou_parm.set(0)


    # Code for /img/waa/IN_image/depth parm 
    if locals().get("hou_node") is None:
        hou_node = hou.node("/img/waa/IN_image")
    hou_parm = hou_node.parm("depth")
    hou_parm.set("float16")


    # Code for /img/waa/IN_image/bwpoints parm tuple
    if locals().get("hou_node") is None:
        hou_node = hou.node("/img/waa/IN_image")
    hou_parm_tuple = hou_node.parmTuple("bwpoints")
    hou_parm_tuple.set((0, 1))


    # Code for /img/waa/IN_image/singleimage parm 
    if locals().get("hou_node") is None:
        hou_node = hou.node("/img/waa/IN_image")
    hou_parm = hou_node.parm("singleimage")
    hou_parm.set(1)


    hou_node.setColor(hou.Color([0.5, 0.7, 0.6]))
    hou_node.setExpressionLanguage(hou.exprLanguage.Hscript)

    hou_node.setUserData("___Version___", "18.0.416")
    if hasattr(hou_node, "syncNodeVersionIfNeeded"):
        hou_node.syncNodeVersionIfNeeded("18.0.416")
    # Update the parent node.
    hou_parent = hou_node


    # Restore the parent and current nodes.
    hou_parent = hou_parent.parent()
    hou_node = hou_node.parent()

    # Code for /img/waa/OUT_image
    hou_node = hou_parent.createNode("rop_comp", "OUT_image", run_init_scripts=False, load_contents=True, exact_type_name=True)
    hou_node.move(hou.Vector2(-5.57182, -3.45225))
    hou_node.bypass(False)
    hou_node.hide(False)
    hou_node.setLocked(False)
    hou_node.setSelected(False)

    # Code for /img/waa/OUT_image/trange parm 
    if locals().get("hou_node") is None:
        hou_node = hou.node("/img/waa/OUT_image")
    hou_parm = hou_node.parm("trange")
    hou_parm.set("on")


    # Code for /img/waa/OUT_image/f parm tuple
    if locals().get("hou_node") is None:
        hou_node = hou.node("/img/waa/OUT_image")
    hou_parm_tuple = hou_node.parmTuple("f")
    hou_parm_tuple.set((1, 1, 1))


    # Code for /img/waa/OUT_image/coppath parm 
    if locals().get("hou_node") is None:
        hou_node = hou.node("/img/waa/OUT_image")
    hou_parm = hou_node.parm("coppath")
    hou_parm.set("/img/waa/colorcorrect1")


    # Code for /img/waa/OUT_image/res parm tuple
    if locals().get("hou_node") is None:
        hou_node = hou.node("/img/waa/OUT_image")
    hou_parm_tuple = hou_node.parmTuple("res")
    hou_parm_tuple.set((1, 1))


    # Code for /img/waa/OUT_image/copoutput parm 
    if locals().get("hou_node") is None:
        hou_node = hou.node("/img/waa/OUT_image")
    hou_parm = hou_node.parm("copoutput")
    hou_parm.set("")


    # Code for /img/waa/OUT_image/scopeplanes parm 
    if locals().get("hou_node") is None:
        hou_node = hou.node("/img/waa/OUT_image")
    hou_parm = hou_node.parm("scopeplanes")
    hou_parm.set("*")


    hou_node.setExpressionLanguage(hou.exprLanguage.Hscript)

    if hasattr(hou_node, "syncNodeVersionIfNeeded"):
        hou_node.syncNodeVersionIfNeeded("18.0.416")
    # Update the parent node.
    hou_parent = hou_node


    # Restore the parent and current nodes.
    hou_parent = hou_parent.parent()
    hou_node = hou_node.parent()

    # Code for /img/waa/vopcop2gen1
    hou_node = hou_parent.createNode("vopcop2gen", "vopcop2gen1", run_init_scripts=False, load_contents=True, exact_type_name=True)
    hou_node.move(hou.Vector2(-7.4497, 4.25378))
    hou_node.bypass(False)
    hou_node.setDisplayFlag(False)
    hou_node.setCompressFlag(False)
    hou_node.hide(False)
    hou_node.setSelected(False)
    hou_node.setRenderFlag(False)
    hou_node.setTemplateFlag(False)

    hou_parm_template_group = hou.ParmTemplateGroup()
    # Code for parameter template
    hou_parm_template = hou.FolderParmTemplate("stdswitcher", "Compiler", folder_type=hou.folderType.Tabs, default_value=0, ends_tab_group=False)
    # Code for parameter template
    hou_parm_template2 = hou.StringParmTemplate("vop_compiler", "Compiler", 1, default_value=(["vcc -q $VOP_INCLUDEPATH -o $VOP_OBJECTFILE -e $VOP_ERRORFILE $VOP_SOURCEFILE"]), naming_scheme=hou.parmNamingScheme.Base1, string_type=hou.stringParmType.Regular, menu_items=([]), menu_labels=([]), icon_names=([]), item_generator_script="", item_generator_script_language=hou.scriptLanguage.Python, menu_type=hou.menuType.Normal)
    hou_parm_template.addParmTemplate(hou_parm_template2)
    # Code for parameter template
    hou_parm_template2 = hou.ButtonParmTemplate("vop_forcecompile", "Force Compile")
    hou_parm_template.addParmTemplate(hou_parm_template2)
    hou_parm_template_group.append(hou_parm_template)
    # Code for parameter template
    hou_parm_template = hou.FolderParmTemplate("stdswitcher_1", "Mask", folder_type=hou.folderType.Tabs, default_value=0, ends_tab_group=False)
    # Code for parameter template
    hou_parm_template2 = hou.FloatParmTemplate("effectamount", "Effect Amount", 1, default_value=([1]), min=0, max=1, min_is_strict=False, max_is_strict=False, look=hou.parmLook.Regular, naming_scheme=hou.parmNamingScheme.Base1)
    hou_parm_template.addParmTemplate(hou_parm_template2)
    # Code for parameter template
    hou_parm_template2 = hou.StringParmTemplate("maskplane", "Mask Plane", 1, default_value=(["A"]), naming_scheme=hou.parmNamingScheme.Base1, string_type=hou.stringParmType.Regular, menu_items=([]), menu_labels=([]), icon_names=([]), item_generator_script="", item_generator_script_language=hou.scriptLanguage.Python, menu_type=hou.menuType.Normal)
    hou_parm_template.addParmTemplate(hou_parm_template2)
    # Code for parameter template
    hou_parm_template2 = hou.ToggleParmTemplate("maskresize", "Resize Mask to Fit Image", default_value=False)
    hou_parm_template.addParmTemplate(hou_parm_template2)
    # Code for parameter template
    hou_parm_template2 = hou.ToggleParmTemplate("maskinvert", "Invert Mask", default_value=False)
    hou_parm_template.addParmTemplate(hou_parm_template2)
    hou_parm_template_group.append(hou_parm_template)
    # Code for parameter template
    hou_parm_template = hou.FolderParmTemplate("stdswitcher_2", "Image", folder_type=hou.folderType.Tabs, default_value=0, ends_tab_group=False)
    # Code for parameter template
    hou_parm_template2 = hou.ToggleParmTemplate("overridesize", "Override Global Size", default_value=False)
    hou_parm_template2.setJoinWithNext(True)
    hou_parm_template.addParmTemplate(hou_parm_template2)
    # Code for parameter template
    hou_parm_template2 = hou.IntParmTemplate("size", "Override Size", 2, default_value=([0, 0]), default_expression=(["$CXRES","$CYRES"]), default_expression_language=([hou.scriptLanguage.Hscript,hou.scriptLanguage.Hscript]), min=1, max=1000, min_is_strict=True, max_is_strict=False, naming_scheme=hou.parmNamingScheme.Base1, menu_items=([]), menu_labels=([]), icon_names=([]), item_generator_script="", item_generator_script_language=hou.scriptLanguage.Python, menu_type=hou.menuType.Normal, menu_use_token=False)
    hou_parm_template2.setJoinWithNext(True)
    hou_parm_template.addParmTemplate(hou_parm_template2)
    # Code for parameter template
    hou_parm_template2 = hou.MenuParmTemplate("sizemenu", "Size Menu", menu_items=([]), menu_labels=([]), default_value=0, icon_names=([]), item_generator_script="", item_generator_script_language=hou.scriptLanguage.Python, menu_type=hou.menuType.Mini, menu_use_token=False, is_button_strip=False, strip_uses_icons=False)
    hou_parm_template.addParmTemplate(hou_parm_template2)
    # Code for parameter template
    hou_parm_template2 = hou.ToggleParmTemplate("overrideaspect", "Override Pixel Aspect", default_value=False)
    hou_parm_template2.setJoinWithNext(True)
    hou_parm_template.addParmTemplate(hou_parm_template2)
    # Code for parameter template
    hou_parm_template2 = hou.FloatParmTemplate("aspect", "Pixel Aspect Ratio", 1, default_value=([0]), default_expression=(["$CPIXA"]), default_expression_language=([hou.scriptLanguage.Hscript]), min=0.0001, max=2, min_is_strict=True, max_is_strict=False, look=hou.parmLook.Regular, naming_scheme=hou.parmNamingScheme.Base1)
    hou_parm_template.addParmTemplate(hou_parm_template2)
    # Code for parameter template
    hou_parm_template2 = hou.MenuParmTemplate("planes", "Image Planes", menu_items=(["rgba","rgba3","rgb","a","a3","m","m3","z","l","b","p","n","v","terrain_height","none"]), menu_labels=(["C, A (C:rgb A)","C, A (C:rgb A:rgb)","C    (rgb)","A","A    (rgb)","M","M    (rgb)","Z","L","B    (uv)","P    (xyz)","N    (xyz)","V    (xyz)","Terrain: Height","None"]), default_value=0, icon_names=([]), item_generator_script="", item_generator_script_language=hou.scriptLanguage.Python, menu_type=hou.menuType.Normal, menu_use_token=False, is_button_strip=False, strip_uses_icons=False)
    hou_parm_template.addParmTemplate(hou_parm_template2)
    # Code for parameter template
    hou_parm_template2 = hou.MenuParmTemplate("addplanes", "Add Plane", menu_items=(["rgba","rgba3","rgb","a","a3","m","m3","z","l","b","p","n","v","terrain_height","none"]), menu_labels=(["C, A (C:rgb A)","C, A (C:rgb A:rgb)","C    (rgb)","A","A    (rgb)","M","M    (rgb)","Z","L","B    (uv)","P    (xyz)","N    (xyz)","V    (xyz)","Terrain: Height","None"]), default_value=5, icon_names=([]), item_generator_script="", item_generator_script_language=hou.scriptLanguage.Python, menu_type=hou.menuType.Normal, menu_use_token=False, is_button_strip=False, strip_uses_icons=False)
    hou_parm_template2.setJoinWithNext(True)
    hou_parm_template.addParmTemplate(hou_parm_template2)
    # Code for parameter template
    hou_parm_template2 = hou.MenuParmTemplate("addplaneop", "", menu_items=(["replace","rename","add","screen","subtract","multiply","min","max","avg"]), menu_labels=(["Replace","Rename","Add","Screen","Subtract","Multiply","Min","Max","Average"]), default_value=0, icon_names=([]), item_generator_script="", item_generator_script_language=hou.scriptLanguage.Python, menu_type=hou.menuType.Normal, menu_use_token=False, is_button_strip=False, strip_uses_icons=False)
    hou_parm_template2.hideLabel(True)
    hou_parm_template.addParmTemplate(hou_parm_template2)
    # Code for parameter template
    hou_parm_template2 = hou.StringParmTemplate("customplanes", "Custom Planes", 1, default_value=([""]), naming_scheme=hou.parmNamingScheme.Base1, string_type=hou.stringParmType.Regular, menu_items=([]), menu_labels=([]), icon_names=([]), item_generator_script="", item_generator_script_language=hou.scriptLanguage.Python, menu_type=hou.menuType.Normal)
    hou_parm_template.addParmTemplate(hou_parm_template2)
    # Code for parameter template
    hou_parm_template2 = hou.MenuParmTemplate("depth", "Raster Depth", menu_items=(["int8","int16","int32","float16","float32","default"]), menu_labels=(["8 Bit Integer","16 Bit Integer","32 Bit Integer","16 Bit Floating Point","32 Bit Floating Point","Default Depth"]), default_value=5, icon_names=([]), item_generator_script="", item_generator_script_language=hou.scriptLanguage.Python, menu_type=hou.menuType.Normal, menu_use_token=False, is_button_strip=False, strip_uses_icons=False)
    hou_parm_template2.setJoinWithNext(True)
    hou_parm_template.addParmTemplate(hou_parm_template2)
    # Code for parameter template
    hou_parm_template2 = hou.MenuParmTemplate("depthmenu", "Depth Menu", menu_items=([]), menu_labels=([]), default_value=0, icon_names=([]), item_generator_script="", item_generator_script_language=hou.scriptLanguage.Python, menu_type=hou.menuType.Mini, menu_use_token=False, is_button_strip=False, strip_uses_icons=False)
    hou_parm_template.addParmTemplate(hou_parm_template2)
    # Code for parameter template
    hou_parm_template2 = hou.IntParmTemplate("depthglobal", "Global Depth Setting", 1, default_value=([0]), default_expression=(["$CDEPTH"]), default_expression_language=([hou.scriptLanguage.Hscript]), min=0, max=10, min_is_strict=False, max_is_strict=False, naming_scheme=hou.parmNamingScheme.Base1, menu_items=([]), menu_labels=([]), icon_names=([]), item_generator_script="", item_generator_script_language=hou.scriptLanguage.Python, menu_type=hou.menuType.Normal, menu_use_token=False)
    hou_parm_template2.hide(True)
    hou_parm_template.addParmTemplate(hou_parm_template2)
    # Code for parameter template
    hou_parm_template2 = hou.ToggleParmTemplate("usebwpoints", "Use Custom Black/White Points", default_value=False)
    hou_parm_template2.setJoinWithNext(True)
    hou_parm_template.addParmTemplate(hou_parm_template2)
    # Code for parameter template
    hou_parm_template2 = hou.IntParmTemplate("bwpoints", "Black/White Points", 2, default_value=([0, 0]), default_expression=(["$CBP","$CWP"]), default_expression_language=([hou.scriptLanguage.Hscript,hou.scriptLanguage.Hscript]), min=0, max=10, min_is_strict=False, max_is_strict=False, naming_scheme=hou.parmNamingScheme.Base1, menu_items=([]), menu_labels=([]), icon_names=([]), item_generator_script="", item_generator_script_language=hou.scriptLanguage.Python, menu_type=hou.menuType.Normal, menu_use_token=False)
    hou_parm_template.addParmTemplate(hou_parm_template2)
    # Code for parameter template
    hou_parm_template2 = hou.MenuParmTemplate("interlace", "Interlacing", menu_items=(["none","inthalf","intblack","intdouble"]), menu_labels=(["None","Half Res Interlaced","Black Interlaced","Line Doubled"]), default_value=0, icon_names=([]), item_generator_script="", item_generator_script_language=hou.scriptLanguage.Python, menu_type=hou.menuType.Normal, menu_use_token=False, is_button_strip=False, strip_uses_icons=False)
    hou_parm_template2.setJoinWithNext(True)
    hou_parm_template.addParmTemplate(hou_parm_template2)
    # Code for parameter template
    hou_parm_template2 = hou.MenuParmTemplate("idominance", "", menu_items=(["odd","even","oddonly","evenonly"]), menu_labels=(["Odd First","Even First","Odd Only","Even Only"]), default_value=0, icon_names=([]), item_generator_script="", item_generator_script_language=hou.scriptLanguage.Python, menu_type=hou.menuType.Normal, menu_use_token=False, is_button_strip=False, strip_uses_icons=False)
    hou_parm_template2.hideLabel(True)
    hou_parm_template.addParmTemplate(hou_parm_template2)
    hou_parm_template_group.append(hou_parm_template)
    # Code for parameter template
    hou_parm_template = hou.FolderParmTemplate("stdswitcher_3", "Sequence", folder_type=hou.folderType.Tabs, default_value=0, ends_tab_group=False)
    # Code for parameter template
    hou_parm_template2 = hou.ToggleParmTemplate("overriderange", "Override Global Range", default_value=False)
    hou_parm_template.addParmTemplate(hou_parm_template2)
    # Code for parameter template
    hou_parm_template2 = hou.ToggleParmTemplate("singleimage", "Still Image", default_value=False)
    hou_parm_template.addParmTemplate(hou_parm_template2)
    # Code for parameter template
    hou_parm_template2 = hou.IntParmTemplate("start", "Start Frame", 1, default_value=([0]), default_expression=(["$FSTART"]), default_expression_language=([hou.scriptLanguage.Hscript]), min=0, max=240, min_is_strict=False, max_is_strict=False, naming_scheme=hou.parmNamingScheme.Base1, menu_items=([]), menu_labels=([]), icon_names=([]), item_generator_script="", item_generator_script_language=hou.scriptLanguage.Python, menu_type=hou.menuType.Normal, menu_use_token=False)
    hou_parm_template.addParmTemplate(hou_parm_template2)
    # Code for parameter template
    hou_parm_template2 = hou.IntParmTemplate("length", "Length", 1, default_value=([0]), default_expression=(["$NFRAMES"]), default_expression_language=([hou.scriptLanguage.Hscript]), min=1, max=240, min_is_strict=True, max_is_strict=False, naming_scheme=hou.parmNamingScheme.Base1, menu_items=([]), menu_labels=([]), icon_names=([]), item_generator_script="", item_generator_script_language=hou.scriptLanguage.Python, menu_type=hou.menuType.Normal, menu_use_token=False)
    hou_parm_template.addParmTemplate(hou_parm_template2)
    # Code for parameter template
    hou_parm_template2 = hou.MenuParmTemplate("preextend", "Pre Extend", menu_items=(["black","cycle","mirror","hold","holdn"]), menu_labels=(["Black Frames","Cycle","Mirror","Hold","Hold N Frames"]), default_value=0, icon_names=([]), item_generator_script="", item_generator_script_language=hou.scriptLanguage.Python, menu_type=hou.menuType.Normal, menu_use_token=False, is_button_strip=False, strip_uses_icons=False)
    hou_parm_template.addParmTemplate(hou_parm_template2)
    # Code for parameter template
    hou_parm_template2 = hou.IntParmTemplate("prehold", "Pre Hold", 1, default_value=([0]), min=0, max=240, min_is_strict=True, max_is_strict=False, naming_scheme=hou.parmNamingScheme.Base1, menu_items=([]), menu_labels=([]), icon_names=([]), item_generator_script="", item_generator_script_language=hou.scriptLanguage.Python, menu_type=hou.menuType.Normal, menu_use_token=False)
    hou_parm_template.addParmTemplate(hou_parm_template2)
    # Code for parameter template
    hou_parm_template2 = hou.MenuParmTemplate("postextend", "Post Extend", menu_items=(["black","cycle","mirror","hold","holdn"]), menu_labels=(["Black Frames","Cycle","Mirror","Hold","Hold N Frames"]), default_value=0, icon_names=([]), item_generator_script="", item_generator_script_language=hou.scriptLanguage.Python, menu_type=hou.menuType.Normal, menu_use_token=False, is_button_strip=False, strip_uses_icons=False)
    hou_parm_template.addParmTemplate(hou_parm_template2)
    # Code for parameter template
    hou_parm_template2 = hou.IntParmTemplate("posthold", "Post Hold", 1, default_value=([0]), min=0, max=240, min_is_strict=True, max_is_strict=False, naming_scheme=hou.parmNamingScheme.Base1, menu_items=([]), menu_labels=([]), icon_names=([]), item_generator_script="", item_generator_script_language=hou.scriptLanguage.Python, menu_type=hou.menuType.Normal, menu_use_token=False)
    hou_parm_template.addParmTemplate(hou_parm_template2)
    hou_parm_template_group.append(hou_parm_template)
    hou_node.setParmTemplateGroup(hou_parm_template_group)
    # Code for /img/waa/vopcop2gen1/stdswitcher1 parm 
    if locals().get("hou_node") is None:
        hou_node = hou.node("/img/waa/vopcop2gen1")
    hou_parm = hou_node.parm("stdswitcher1")
    hou_parm.set(2)


    # Code for /img/waa/vopcop2gen1/size parm tuple
    if locals().get("hou_node") is None:
        hou_node = hou.node("/img/waa/vopcop2gen1")
    hou_parm_tuple = hou_node.parmTuple("size")

    # Code for first keyframe.
    # Code for keyframe.
    hou_keyframe = hou.Keyframe()
    hou_keyframe.setTime(0)
    hou_keyframe.setExpression("$CXRES", hou.exprLanguage.Hscript)
    hou_parm_tuple[0].setKeyframe(hou_keyframe)

    # Code for last keyframe.
    # Code for keyframe.
    hou_keyframe = hou.Keyframe()
    hou_keyframe.setTime(0)
    hou_keyframe.setExpression("$CXRES", hou.exprLanguage.Hscript)
    hou_parm_tuple[0].setKeyframe(hou_keyframe)

    # Code for keyframe.
    hou_keyframe = hou.Keyframe()
    hou_keyframe.setTime(0)
    hou_keyframe.setExpression("$CXRES", hou.exprLanguage.Hscript)
    hou_parm_tuple[0].setKeyframe(hou_keyframe)

    # Code for first keyframe.
    # Code for keyframe.
    hou_keyframe = hou.Keyframe()
    hou_keyframe.setTime(0)
    hou_keyframe.setExpression("$CYRES", hou.exprLanguage.Hscript)
    hou_parm_tuple[1].setKeyframe(hou_keyframe)

    # Code for last keyframe.
    # Code for keyframe.
    hou_keyframe = hou.Keyframe()
    hou_keyframe.setTime(0)
    hou_keyframe.setExpression("$CYRES", hou.exprLanguage.Hscript)
    hou_parm_tuple[1].setKeyframe(hou_keyframe)

    # Code for keyframe.
    hou_keyframe = hou.Keyframe()
    hou_keyframe.setTime(0)
    hou_keyframe.setExpression("$CYRES", hou.exprLanguage.Hscript)
    hou_parm_tuple[1].setKeyframe(hou_keyframe)


    # Code for /img/waa/vopcop2gen1/aspect parm 
    if locals().get("hou_node") is None:
        hou_node = hou.node("/img/waa/vopcop2gen1")
    hou_parm = hou_node.parm("aspect")

    # Code for first keyframe.
    # Code for keyframe.
    hou_keyframe = hou.Keyframe()
    hou_keyframe.setTime(0)
    hou_keyframe.setExpression("$CPIXA", hou.exprLanguage.Hscript)
    hou_parm.setKeyframe(hou_keyframe)

    # Code for last keyframe.
    # Code for keyframe.
    hou_keyframe = hou.Keyframe()
    hou_keyframe.setTime(0)
    hou_keyframe.setExpression("$CPIXA", hou.exprLanguage.Hscript)
    hou_parm.setKeyframe(hou_keyframe)

    # Code for keyframe.
    hou_keyframe = hou.Keyframe()
    hou_keyframe.setTime(0)
    hou_keyframe.setExpression("$CPIXA", hou.exprLanguage.Hscript)
    hou_parm.setKeyframe(hou_keyframe)

    # Code for keyframe.
    hou_keyframe = hou.Keyframe()
    hou_keyframe.setTime(0)
    hou_keyframe.setExpression("$CPIXA", hou.exprLanguage.Hscript)
    hou_parm.setKeyframe(hou_keyframe)


    # Code for /img/waa/vopcop2gen1/depth parm 
    if locals().get("hou_node") is None:
        hou_node = hou.node("/img/waa/vopcop2gen1")
    hou_parm = hou_node.parm("depth")
    hou_parm.set("float16")


    # Code for /img/waa/vopcop2gen1/depthglobal parm 
    if locals().get("hou_node") is None:
        hou_node = hou.node("/img/waa/vopcop2gen1")
    hou_parm = hou_node.parm("depthglobal")
    hou_parm.set(4)


    # Code for /img/waa/vopcop2gen1/bwpoints parm tuple
    if locals().get("hou_node") is None:
        hou_node = hou.node("/img/waa/vopcop2gen1")
    hou_parm_tuple = hou_node.parmTuple("bwpoints")
    hou_parm_tuple.set((0, 1))


    # Code for /img/waa/vopcop2gen1/start parm 
    if locals().get("hou_node") is None:
        hou_node = hou.node("/img/waa/vopcop2gen1")
    hou_parm = hou_node.parm("start")

    # Code for first keyframe.
    # Code for keyframe.
    hou_keyframe = hou.Keyframe()
    hou_keyframe.setTime(0)
    hou_keyframe.setExpression("$FSTART", hou.exprLanguage.Hscript)
    hou_parm.setKeyframe(hou_keyframe)

    # Code for last keyframe.
    # Code for keyframe.
    hou_keyframe = hou.Keyframe()
    hou_keyframe.setTime(0)
    hou_keyframe.setExpression("$FSTART", hou.exprLanguage.Hscript)
    hou_parm.setKeyframe(hou_keyframe)

    # Code for keyframe.
    hou_keyframe = hou.Keyframe()
    hou_keyframe.setTime(0)
    hou_keyframe.setExpression("$FSTART", hou.exprLanguage.Hscript)
    hou_parm.setKeyframe(hou_keyframe)

    # Code for keyframe.
    hou_keyframe = hou.Keyframe()
    hou_keyframe.setTime(0)
    hou_keyframe.setExpression("$FSTART", hou.exprLanguage.Hscript)
    hou_parm.setKeyframe(hou_keyframe)


    # Code for /img/waa/vopcop2gen1/length parm 
    if locals().get("hou_node") is None:
        hou_node = hou.node("/img/waa/vopcop2gen1")
    hou_parm = hou_node.parm("length")

    # Code for first keyframe.
    # Code for keyframe.
    hou_keyframe = hou.Keyframe()
    hou_keyframe.setTime(0)
    hou_keyframe.setExpression("$NFRAMES", hou.exprLanguage.Hscript)
    hou_parm.setKeyframe(hou_keyframe)

    # Code for last keyframe.
    # Code for keyframe.
    hou_keyframe = hou.Keyframe()
    hou_keyframe.setTime(0)
    hou_keyframe.setExpression("$NFRAMES", hou.exprLanguage.Hscript)
    hou_parm.setKeyframe(hou_keyframe)

    # Code for keyframe.
    hou_keyframe = hou.Keyframe()
    hou_keyframe.setTime(0)
    hou_keyframe.setExpression("$NFRAMES", hou.exprLanguage.Hscript)
    hou_parm.setKeyframe(hou_keyframe)

    # Code for keyframe.
    hou_keyframe = hou.Keyframe()
    hou_keyframe.setTime(0)
    hou_keyframe.setExpression("$NFRAMES", hou.exprLanguage.Hscript)
    hou_parm.setKeyframe(hou_keyframe)


    hou_node.setColor(hou.Color([0.5, 0.7, 0.6]))
    hou_node.setExpressionLanguage(hou.exprLanguage.Hscript)

    if hasattr(hou_node, "syncNodeVersionIfNeeded"):
        hou_node.syncNodeVersionIfNeeded("18.0.416")
    # Update the parent node.
    hou_parent = hou_node

    # Code for /img/waa/vopcop2gen1/global1
    hou_node = hou_parent.createNode("global", "global1", run_init_scripts=False, load_contents=True, exact_type_name=True)
    hou_node.move(hou.Vector2(1, 1))
    hou_node.setDebugFlag(False)
    hou_node.setDetailLowFlag(False)
    hou_node.setDetailMediumFlag(False)
    hou_node.setDetailHighFlag(True)
    hou_node.bypass(False)
    hou_node.setCompressFlag(True)
    hou_node.hide(False)
    hou_node.setSelected(False)

    # Code for /img/waa/vopcop2gen1/global1/contexttype parm 
    if locals().get("hou_node") is None:
        hou_node = hou.node("/img/waa/vopcop2gen1/global1")
    hou_parm = hou_node.parm("contexttype")
    hou_parm.set("cop2")


    hou_node.setExpressionLanguage(hou.exprLanguage.Hscript)

    if hasattr(hou_node, "syncNodeVersionIfNeeded"):
        hou_node.syncNodeVersionIfNeeded("18.0.416")
    # Update the parent node.
    hou_parent = hou_node


    # Restore the parent and current nodes.
    hou_parent = hou_parent.parent()
    hou_node = hou_node.parent()

    # Code for /img/waa/vopcop2gen1/output1
    hou_node = hou_parent.createNode("output", "output1", run_init_scripts=False, load_contents=True, exact_type_name=True)
    hou_node.move(hou.Vector2(5, 1))
    hou_node.setDebugFlag(False)
    hou_node.setDetailLowFlag(False)
    hou_node.setDetailMediumFlag(False)
    hou_node.setDetailHighFlag(True)
    hou_node.bypass(False)
    hou_node.setCompressFlag(True)
    hou_node.hide(False)
    hou_node.setSelected(False)

    # Code for /img/waa/vopcop2gen1/output1/contexttype parm 
    if locals().get("hou_node") is None:
        hou_node = hou.node("/img/waa/vopcop2gen1/output1")
    hou_parm = hou_node.parm("contexttype")
    hou_parm.set("cop2")


    # Code for /img/waa/vopcop2gen1/output1/outputcodelast parm 
    if locals().get("hou_node") is None:
        hou_node = hou.node("/img/waa/vopcop2gen1/output1")
    hou_parm = hou_node.parm("outputcodelast")
    hou_parm.set(1)


    hou_node.setExpressionLanguage(hou.exprLanguage.Hscript)

    if hasattr(hou_node, "syncNodeVersionIfNeeded"):
        hou_node.syncNodeVersionIfNeeded("18.0.416")
    # Update the parent node.
    hou_parent = hou_node


    # Restore the parent and current nodes.
    hou_parent = hou_parent.parent()
    hou_node = hou_node.parent()


    # Restore the parent and current nodes.
    hou_parent = hou_parent.parent()
    hou_node = hou_node.parent()

    # Code for /img/waa/add1
    hou_node = hou_parent.createNode("add", "add1", run_init_scripts=False, load_contents=True, exact_type_name=True)
    hou_node.move(hou.Vector2(-5.57182, 1.72575))
    hou_node.bypass(False)
    hou_node.setDisplayFlag(False)
    hou_node.setCompressFlag(False)
    hou_node.hide(False)
    hou_node.setSelected(False)
    hou_node.setRenderFlag(False)
    hou_node.setTemplateFlag(False)

    # Code for /img/waa/add1/stdswitcher1 parm 
    if locals().get("hou_node") is None:
        hou_node = hou.node("/img/waa/add1")
    hou_parm = hou_node.parm("stdswitcher1")
    hou_parm.set(1)


    # Code for /img/waa/add1/depthmatch parm 
    if locals().get("hou_node") is None:
        hou_node = hou.node("/img/waa/add1")
    hou_parm = hou_node.parm("depthmatch")
    hou_parm.set("usefirst")


    hou_node.setExpressionLanguage(hou.exprLanguage.Hscript)

    if hasattr(hou_node, "syncNodeVersionIfNeeded"):
        hou_node.syncNodeVersionIfNeeded("18.0.416")
    # Update the parent node.
    hou_parent = hou_node


    # Restore the parent and current nodes.
    hou_parent = hou_parent.parent()
    hou_node = hou_node.parent()

    # Code to establish connections for /img/waa/colorspace_transform
    hou_node = hou_parent.node("colorspace_transform")
    if hou_parent.node("add1") is not None:
        hou_node.setInput(0, hou_parent.node("add1"), 0)
    # Code to establish connections for /img/waa/OUT_image
    hou_node = hou_parent.node("OUT_image")
    if hou_parent.node("colorspace_transform") is not None:
        hou_node.setInput(0, hou_parent.node("colorspace_transform"), 0)
    # Code to establish connections for /img/waa/add1
    hou_node = hou_parent.node("add1")
    if hou_parent.node("vopcop2gen1") is not None:
        hou_node.setInput(0, hou_parent.node("vopcop2gen1"), 0)
    if hou_parent.node("IN_image") is not None:
        hou_node.setInput(1, hou_parent.node("IN_image"), 0)

    # Restore the parent and current nodes.
    hou_parent = hou_parent.parent()
    hou_node = hou_node.parent()




    return out