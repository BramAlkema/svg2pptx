from core.color.utils import color_to_hex


def test_color_to_hex_handles_named_color():
    assert color_to_hex('red') == 'FF0000'


def test_color_to_hex_handles_hex_string():
    assert color_to_hex('#abc') == 'AABBCC'
    assert color_to_hex('#112233') == '112233'


def test_color_to_hex_handles_rgb():
    assert color_to_hex('rgb(0, 128, 255)') == '0080FF'


def test_color_to_hex_fallback():
    assert color_to_hex('invalid', default='123456') == '123456'
