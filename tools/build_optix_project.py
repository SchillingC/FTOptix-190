#!/usr/bin/env python3
"""FactoryTalk View ME display XML (+ tag CSV) -> FactoryTalk Optix project (YAML).

Usage: build_optix_project.py --template <clone of FactoryTalk-Optix/Optix_Sample_AzureIoTOperations>
Reads the display exports and analysis/HMI_flat_tags.csv from the repository root and
writes OptixProject/HMI190/.
"""
import argparse, csv, glob, json, os, re, shutil, sys, uuid
import xml.etree.ElementTree as ET

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PROJ = "HMI190"
NS_CB = 9      # FTOptix.CoreBase in the template's dependency table
DRV = f"/Objects/{PROJ}/CommDrivers/RAEtherNet_IPDriver1/RAEtherNet_IPStation1"
TAGS = f"{DRV}/Tags/Controller Tags"
MODEL = f"/Objects/{PROJ}/Model"
LOADER = f"/Objects/{PROJ}/UI/MainWindow/PanelLoader1"
SCREENS = f"/Objects/{PROJ}/UI/Screens"
WARN = []

# ---------------------------------------------------------------- YAML emitter
def val(v):
    if isinstance(v, bool): return "true" if v else "false"
    if isinstance(v, float): return repr(v)
    if isinstance(v, int): return str(v)
    if isinstance(v, (dict, list)): return json.dumps(v, ensure_ascii=False, separators=(",", ":"))
    return json.dumps(v, ensure_ascii=False)

KEYS = ["Name", "Supertype", "Type", "ReferenceType", "DataType", "ModellingRule", "AccessLevel", "ValueRank", "ArrayDimensions", "Description", "Value"]

def emit(n, ind, out):
    pre = " " * ind
    if n.get("Class") == "Reference":
        out += [f"{pre}- Class: Reference", f"{pre}  Target: {n['Target']}", f"{pre}  Direction: Forward"]
        return
    first = True
    for k in KEYS:
        if k in n:
            v = n[k]
            if k == "Name" and re.search(r"[:\s#]", v): v = f"'{v}'" if "'" not in v else json.dumps(v)
            elif k in ("Value", "Description"): v = val(v)
            elif k == "ArrayDimensions": v = val(v)
            out.append(f"{pre}{'- ' if first else '  '}{k}: {v}")
            first = False
    if n.get("Children"):
        out.append(f"{pre}  Children:")
        for c in n["Children"]: emit(c, ind + 2, out)

def dump(root_node, path, header_only=False):
    out = []
    keys = {k: root_node[k] for k in root_node if k != "Children"}
    for k in KEYS:
        if k in keys:
            v = keys[k]
            if k == "Name" and re.search(r"[:\s#]", v): v = f"'{v}'"
            out.append(f"{k}: {v}")
    if root_node.get("Children"):
        out.append("Children:")
        for c in root_node["Children"]: emit(c, 0, out)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    open(path, "w", encoding="utf-8", newline="\n").write("\n".join(out) + "\n")

# ---------------------------------------------------------------- node helpers
def N(name, typ, children=None, **kw):
    d = {"Name": name, "Type": typ}
    d.update(kw)
    if children: d["Children"] = [c for c in children if c]
    return d

def P(name, dt, value=None, kind="BaseVariableType", children=None, optional=True, **kw):
    d = {"Name": name, "Type": kind, "DataType": dt}
    if optional: d["ModellingRule"] = "Optional"
    d.update(kw)
    if value is not None: d["Value"] = value
    if children: d["Children"] = [c for c in children if c]
    return d

def DV(name, dt, value=None, children=None, **kw):
    return P(name, dt, value, "BaseDataVariableType", children, **kw)

def link(path, rw=False):
    c = [P("Mode", "DynamicLinkMode", 2)] if rw else None
    return N("DynamicLink", "DynamicLink", c, DataType="NodePath", Value=path)

def expr_prop(name, dt, expression, sources, default=None, **kw):
    ev = N("ExpressionEvaluator1", "ExpressionEvaluator", [
        DV("Expression", "String", expression, ReferenceType="HasParameter"),
        *[{"Name": f"ns={NS_CB};Source{i}", "Type": "BaseDataVariableType", "DataType": "BaseDataType",
           "ReferenceType": "HasSource", "Children": [link(s)]} for i, s in enumerate(sources)]])
    return DV(name, dt, default, [ev], **kw)

def link_prop(name, dt, path, rw=False, default=None, **kw):
    return DV(name, dt, default, [link(path, rw)], **kw)

