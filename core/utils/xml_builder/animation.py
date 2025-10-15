"""Animation element generation helpers."""

from __future__ import annotations

from typing import TYPE_CHECKING

from lxml.etree import Element, QName, SubElement

from .constants import P_URI

if TYPE_CHECKING:  # pragma: no cover
    from .builder import EnhancedXMLBuilder


class AnimationGenerator:
    """Build PowerPoint animation XML fragments using shared builder state."""

    def __init__(self, builder: "EnhancedXMLBuilder") -> None:
        self.builder = builder

    def create_animation_element(
        self,
        effect_type: str,
        target_shape_id: int,
        *,
        duration: float = 1.0,
        delay: float = 0.0,
    ) -> Element:
        animation_id = self.builder.get_next_id()
        duration_ms = int(duration * 1000)
        delay_ms = int(delay * 1000)

        par = Element(QName(P_URI, "par"))
        c_tn = SubElement(par, QName(P_URI, "cTn"))
        c_tn.set("id", str(animation_id))
        c_tn.set("dur", "indefinite")
        c_tn.set("nodeType", "seq")

        child_tn_lst = SubElement(c_tn, QName(P_URI, "childTnLst"))
        child_par = SubElement(child_tn_lst, QName(P_URI, "par"))
        child_c_tn = SubElement(child_par, QName(P_URI, "cTn"))
        child_c_tn.set("id", str(animation_id + 1))
        child_c_tn.set("dur", str(duration_ms))
        child_c_tn.set("delay", str(delay_ms))

        child_child_tn_lst = SubElement(child_c_tn, QName(P_URI, "childTnLst"))
        anim_effect = SubElement(child_child_tn_lst, QName(P_URI, "animEffect"))
        anim_effect.set("transition", "in")
        anim_effect.set("filter", effect_type)

        c_bhvr = SubElement(anim_effect, QName(P_URI, "cBhvr"))
        bhvr_c_tn = SubElement(c_bhvr, QName(P_URI, "cTn"))
        bhvr_c_tn.set("id", str(animation_id + 2))
        bhvr_c_tn.set("dur", str(duration_ms))

        tgt_el = SubElement(c_bhvr, QName(P_URI, "tgtEl"))
        sp_tgt = SubElement(tgt_el, QName(P_URI, "spTgt"))
        sp_tgt.set("spid", str(target_shape_id))

        return par
