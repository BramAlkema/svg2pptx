from lxml import etree as ET
from core.xml.safe_iter import walk, children

svg = ET.fromstring("""
<svg xmlns="http://www.w3.org/2000/svg" width="200" height="100">
  <!-- comment -->
  <?processing instruction?>
  <g id="layer1">
    <rect x="0" y="0" width="10" height="10"/>
    <!-- another -->
    <g><circle cx="5" cy="5" r="3"/></g>
  </g>
</svg>
""")

print("All elements via walk():")
for i, el in enumerate(walk(svg)):
    print(i, el.tag)

print("Children of root via children():")
for i, el in enumerate(children(svg)):
    print(i, el.tag)