# ---------------------------------------------------------------- colours / fonts
NAMED = {"black": "#000000", "white": "#ffffff", "silver": "#c0c0c0", "gray": "#808080", "grey": "#808080",
         "maroon": "#800000", "red": "#ff0000", "purple": "#800080", "fuchsia": "#ff00ff", "magenta": "#ff00ff",
         "green": "#008000", "lime": "#00ff00", "olive": "#808000", "yellow": "#ffff00", "navy": "#000080",
         "blue": "#0000ff", "teal": "#008080", "aqua": "#00ffff", "cyan": "#00ffff"}

def col(c, default="#ffffff"):
    if not c: return default
    c = c.strip()
    if c.startswith("#"): return c.lower() if len(c) == 7 else default
    return NAMED.get(c.lower(), default)

def fsize(e, default=10):
    return float(round(float(e.get("fontSize") or default) * 1.33))

H_ALIGN = {"Left": 0, "Center": 1, "Right": 2}
def text_align(a):
    a = a or "middleCenter"
    v = 1 if a.startswith("middle") and False else 0
    vert = 1 if a.startswith("middle") else (2 if a.startswith("bottom") else 0)
    horiz = 2 if a.endswith("Right") else (0 if a.endswith("Left") else 1)
    return horiz, vert

def sanitize(s):
    s = (s.replace("ä", "ae").replace("ö", "oe").replace("ü", "ue").replace("Ä", "Ae").replace("Ö", "Oe")
         .replace("Ü", "Ue").replace("ß", "ss"))
    return re.sub(r"[^A-Za-z0-9_]", "_", s)

# ---------------------------------------------------------------- tag / expression handling
LOCAL_VARS = {"Helligkeit": "Int32", "SM_LongDancerOff": "Boolean", "SM_ShortDancerOff": "Boolean",
              "SM_VacuumSupplyOff": "Boolean", "UserHasCode_A": "Boolean", "UserHasCode_B": "Boolean",
              "UserHasCode_C": "Boolean", "CurrentUserName": "String"}
STATION_VARS = {"Mode": "Mode", "ProcessorName": "ControllerName", "IsPresent": "Present", "Revision": "MajorRev",
                "DPVersion": "ProductCode"}
FAULTED = [f"{DRV}/StationStatusVariables/RecoverableMajorFaults", f"{DRV}/StationStatusVariables/UnrecoverableMajorFaults"]

def tagpath(t):  # HMI.General.Reset.On -> .../HMI/General/Reset/On
    return f"{TAGS}/{t.replace('.', '/')}"

def translate(expr, true_state="visible"):
    """FTView expression -> (Optix expression, [source paths]) or None."""
    e = " ".join(expr.split())
    srcs = []
    def src(path):
        if path not in srcs: srcs.append(path)
        return "{%d}" % srcs.index(path)
    e = re.sub(r"(?i)^IF\s+(.*)\s+THEN\s+1\s+ELSE\s+0$", r"\1", e)
    e = re.sub(r'\{\[PLC1\]@Status\}\s*==\s*"Faulted"', lambda m: f"({src(FAULTED[0])} || {src(FAULTED[1])})", e)
    e = re.sub(r"\{\[PLC1\]@(\w+)\}", lambda m: src(f"{DRV}/StationStatusVariables/{STATION_VARS.get(m.group(1), m.group(1))}"), e)
    e = re.sub(r"\{\[PLC1\](HMI\.[\w.]+)\}", lambda m: src(tagpath(m.group(1))), e)
    e = re.sub(r"CurrentUserHasCode\(\s*(\w)\s*\)", lambda m: src(f"{MODEL}/UserHasCode_{m.group(1)}"), e)
    e = re.sub(r'CurrentLanguage\(\s*\)\s*=\s*"([\w-]+)"', lambda m: f'{src("{Session}/ActualLocaleId")} == "{m.group(1)}"', e)
    e = re.sub(r"\{(SM_\w+)\}", lambda m: src(f"{MODEL}/{m.group(1)}"), e)
    e = re.sub(r"(?i)\bAND\b", "&&", e)
    e = re.sub(r"(?i)\bOR\b", "||", e)
    if re.search(r"[A-Za-z_]{3,}\s*\(", e.replace("{", "")) and "&&" not in e and "||" not in e and "==" not in e:
        return None
    if true_state == "invisible": e = f"!({e})"
    return e, srcs

# ---------------------------------------------------------------- screen builders
class Ctx:
    def __init__(self, screen):
        self.screen = screen
        self.n = 0
        self.images = set()
        self.used_local = set()
    def uid(self, base):
        self.n += 1
        return f"{sanitize(base) or 'Obj'}_{self.n}"

