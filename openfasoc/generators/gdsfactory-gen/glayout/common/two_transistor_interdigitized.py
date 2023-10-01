from glayout.pdk.mappedpdk import MappedPDK
from pydantic import validate_arguments
from gdsfactory.component import Component
from glayout.fet import nmos, pmos, multiplier
from glayout.pdk.util.comp_utils import evaluate_bbox
from typing import Literal, Union
from glayout.pdk.util.port_utils import rename_ports_by_orientation, rename_ports_by_list
from glayout.pdk.util.comp_utils import prec_ref_center
from glayout.routing.straight_route import straight_route
from gdsfactory.functions import transformed
from glayout.guardring import tapring
from glayout.pdk.util.port_utils import add_ports_perimeter
from gdsfactory.cell import clear_cache


#from glayout.common.two_transistor_interdigitized import two_nfet_interdigitized; from glayout.pdk.sky130_mapped import sky130_mapped_pdk as pdk; biasParams=[6,2,4]; rmult=2

@validate_arguments
def two_transistor_interdigitized(
    pdk: MappedPDK,
    numcols: int,
    deviceA_and_B: Literal["nfet", "pfet"],
    dummy: Union[bool, tuple[bool, bool]] = True,
    **kwargs
) -> Component:
    """place two transistors in a single row with interdigitized placement
    Currently only supports two of the same transistor (same devices)
    Place follows an ABABAB... pattern
    args:
    pdk = MappedPDK to use
    numcols = a single col is actually one col for both transistors (so AB). 2 cols = ABAB ... so on
    deviceA_and_B = the device to place for both transistors (either nfet or pfet)
    dummy = place dummy at the edges of the interdigitized place (true by default). you can specify tuple to place only on one side
    kwargs = key word arguments for device. 
    ****NOTE: These are the same as glayout.fet.multiplier arguments EXCLUDING dummy, sd_route_extension, and pdk options
    """
    if isinstance(dummy, bool):
        dummy = (dummy, dummy)
    # override kwargs for needed options
    kwargs["sd_route_extension"] = 0
    kwargs["gate_route_extension"] = 0
    kwargs["sdlayer"] = "n+s/d" if deviceA_and_B == "nfet" else "p+s/d"
    kwargs["pdk"] = pdk
    # create devices dummy l/r and A/B (change extension options)
    kwargs["dummy"] = (True,False) if dummy[0] else False
    lefttmost_devA = multiplier(**kwargs)
    kwargs["dummy"] = False
    center_devA = multiplier(**kwargs)
    devB_sd_extension = pdk.util_max_metal_seperation() + abs(center_devA.ports["drain_N"].center[1]-center_devA.ports["diff_N"].center[1])
    devB_gate_extension = pdk.util_max_metal_seperation() + abs(center_devA.ports["row0_col0_gate_S"].center[1]-center_devA.ports["gate_S"].center[1])
    kwargs["sd_route_extension"] = pdk.snap_to_2xgrid(devB_sd_extension)
    kwargs["gate_route_extension"] = pdk.snap_to_2xgrid(devB_gate_extension)
    center_devB = multiplier(**kwargs)
    kwargs["dummy"] = (False,True) if dummy[1] else False
    rightmost_devB = multiplier(**kwargs)
    # place devices
    idplace = Component()
    dims = evaluate_bbox(center_devA)
    xdisp = pdk.snap_to_2xgrid(dims[0]+pdk.get_grule("active_diff")["min_separation"])
    refs = list()
    for i in range(2*numcols):
        if i==0:
            refs.append(idplace << lefttmost_devA)
        elif i==((2*numcols)-1):
            refs.append(idplace << rightmost_devB)
        elif i%2: # is odd (so device B)
            refs.append(idplace << center_devB)
        else: # not i%2 == i is even (so device A)
            refs.append(idplace << center_devA)
        refs[-1].movex(i*(xdisp))
        devletter = "B" if i%2 else "A"
        prefix=devletter+"_"+str(int(i/2))+"_"
        idplace.add_ports(refs[-1].get_ports_list(), prefix=prefix)
    #issue somehwere before line 89
    # merge s/d layer for all transistors
    idplace << straight_route(pdk, refs[0].ports["plusdoped_W"],refs[-1].ports["plusdoped_E"])
    # create s/d/gate connections extending over entire row
    A_src = idplace << rename_ports_by_orientation(rename_ports_by_list(straight_route(pdk, refs[0].ports["source_W"], refs[-1].ports["source_E"]), [("route_","_")]))
    B_src = idplace << rename_ports_by_orientation(rename_ports_by_list(straight_route(pdk, refs[-1].ports["source_E"], refs[0].ports["source_W"]), [("route_","_")]))
    A_drain = idplace << rename_ports_by_orientation(rename_ports_by_list(straight_route(pdk, refs[0].ports["drain_W"], refs[-1].ports["drain_E"]), [("route_","_")]))
    B_drain = idplace << rename_ports_by_orientation(rename_ports_by_list(straight_route(pdk, refs[-1].ports["drain_E"], refs[0].ports["drain_W"]), [("route_","_")]))
    A_gate = idplace << rename_ports_by_orientation(rename_ports_by_list(straight_route(pdk, refs[0].ports["gate_W"], refs[-1].ports["gate_E"]), [("route_","_")]))
    B_gate = idplace << rename_ports_by_orientation(rename_ports_by_list(straight_route(pdk, refs[-1].ports["gate_E"], refs[0].ports["gate_W"]), [("route_","_")]))
    # add route ports and return
    prefixes = ["A_source","B_source","A_drain","B_drain","A_gate","B_gate"]
    for i, ref in enumerate([A_src, B_src, A_drain, B_drain, A_gate, B_gate]):
        idplace.add_ports(ref.get_ports_list(),prefix=prefixes[i])
    idplace = transformed(prec_ref_center(idplace))
    idplace.unlock()
    return idplace


