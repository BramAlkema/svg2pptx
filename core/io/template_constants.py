"""Constants for Clean Slate PPTX templates."""

SLIDE_WIDTH_EMU = 9_144_000
SLIDE_HEIGHT_EMU = 6_858_000
NOTES_WIDTH_EMU = 6_858_000
NOTES_HEIGHT_EMU = 9_144_000

THEME_COLOR_SCHEME = {
    "dk1": {"type": "sysClr", "attrs": {"val": "windowText", "lastClr": "000000"}},
    "lt1": {"type": "sysClr", "attrs": {"val": "window", "lastClr": "FFFFFF"}},
    "dk2": {"type": "srgbClr", "val": "1F497D"},
    "lt2": {"type": "srgbClr", "val": "EEECE1"},
    "accent1": {"type": "srgbClr", "val": "4F81BD"},
    "accent2": {"type": "srgbClr", "val": "F79646"},
    "accent3": {"type": "srgbClr", "val": "9BBB59"},
    "accent4": {"type": "srgbClr", "val": "8064A2"},
    "accent5": {"type": "srgbClr", "val": "4BACC6"},
    "accent6": {"type": "srgbClr", "val": "F366CC"},
    "hlink": {"type": "srgbClr", "val": "0000FF"},
    "folHlink": {"type": "srgbClr", "val": "800080"},
}

THEME_MAJOR_LATIN_FONT = "Calibri Light"
THEME_MINOR_LATIN_FONT = "Calibri"

DEFAULT_APPLICATION_NAME = "SVG2PPTX"
DEFAULT_SLIDE_TITLE_PREFIX = "Slide "