def geo(e, ox, oy):
    return [P("HorizontalAlignment", "HorizontalAlignment", 0), P("VerticalAlignment", "VerticalAlignment", 0),
            P("LeftMargin", "Size", float(e.get("left", 0)) - ox), P("TopMargin", "Size", float(e.get("top", 0)) - oy),
            P("Width", "Size", float(e.get("width", 0))), P("Height", "Size", float(e.get("height", 0)))]

def visibility(e):
    props = []
    anims = e.find("animations")
    if anims is None: return props
    for a in anims.findall("animateVisibility"):
        t = translate(a.get("expression", ""), a.get("expressionTrueState", "visible"))
        if not t:
            WARN.append(f"unsupported visibility expression: {a.get('expression')}")
            continue
        ex, srcs = t
        if ex == "{0}" and len(srcs) == 1 and "UserHasCode" not in srcs[0]:
            props.append(link_prop("Visible", "Boolean", srcs[0], default=True))
        else:
            props.append(expr_prop("Visible", "Boolean", ex, srcs, True))
    if anims.find("animateColor") is not None:
        WARN.append(f"{e.get('name')}: animateColor not converted")
    return props

def fill_props(e, transparent_default=False):
    solid = e.get("backStyle", "solid") == "solid" and not transparent_default
    border = e.get("borderStyle", "none")
    return [DV("FillColor", "Color", col(e.get("backColor")) if solid else "#00ffffff", optional=True),
            DV("BorderColor", "Color", col(e.get("borderColor"), "#808080"), optional=True),
            P("BorderThickness", "Size", 0.0 if border == "none" else float(min(int(e.get("borderWidth", 2) or 2), 2)))]

def label(name, text, e_or_c, w, h, fore=None, link_path=None, extra_expr=None):
    c = e_or_c
    ha, va = text_align(c.get("alignment"))
    kids = [P("HorizontalAlignment", "HorizontalAlignment", 0), P("VerticalAlignment", "VerticalAlignment", 0),
            P("LeftMargin", "Size", 0.0), P("TopMargin", "Size", 0.0), P("Width", "Size", float(w)), P("Height", "Size", float(h)),
            P("TextHorizontalAlignment", "TextHorizontalAlignment", ha), P("TextVerticalAlignment", "TextVerticalAlignment", va),
            DV("TextColor", "Color", col(fore or c.get("foreColor") or c.get("color"), "#000000")),
            P("FontSize", "Size", fsize(c)),
            P("FontWeight", "FontWeightEnum", 700 if c.get("bold") == "true" else 400),
            P("FontItalic", "Boolean", c.get("italic") == "true"),
            P("WordWrap", "Boolean", c.get("wordWrap", "true") == "true")]
    if extra_expr:
        kids.append(extra_expr)
    elif link_path:
        kids.append(link_prop("Text", "LocalizedText", link_path))
    else:
        kids.append(DV("Text", "LocalizedText", {"LocaleId": "de-DE", "Text": text}))
    return N(name, "Label", kids)

def image_node(name, img, w, h, ctx, left=0.0, top=0.0, color=None):
    if not img: return None
    ctx.images.add(img)
    kids = [P("HorizontalAlignment", "HorizontalAlignment", 0), P("VerticalAlignment", "VerticalAlignment", 0),
            P("LeftMargin", "Size", left), P("TopMargin", "Size", top), P("Width", "Size", float(w)), P("Height", "Size", float(h)),
            DV("Path", "ResourceUri", f"ns=18;%PROJECTDIR%/Images/{sanitize(img)}.png", optional=False),
            P("FillMode", "ImageFillModeEnum", 1)]
    return N(name, "Image", kids)

def nav_event(target):
    return N("MouseClickEventHandler1", "EventHandler", [
        N("ListenEventType", "PropertyType", DataType="NodeId", Value="/Types/EventTypes/BaseEventType/MouseEvent/MouseClickEvent"),
        N("MethodsToCall", "BaseObjectType", [N("MethodContainer1", "BaseObjectType", [
            N("ObjectPointer", "NodePointer", [link(f"{LOADER}@NodeId"),
               N("Kind", "PropertyType", DataType="NodeId", Value="/Types/ObjectTypes/BaseObjectType")], DataType="NodeId"),
            DV("Method", "String", "ChangePanel", optional=False),
            N("InputArguments", "BaseObjectType", [
                DV("NewPanel", "NodeId", f"{SCREENS}/{target}", optional=False),
                DV("AliasNode", "NodeId", optional=False, ValueRank="ScalarOrOneDimension")])])]),
        N("EventArguments", "MouseClickEvent", [
            N("EventId", "PropertyType", DataType="ByteString"), N("EventType", "PropertyType", DataType="NodeId"),
            N("SourceNode", "PropertyType", DataType="NodeId"), N("SourceName", "PropertyType", DataType="String"),
            N("Time", "PropertyType", DataType="UtcTime"), N("ReceiveTime", "PropertyType", DataType="UtcTime"),
            N("Message", "PropertyType", DataType="LocalizedText"), N("Severity", "PropertyType", DataType="UInt16")])])