@validate_arguments
def two_nfet_interdigitized(
    pdk: MappedPDK,
    numcols: int,
    dummy: Union[bool, tuple[bool, bool]] = True,
    with_substrate_tap: bool = True,
    with_tie: bool = True,
    **kwargs
) -> Component:
    """Currently only supports two of the same nfet instances. does NOT support multipliers (currently)
    Place follows an ABABAB... pattern
    args:
    pdk = MappedPDK to use
    numcols = a single col is actually one col for both nfets (so AB). 2 cols = ABAB ... so on
    dummy = place dummy at the edges of the interdigitized place (true by default). you can specify tuple to place only on one side
    kwargs = key word arguments for multiplier. 
    ****NOTE: These are the same as glayout.fet.multiplier arguments EXCLUDING dummy, sd_route_extension, and pdk options
    """
    base_multiplier = two_transistor_interdigitized(pdk, numcols, "nfet", dummy, **kwargs)
    # tie
    if with_tie:
        tap_separation = max(
            pdk.get_grule("met2")["min_separation"],
            pdk.get_grule("met1")["min_separation"],
            pdk.get_grule("active_diff", "active_tap")["min_separation"],
        )
        tap_separation += pdk.get_grule("p+s/d", "active_tap")["min_enclosure"]
        tap_encloses = (
            2 * (tap_separation + base_multiplier.xmax),
            2 * (tap_separation + base_multiplier.ymax),
        )
        tiering_ref = base_multiplier << tapring(
            pdk,
            enclosed_rectangle=tap_encloses,
            sdlayer="p+s/d",
            horizontal_glayer="met2",
            vertical_glayer="met1",
        )
        base_multiplier.add_ports(tiering_ref.get_ports_list(), prefix="welltie_")
    # add pwell
    base_multiplier.add_padding(
        layers=(pdk.get_glayer("pwell"),),
        default=pdk.get_grule("pwell", "active_tap")["min_enclosure"],
    )
    # add substrate tap
    base_multiplier = add_ports_perimeter(base_multiplier,layer=pdk.get_glayer("pwell"),prefix="well_")
    # add substrate tap if with_substrate_tap
    if with_substrate_tap:
        substrate_tap_separation = pdk.get_grule("dnwell", "active_tap")[
            "min_separation"
        ]
        substrate_tap_encloses = (
            2 * (substrate_tap_separation + base_multiplier.xmax),
            2 * (substrate_tap_separation + base_multiplier.ymax),
        )
        ringtoadd = tapring(
            pdk,
            enclosed_rectangle=substrate_tap_encloses,
            sdlayer="p+s/d",
            horizontal_glayer="met2",
            vertical_glayer="met1",
        )
        tapring_ref = base_multiplier << ringtoadd
        base_multiplier.add_ports(tapring_ref.get_ports_list(),prefix="substratetap_")
    return base_multiplier