def set_event(var_path, vtype, value, event="MouseClickEvent", name="MouseClickEventHandler1"):
    return N(name, "EventHandler", [
        N("ListenEventType", "PropertyType", DataType="NodeId", Value=f"/Types/EventTypes/BaseEventType/MouseEvent/{event}"),
        N("MethodsToCall", "BaseObjectType", [N("MethodContainer1", "BaseObjectType", [
            N(f"ns={NS_CB};ObjectPointer", "NodePointer", [N("Kind", "PropertyType", DataType="NodeId", Value="/Types/ObjectTypes/BaseObjectType")],
              DataType="NodeId", Value="/Objects/Commands/VariableCommands"),
            DV(f"ns={NS_CB};Method", "String", "Set", optional=False),
            N("InputArguments", "BaseObjectType", [
                DV("VariableToModify", "VariablePointer", children=[link(f"{var_path}@NodeId", True)], optional=False),
                DV("Value", vtype, value, optional=False),
                DV("ArrayIndex", "UInt32", optional=False, ValueRank="ScalarOrOneDimension")])])]),
        N("EventArguments", event, [
            N("EventId", "PropertyType", DataType="ByteString"), N("EventType", "PropertyType", DataType="NodeId"),
            N("SourceNode", "PropertyType", DataType="NodeId"), N("SourceName", "PropertyType", DataType="String"),
            N("Time", "PropertyType", DataType="UtcTime"), N("ReceiveTime", "PropertyType", DataType="UtcTime"),
            N("Message", "PropertyType", DataType="LocalizedText"), N("Severity", "PropertyType", DataType="UInt16")])])

def conn(e, name):
    cs = e.find("connections")
    if cs is None: return None
    for c in cs.findall("connection"):
        if c.get("name") == name: return c.get("expression")
    return None

def tag_of(expr):
    """single-tag expression -> (path, divisor) or None"""
    if not expr: return None
    m = re.fullmatch(r"\s*\{\[PLC1\](HMI\.[\w.]+)\}\s*(?:/\s*(\d+))?\s*", expr)
    if m: return tagpath(m.group(1)), (int(m.group(2)) if m.group(2) else None)
    m = re.fullmatch(r"\s*\{?(Helligkeit|SM_\w+)\}?\s*", expr)
    if m:
        LOCALS_USED.add(m.group(1))
        return f"{MODEL}/{m.group(1)}", None
    return None
LOCALS_USED = set()

def state_caption(st):
    c = st.find("caption")
    return (c.get("caption") if c is not None else "") or ""

def build(e, ox, oy, ctx, ind=0):
    """returns list of nodes for element e (positions relative to (ox,oy))"""
    t = e.tag
    name = ctx.uid(e.get("name", t))
    w, h = float(e.get("width", 0) or 0), float(e.get("height", 0) or 0)
    vis = visibility(e)

    if t == "group":
        kids = [c for c in e if c.tag not in ("animations", "connections")]
        boxes = [(float(c.get("left", 0)), float(c.get("top", 0)), float(c.get("left", 0)) + float(c.get("width", 0)),
                  float(c.get("top", 0)) + float(c.get("height", 0))) for c in grp_leaves(e)]
        if not boxes: return []
        l, tp = min(b[0] for b in boxes), min(b[1] for b in boxes)
        r, bt = max(b[2] for b in boxes), max(b[3] for b in boxes)
        inner = []
        for c in kids: inner += build(c, l, tp, ctx, ind + 1)
        return [N(name, "Panel", [P("HorizontalAlignment", "HorizontalAlignment", 0), P("VerticalAlignment", "VerticalAlignment", 0),
                                  P("LeftMargin", "Size", l - ox), P("TopMargin", "Size", tp - oy), P("Width", "Size", r - l),
                                  P("Height", "Size", bt - tp)] + vis + inner)]

    if t in ("rectangle", "panel", "line"):
        return [N(name, "Rectangle", geo(e, ox, oy) + fill_props(e) + vis)]

    if t == "text":
        return [N(name, "Rectangle", geo(e, ox, oy) + fill_props(e) + vis + [label("Text", e.get("caption", ""), e, w, h)])]

    if t == "image":
        return [image_node(name, e.get("imageName"), w, h, ctx, float(e.get("left", 0)) - ox, float(e.get("top", 0)) - oy)]

    if t == "timeAndDateDisplay":
        return [N(name, "Rectangle", geo(e, ox, oy) + fill_props(e) + vis + [
            N("Clock", "Label", [P("HorizontalAlignment", "HorizontalAlignment", 0), P("VerticalAlignment", "VerticalAlignment", 0),
                                 P("Width", "Size", w), P("Height", "Size", h), P("TextHorizontalAlignment", "TextHorizontalAlignment", 2),
                                 P("TextVerticalAlignment", "TextVerticalAlignment", 1), DV("TextColor", "Color", col(e.get("foreColor"))),
                                 P("FontSize", "Size", fsize(e)),
                                 link_prop("Text", "LocalizedText", "{Session}/CurrentTime")])])]

    if t in ("stringDisplay", "numericDisplay"):
        ex = conn(e, "Value")
        tg = tag_of(ex)
        body = []
        if tg and tg[1]:
            body = [label("Text", "", e, w, h, extra_expr=expr_prop("Text", "LocalizedText", "{0}/%d" % tg[1], [tg[0]]))]
        elif tg:
            body = [label("Text", "", e, w, h, link_path=tg[0])]
        elif ex and re.match(r"(?i)\s*if\b", ex):
            pairs = re.findall(r'\{\[PLC1\](HMI\.[\w.]+)\}\s*==\s*(\d+)\s*then\s*"([^"]*)"', ex, re.I)
            elsepart = re.findall(r'else\s*"([^"]*)"\s*$', " ".join(ex.split()), re.I)
            if pairs:
                p = tagpath(pairs[0][0])
                for v, txt in [(a, b) for _, a, b in pairs]:
                    lab = label(f"Text_{v}", txt, e, w, h)
                    lab["Children"].append(expr_prop("Visible", "Boolean", "{0} == %s" % v, [p], True))
                    body.append(lab)
                lab = label("Text_else", elsepart[0] if elsepart else "", e, w, h)
                lab["Children"].append(expr_prop("Visible", "Boolean", " && ".join("{0} != %s" % v for _, v, _ in pairs), [p], True))
                body.append(lab)
        elif ex:
            t2 = translate(ex)
            if t2 and len(t2[1]) == 1 and t2[0] == "{0}":
                body = [label("Text", "", e, w, h, link_path=t2[1][0])]
            elif ex.strip().lower() in ("system\\user",):
                body = [label("Text", "", e, w, h, link_path=f"{MODEL}/CurrentUserName")]
                LOCALS_USED.add("CurrentUserName")
            else:
                WARN.append(f"{ctx.screen}/{e.get('name')}: expression not converted: {ex[:60]}")
                body = [label("Text", "", e, w, h)]
        return [N(name, "Rectangle", geo(e, ox, oy) + fill_props(e) + vis + body)]

    if t in ("gotoButton", "returnToButton", "momentaryButton", "latchedButton", "rampButton", "languageSwitchButton",
             "loginButton", "logoutButton", "shutdownButton", "moveUpKey", "moveDownKey", "moveLeftKey", "moveRightKey",
             "acknowledgeAlarmButton", "silenceAlarmsButton", "clearAlarmBannerButton", "closeButton",
             "diagnosticsClearButton", "diagnosticsClearAllButton", "informationAckButton"):
        cap = e.find("caption")
        im = e.find("imageSettings")
        text = (cap.get("caption") if cap is not None else "") or ""
        img = im.get("imageName") if im is not None else ""
        kids = geo(e, ox, oy) + vis
        kids += [DV("BackgroundColor", "Color", col(e.get("backColor"), "#c0c0c0")), P("FontSize", "Size", fsize(cap if cap is not None else e, 10)),
                 DV("TextColor", "Color", col((cap.get("color") if cap is not None else None), "#000000"))]
        kids.append(DV("Text", "LocalizedText", {"LocaleId": "de-DE", "Text": text}))
        if img:
            ctx.images.add(img)
            kids += [DV("ImagePath", "ResourceUri", f"ns=18;%PROJECTDIR%/Images/{sanitize(img)}.png", optional=False),
                     P("ImageWidth", "Size", w), P("ImageHeight", "Size", h)]
        typ = "Button"
        if t == "gotoButton":
            target = e.get("display", "")
            kids.append(nav_event(screen_name(target)))
        elif t == "returnToButton":
            kids.append(nav_event(RETURN_TARGET))
        elif t == "momentaryButton":
            tg = tag_of(conn(e, "Value"))
            typ = "MomentaryButton"
            kids += [DV("MinHoldTime", "Duration", "0:00:00:0.2500000")]
            if tg: kids.append(link_prop("Active", "Boolean", tg[0], True))
            kids = [k for k in kids if k["Name"] != "ImagePath"] + [k for k in kids if k["Name"] == "ImagePath"]
        elif t == "latchedButton":
            tg = tag_of(conn(e, "Value"))
            kids.append(P("Toggle", "Boolean", True))
            if tg: kids.append(link_prop("Checked", "Boolean", tg[0], True))
        elif t == "languageSwitchButton":
            kids.append(set_event("{Session}/ActualLocaleId", "LocaleId", e.get("language", "de-DE")))
        elif t in ("rampButton", "loginButton", "logoutButton", "shutdownButton", "acknowledgeAlarmButton",
                   "silenceAlarmsButton", "clearAlarmBannerButton", "closeButton", "informationAckButton"):
            WARN.append(f"{ctx.screen}/{e.get('name')}: {t} has no function yet")
        return [N(name, typ, kids)]

    if t == "multistateIndicator":
        tg = tag_of(conn(e, "Indicator"))
        out = [N(name, "Rectangle", geo(e, ox, oy) + vis + [DV("FillColor", "Color", "#00ffffff"), P("BorderThickness", "Size", 0.0)])]
        st = e.find("states")
        for s in (st.findall("state") if st is not None else []):
            if s.get("value") is None or not tg: continue
            kids = [P("HorizontalAlignment", "HorizontalAlignment", 0), P("VerticalAlignment", "VerticalAlignment", 0),
                    P("LeftMargin", "Size", 0.0), P("TopMargin", "Size", 0.0), P("Width", "Size", w), P("Height", "Size", h),
                    DV("FillColor", "Color", col(s.get("backColor"), "#ffffff")),
                    DV("BorderColor", "Color", col(s.get("borderColor"), "#808080")),
                    P("BorderThickness", "Size", 0.0 if e.get("borderStyle") == "none" else 2.0),
                    expr_prop("Visible", "Boolean", "{0} == %s" % s.get("value"), [tg[0]], True)]
            sim = s.find("imageSettings")
            img = sim.get("imageName") if sim is not None else ""
            im_n = image_node("Image", img, w, h, ctx)
            if im_n: kids.append(im_n)
            cap = state_caption(s)
            if cap:
                kids.append(label("Text", cap, s.find("caption"), w, h))
            out[0]["Children"].append(N(f"State_{s.get('stateId')}", "Rectangle", kids))
        return out

    if t == "barGraph":
        tg = tag_of(conn(e, "Value"))
        mn, mx = float(e.get("minValue", 0)), float(e.get("maxValue", 100))
        fill = [P("HorizontalAlignment", "HorizontalAlignment", 3), P("VerticalAlignment", "VerticalAlignment", 2),
                DV("FillColor", "Color", col(e.get("fillColor"), "#40ff10")), P("BorderThickness", "Size", 0.0)]
        if tg:
            fill.append(expr_prop("Height", "Size", "max(0, min(%s, ({0}-%s)/%s*%s))" % (h, mn, mx - mn, h), [tg[0]]))
        return [N(name, "Rectangle", geo(e, ox, oy) + fill_props(e) + vis + [N("Level", "Rectangle", fill)])]

    if t == "numericInputCursorPoint":
        tg = tag_of(conn(e, "Value"))
        kids = geo(e, ox, oy) + vis + [P("FontSize", "Size", fsize(e)), P("MinValue", "Double", 0.0), P("MaxValue", "Double", 9999.0)]
        if tg: kids.append(link_prop("Value", "Double", tg[0], True))
        return [N(name, "SpinBox", kids)]

    if t in ("alarmStatusList", "alarmList", "alarmBanner", "diagnosticsList", "informationMessageDisplay"):
        WARN.append(f"{ctx.screen}/{e.get('name')}: {t} not converted (alarm system pending)")
        return [N(name, "Rectangle", geo(e, ox, oy) + fill_props(e) + vis + [
            label("Text", f"[{t}]", e, w, h)])]

    WARN.append(f"{ctx.screen}: unsupported element {t} ({e.get('name')})")
    return []

def grp_leaves(g):
    for c in g:
        if c.tag == "group": yield from grp_leaves(c)
        elif c.tag not in ("animations", "connections") and c.get("width") is not None: yield c

DISPLAY_NAMES = {}
RETURN_TARGET = "S0021_Handbetrieb"

def screen_name(display):
    return DISPLAY_NAMES.get(display, "S" + sanitize(display))

def build_screen(path):
    root = ET.parse(path).getroot()
    ds = root.find("displaySettings")
    base = os.path.splitext(os.path.basename(path))[0]
    sname = DISPLAY_NAMES[base]
    ctx = Ctx(sname)
    kids = [P("HorizontalAlignment", "HorizontalAlignment", 0), P("VerticalAlignment", "VerticalAlignment", 0),
            P("Width", "Size", float(ds.get("width"))), P("Height", "Size", float(ds.get("height"))),
            N("Background", "Rectangle", [P("HorizontalAlignment", "HorizontalAlignment", 3), P("VerticalAlignment", "VerticalAlignment", 3),
                                          DV("FillColor", "Color", col(ds.get("backColor"))), P("BorderThickness", "Size", 0.0)])]
    for c in root:
        if c.tag in ("displaySettings",): continue
        kids += [k for k in build(c, 0, 0, ctx) if k]
    return {"Name": sname, "Supertype": "Screen", "ReferenceType": "HasComponent", "Children": kids}, ctx

# ---------------------------------------------------------------- project files
def tag_nodes(csvpath):
    tree = {}
    DT = {"BOOL": "Boolean", "DINT": "Int32", "INT": "Int16", "REAL": "Float", "SINT": "SByte", "STRING": "String"}
    for r in csv.DictReader(open(csvpath, encoding="utf-8"), delimiter=";"):
        tag, dt = r["Tag"], r["DataType"]
        if dt not in DT or ".Help." in tag or ".SM." in tag: continue
        parts = tag.split(".")
        d = tree
        for p in parts[:-1]: d = d.setdefault(p, {})
        d[parts[-1]] = (tag, DT[dt])
    # bit access of PLCStatus.MinorFault (DINT) used by the displays
    d = tree["HMI"]["PLCStatus"]
    mf = d.pop("MinorFault", None)
    d["MinorFault"] = {str(i): (f"HMI.PLCStatus.MinorFault.{i}", "Boolean") for i in range(0, 32)}
    def conv(name, v):
        if isinstance(v, tuple):
            return N(name, "RAEtherNetIPTag", [DV("SymbolName", "String", v[0], optional=False)], DataType=v[1])
        return N(name, "FolderType", [conv(k, x) for k, x in v.items()])
    return N("Controller Tags", "FolderType", [conv(k, v) for k, v in tree["HMI"].items() and [("HMI", tree["HMI"])]])

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--template", required=True)
    ap.add_argument("--out", default=os.path.join(ROOT, "OptixProject", PROJ))
    a = ap.parse_args()
    T, O = a.template, a.out
    shutil.rmtree(O, ignore_errors=True)
    os.makedirs(O)

    pages = sorted(f for f in glob.glob(os.path.join(ROOT, "*.xml"))
                   if re.match(r"\d{4} ", os.path.basename(f)))
    for f in pages:
        base = os.path.splitext(os.path.basename(f))[0]
        DISPLAY_NAMES[base] = "S" + sanitize(base)
    global RETURN_TARGET
    RETURN_TARGET = DISPLAY_NAMES.get("0020 Produktion") or next(iter(DISPLAY_NAMES.values()))

    screens, imgs = [], set()
    for f in pages:
        s, ctx = build_screen(f)
        screens.append(s); imgs |= ctx.images

    # images
    os.makedirs(f"{O}/ProjectFiles/Images", exist_ok=True)
    for im in sorted(imgs):
        src = f"/root/png/{im}.png"
        if os.path.exists(src): shutil.copy(src, f"{O}/ProjectFiles/Images/{sanitize(im)}.png")
        else: WARN.append(f"image missing: {im}")

    # template based files
    nodes = f"{O}/Nodes"
    shutil.copytree(f"{T}/Nodes/CommDrivers", f"{nodes}/CommDrivers")
    shutil.copytree(f"{T}/Nodes/Security", f"{nodes}/Security")
    for d in ("OPC-UA", "NetLogic"): pass
    ctrl = f"{nodes}/CommDrivers/RAEtherNet_IPDriver1/RAEtherNet_IPStation1/Tags/Controller_Tags/Controller_Tags.yaml"
    dump(tag_nodes(os.path.join(ROOT, "analysis", "HMI_flat_tags.csv")), ctrl)
    ui_src = open(f"{T}/Nodes/UI/UI.yaml", encoding="utf-8").read().split("\n")
    style = "\n".join(ui_src[3:ui_src.index("- Name: RockwellStyleSheet")]) if "- Name: RockwellStyleSheet" in ui_src else ""
    start = next(i for i, l in enumerate(ui_src) if l.startswith("- Name: NativePresentationEngine"))
    mw = next(i for i, l in enumerate(ui_src) if l.startswith("- Name: MainWindow"))
    engine = "\n".join(ui_src[start:mw])
    engine = engine.replace("RockwellStyleSheet", "DefaultStyleSheet")
    ui = ["Name: UI", "Type: UICategoryFolder", "Children:", style, engine]
    ui_txt = "\n".join(ui)
    out = []
    mainw = {"Name": "MainWindow", "Supertype": "Window", "Children": [
        DV("Width", "Size", 480.0, optional=True), DV("Height", "Size", 272.0, optional=True),
        DV("Caption", "String", "HMI190", optional=False),
        N("PanelLoader1", "PanelLoader", [
            N("Panel", "NodePointer", [N("Kind", "PropertyType", DataType="NodeId", Value="/Types/ObjectTypes/BaseObjectType/BaseUIObject/Item/Container")],
              DataType="NodeId", Value=f"{SCREENS}/{RETURN_TARGET}"),
            N("CurrentPanel", "NodePointer", [N("Kind", "PropertyType", DataType="NodeId", Value="/Types/ObjectTypes/BaseObjectType/BaseUIObject/Item")],
              DataType="NodeId", AccessLevel="Read"),
            P("HorizontalAlignment", "HorizontalAlignment", 0), P("VerticalAlignment", "VerticalAlignment", 0),
            P("Width", "Size", 480.0), P("Height", "Size", 272.0)])]}
    emit(mainw, 0, out)
    ui_txt += "\n" + "\n".join(out) + "\n- File: Screens/Screens.yaml\n"
    ui_txt = ui_txt.replace("Optix_Sample_AzureIoTOperations", PROJ)
    ui_txt = re.sub(r"\n\s*Id: g=[0-9a-f]+", "", ui_txt)
    os.makedirs(f"{nodes}/UI", exist_ok=True)
    open(f"{nodes}/UI/UI.yaml", "w", encoding="utf-8", newline="\n").write(ui_txt)
    dump({"Name": "Screens", "Type": "ScreensCategoryFolder", "Children": screens}, f"{nodes}/UI/Screens/Screens.yaml")

    # model (local HMI variables)
    mvars = [DV(n, t, {"Boolean": False, "Int32": 0, "String": ""}[t], optional=False) for n, t in LOCAL_VARS.items()]
    for v in mvars:
        if v["Name"].startswith("UserHasCode"): v["Value"] = True
    dump({"Name": "Model", "Type": "ModelCategoryFolder", "Children": mvars}, f"{nodes}/Model/Model.yaml")

    # translations (de-DE source language)
    dump({"Name": "Translations", "Type": "TranslationsCategoryFolder"}, f"{nodes}/Translations/Translations.yaml")

    # project root node + .optix
    root = open(f"{T}/Nodes/Optix_Sample_AzureIoTOperations.yaml", encoding="utf-8").read()
    root = re.sub(r"\n\s*Id: g=[0-9a-f]+", "", root).replace("Optix_Sample_AzureIoTOperations", PROJ)
    root = root.replace('Value: ["en-US"]', 'Value: ["de-DE","en-GB","es-ES","fr-FR","ja-JP","pl-PL"]', 1)
    root = re.sub(r"- File: '?(OPC-UA|NetLogic)/[^\n]*\n", "", root)
    root = root.replace("- File: Translations/Translations.yaml\n", "- File: Translations/Translations.yaml\n")
    open(f"{nodes}/{PROJ}.yaml", "w", encoding="utf-8", newline="\n").write(root)
    opt = open(f"{T}/Optix_Sample_AzureIoTOperations.optix", encoding="utf-8").read()
    opt = opt.replace("Optix_Sample_AzureIoTOperations", PROJ)
    opt = re.sub(r"GUID: \w+", "GUID: " + uuid.uuid4().hex, opt)
    opt = re.sub(r"Statistics:.*?(?=Nodes:)", "", opt, flags=re.S)
    opt = re.sub(r" Nodes:.*", f" Nodes:\n - File: Nodes/{PROJ}.yaml\n", opt, flags=re.S)
    open(f"{O}/{PROJ}.optix", "w", encoding="utf-8", newline="\n").write(opt)

    print(f"screens: {len(screens)}  images: {len(imgs)}  warnings: {len(WARN)}")
    open(f"{O}/CONVERSION_WARNINGS.txt", "w", encoding="utf-8").write("\n".join(sorted(set(WARN))) + "\n")

if __name__ == "__main__":
    main()
