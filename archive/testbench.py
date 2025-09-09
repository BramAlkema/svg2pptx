#!/usr/bin/env python3
"""
Local Python Testbench for SVG to PPTX Direct Integration

Creates actual PPTX files by manually building the ZIP structure
and injecting DrawingML shapes directly into slide XML.
"""

import os
import zipfile
import tempfile
import xml.etree.ElementTree as ET
from pathlib import Path
from src.svg2drawingml import SVGToDrawingMLConverter


class PPTXBuilder:
    """Build PPTX files from scratch with direct XML manipulation."""
    
    def __init__(self):
        self.slide_width = 9144000   # 10 inches in EMUs
        self.slide_height = 6858000  # 7.5 inches in EMUs
        
    def create_minimal_pptx(self, drawingml_shapes: str, output_path: str):
        """Create a minimal PPTX file with DrawingML shapes."""
        
        # Create temporary directory for PPTX structure
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            
            # Create PPTX directory structure
            self._create_pptx_structure(temp_path)
            
            # Create slide with our DrawingML shapes
            slide_xml = self._create_slide_xml(drawingml_shapes)
            (temp_path / 'ppt' / 'slides' / 'slide1.xml').write_text(slide_xml, encoding='utf-8')
            
            # Create ZIP archive
            self._zip_pptx_structure(temp_path, output_path)
    
    def _create_pptx_structure(self, base_path: Path):
        """Create the basic PPTX directory structure and required files."""
        
        # Create directories
        (base_path / 'ppt' / 'slides').mkdir(parents=True)
        (base_path / 'ppt' / 'slideLayouts').mkdir(parents=True)
        (base_path / 'ppt' / 'slideMasters').mkdir(parents=True)
        (base_path / 'ppt' / 'theme').mkdir(parents=True)
        (base_path / '_rels').mkdir(parents=True)
        (base_path / 'ppt' / '_rels').mkdir(parents=True)
        (base_path / 'ppt' / 'slides' / '_rels').mkdir(parents=True)
        
        # Create [Content_Types].xml
        content_types = f'''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
    <Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
    <Default Extension="xml" ContentType="application/xml"/>
    <Override PartName="/ppt/presentation.xml" ContentType="application/vnd.openxmlformats-officedocument.presentationml.presentation.main+xml"/>
    <Override PartName="/ppt/slides/slide1.xml" ContentType="application/vnd.openxmlformats-officedocument.presentationml.slide+xml"/>
    <Override PartName="/ppt/theme/theme1.xml" ContentType="application/vnd.openxmlformats-officedocument.theme+xml"/>
    <Override PartName="/ppt/slideLayouts/slideLayout1.xml" ContentType="application/vnd.openxmlformats-officedocument.presentationml.slideLayout+xml"/>
    <Override PartName="/ppt/slideMasters/slideMaster1.xml" ContentType="application/vnd.openxmlformats-officedocument.presentationml.slideMaster+xml"/>
</Types>'''
        (base_path / '[Content_Types].xml').write_text(content_types, encoding='utf-8')
        
        # Create main .rels file
        main_rels = '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
    <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="ppt/presentation.xml"/>
</Relationships>'''
        (base_path / '_rels' / '.rels').write_text(main_rels, encoding='utf-8')
        
        # Create presentation.xml
        presentation_xml = f'''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<p:presentation xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main" xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">
    <p:sldMasterIdLst>
        <p:sldMasterId id="2147483648" r:id="rId1"/>
    </p:sldMasterIdLst>
    <p:sldIdLst>
        <p:sldId id="256" r:id="rId2"/>
    </p:sldIdLst>
    <p:sldSz cx="{self.slide_width}" cy="{self.slide_height}"/>
    <p:notesSz cx="6858000" cy="9144000"/>
</p:presentation>'''
        (base_path / 'ppt' / 'presentation.xml').write_text(presentation_xml, encoding='utf-8')
        
        # Create presentation relationships
        ppt_rels = '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
    <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/slideMaster" Target="slideMasters/slideMaster1.xml"/>
    <Relationship Id="rId2" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/slide" Target="slides/slide1.xml"/>
    <Relationship Id="rId3" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/theme" Target="theme/theme1.xml"/>
</Relationships>'''
        (base_path / 'ppt' / '_rels' / 'presentation.xml.rels').write_text(ppt_rels, encoding='utf-8')
        
        # Create slide relationships
        slide_rels = '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
    <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/slideLayout" Target="../slideLayouts/slideLayout1.xml"/>
</Relationships>'''
        (base_path / 'ppt' / 'slides' / '_rels' / 'slide1.xml.rels').write_text(slide_rels, encoding='utf-8')
        
        # Create minimal theme
        theme_xml = '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<a:theme xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" name="Office Theme">
    <a:themeElements>
        <a:clrScheme name="Office">
            <a:dk1><a:sysClr val="windowText" lastClr="000000"/></a:dk1>
            <a:lt1><a:sysClr val="window" lastClr="FFFFFF"/></a:lt1>
            <a:dk2><a:srgbClr val="1F497D"/></a:dk2>
            <a:lt2><a:srgbClr val="EEECE1"/></a:lt2>
            <a:accent1><a:srgbClr val="4F81BD"/></a:accent1>
            <a:accent2><a:srgbClr val="F79646"/></a:accent2>
            <a:accent3><a:srgbClr val="9BBB59"/></a:accent3>
            <a:accent4><a:srgbClr val="8064A2"/></a:accent4>
            <a:accent5><a:srgbClr val="4BACC6"/></a:accent5>
            <a:accent6><a:srgbClr val="F79646"/></a:accent6>
            <a:hlink><a:srgbClr val="0000FF"/></a:hlink>
            <a:folHlink><a:srgbClr val="800080"/></a:folHlink>
        </a:clrScheme>
        <a:fontScheme name="Office">
            <a:majorFont>
                <a:latin typeface="Calibri"/>
                <a:ea typeface=""/>
                <a:cs typeface=""/>
            </a:majorFont>
            <a:minorFont>
                <a:latin typeface="Calibri"/>
                <a:ea typeface=""/>
                <a:cs typeface=""/>
            </a:minorFont>
        </a:fontScheme>
        <a:fmtScheme name="Office">
            <a:fillStyleLst>
                <a:solidFill><a:schemeClr val="phClr"/></a:solidFill>
                <a:gradFill rotWithShape="1">
                    <a:gsLst>
                        <a:gs pos="0"><a:schemeClr val="phClr"><a:tint val="50000"/><a:satMod val="300000"/></a:schemeClr></a:gs>
                        <a:gs pos="35000"><a:schemeClr val="phClr"><a:tint val="37000"/><a:satMod val="300000"/></a:schemeClr></a:gs>
                        <a:gs pos="100000"><a:schemeClr val="phClr"><a:tint val="15000"/><a:satMod val="350000"/></a:schemeClr></a:gs>
                    </a:gsLst>
                    <a:lin ang="16200000" scaled="1"/>
                </a:gradFill>
                <a:gradFill rotWithShape="1">
                    <a:gsLst>
                        <a:gs pos="0"><a:schemeClr val="phClr"><a:shade val="51000"/><a:satMod val="130000"/></a:schemeClr></a:gs>
                        <a:gs pos="80000"><a:schemeClr val="phClr"><a:shade val="93000"/><a:satMod val="130000"/></a:schemeClr></a:gs>
                        <a:gs pos="100000"><a:schemeClr val="phClr"><a:shade val="94000"/><a:satMod val="135000"/></a:schemeClr></a:gs>
                    </a:gsLst>
                    <a:lin ang="16200000" scaled="0"/>
                </a:gradFill>
            </a:fillStyleLst>
            <a:lnStyleLst>
                <a:ln w="9525" cap="flat" cmpd="sng" algn="ctr">
                    <a:solidFill><a:schemeClr val="phClr"><a:shade val="95000"/><a:satMod val="105000"/></a:schemeClr></a:solidFill>
                    <a:prstDash val="solid"/>
                </a:ln>
                <a:ln w="25400" cap="flat" cmpd="sng" algn="ctr">
                    <a:solidFill><a:schemeClr val="phClr"/></a:solidFill>
                    <a:prstDash val="solid"/>
                </a:ln>
                <a:ln w="38100" cap="flat" cmpd="sng" algn="ctr">
                    <a:solidFill><a:schemeClr val="phClr"/></a:solidFill>
                    <a:prstDash val="solid"/>
                </a:ln>
            </a:lnStyleLst>
            <a:effectStyleLst>
                <a:effectStyle>
                    <a:effectLst>
                        <a:outerShdw blurRad="40000" dist="20000" dir="5400000" rotWithShape="0">
                            <a:srgbClr val="000000"><a:alpha val="38000"/></a:srgbClr>
                        </a:outerShdw>
                    </a:effectLst>
                </a:effectStyle>
                <a:effectStyle>
                    <a:effectLst>
                        <a:outerShdw blurRad="40000" dist="23000" dir="5400000" rotWithShape="0">
                            <a:srgbClr val="000000"><a:alpha val="35000"/></a:srgbClr>
                        </a:outerShdw>
                    </a:effectLst>
                </a:effectStyle>
                <a:effectStyle>
                    <a:effectLst>
                        <a:outerShdw blurRad="40000" dist="23000" dir="5400000" rotWithShape="0">
                            <a:srgbClr val="000000"><a:alpha val="35000"/></a:srgbClr>
                        </a:outerShdw>
                    </a:effectLst>
                </a:effectStyle>
            </a:effectStyleLst>
            <a:bgFillStyleLst>
                <a:solidFill><a:schemeClr val="phClr"/></a:solidFill>
                <a:gradFill rotWithShape="1">
                    <a:gsLst>
                        <a:gs pos="0"><a:schemeClr val="phClr"><a:tint val="40000"/><a:satMod val="350000"/></a:schemeClr></a:gs>
                        <a:gs pos="40000"><a:schemeClr val="phClr"><a:tint val="45000"/><a:shade val="99000"/><a:satMod val="350000"/></a:schemeClr></a:gs>
                        <a:gs pos="100000"><a:schemeClr val="phClr"><a:shade val="20000"/><a:satMod val="255000"/></a:schemeClr></a:gs>
                    </a:gsLst>
                    <a:path path="circle">
                        <a:fillToRect l="50000" t="-80000" r="50000" b="180000"/>
                    </a:path>
                </a:gradFill>
                <a:gradFill rotWithShape="1">
                    <a:gsLst>
                        <a:gs pos="0"><a:schemeClr val="phClr"><a:tint val="80000"/><a:satMod val="300000"/></a:schemeClr></a:gs>
                        <a:gs pos="100000"><a:schemeClr val="phClr"><a:shade val="30000"/><a:satMod val="200000"/></a:schemeClr></a:gs>
                    </a:gsLst>
                    <a:path path="circle">
                        <a:fillToRect l="50000" t="50000" r="50000" b="50000"/>
                    </a:path>
                </a:gradFill>
            </a:bgFillStyleLst>
        </a:fmtScheme>
    </a:themeElements>
</a:theme>'''
        (base_path / 'ppt' / 'theme' / 'theme1.xml').write_text(theme_xml, encoding='utf-8')
        
        # Create minimal slide layout
        layout_xml = '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<p:sldLayout xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main" xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" preserve="1">
    <p:cSld name="Blank">
        <p:spTree>
            <p:nvGrpSpPr>
                <p:cNvPr id="1" name=""/>
                <p:cNvGrpSpPr/>
                <p:nvPr/>
            </p:nvGrpSpPr>
            <p:grpSpPr>
                <a:xfrm/>
            </p:grpSpPr>
        </p:spTree>
    </p:cSld>
    <p:clrMapOvr>
        <a:masterClrMapping/>
    </p:clrMapOvr>
</p:sldLayout>'''
        (base_path / 'ppt' / 'slideLayouts' / 'slideLayout1.xml').write_text(layout_xml, encoding='utf-8')
        
        # Create minimal slide master
        master_xml = '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<p:sldMaster xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main" xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">
    <p:cSld>
        <p:bg>
            <p:bgRef idx="1001">
                <a:schemeClr val="bg1"/>
            </p:bgRef>
        </p:bg>
        <p:spTree>
            <p:nvGrpSpPr>
                <p:cNvPr id="1" name=""/>
                <p:cNvGrpSpPr/>
                <p:nvPr/>
            </p:nvGrpSpPr>
            <p:grpSpPr>
                <a:xfrm/>
            </p:grpSpPr>
        </p:spTree>
    </p:cSld>
    <p:clrMap bg1="lt1" tx1="dk1" bg2="lt2" tx2="dk2" accent1="accent1" accent2="accent2" accent3="accent3" accent4="accent4" accent5="accent5" accent6="accent6" hlink="hlink" folHlink="folHlink"/>
    <p:sldLayoutIdLst>
        <p:sldLayoutId id="2147483649" r:id="rId1"/>
    </p:sldLayoutIdLst>
    <p:txStyles>
        <p:titleStyle>
            <a:lvl1pPr marL="0" algn="ctr" defTabSz="914400" rtl="0" eaLnBrk="1" latinLnBrk="0" hangingPunct="1">
                <a:defRPr sz="4400" kern="1200">
                    <a:solidFill><a:schemeClr val="tx1"/></a:solidFill>
                    <a:latin typeface="+mj-lt"/>
                    <a:ea typeface="+mj-ea"/>
                    <a:cs typeface="+mj-cs"/>
                </a:defRPr>
            </a:lvl1pPr>
        </p:titleStyle>
        <p:bodyStyle>
            <a:lvl1pPr marL="342900" indent="-342900" algn="l" defTabSz="914400" rtl="0" eaLnBrk="1" latinLnBrk="0" hangingPunct="1">
                <a:defRPr sz="1800" kern="1200">
                    <a:solidFill><a:schemeClr val="tx1"/></a:solidFill>
                    <a:latin typeface="+mn-lt"/>
                    <a:ea typeface="+mn-ea"/>
                    <a:cs typeface="+mn-cs"/>
                </a:defRPr>
            </a:lvl1pPr>
        </p:bodyStyle>
    </p:txStyles>
</p:sldMaster>'''
        (base_path / 'ppt' / 'slideMasters' / 'slideMaster1.xml').write_text(master_xml, encoding='utf-8')

    def _create_slide_xml(self, drawingml_shapes: str) -> str:
        """Create slide XML with embedded DrawingML shapes."""
        
        # Clean up the DrawingML shapes - remove leading whitespace
        shapes_clean = '\n'.join([line.strip() for line in drawingml_shapes.split('\n') if line.strip()])
        
        slide_xml = f'''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<p:sld xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main" xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">
    <p:cSld>
        <p:spTree>
            <p:nvGrpSpPr>
                <p:cNvPr id="1" name=""/>
                <p:cNvGrpSpPr/>
                <p:nvPr/>
            </p:nvGrpSpPr>
            <p:grpSpPr>
                <a:xfrm>
                    <a:off x="0" y="0"/>
                    <a:ext cx="{self.slide_width}" cy="{self.slide_height}"/>
                    <a:chOff x="0" y="0"/>
                    <a:chExt cx="{self.slide_width}" cy="{self.slide_height}"/>
                </a:xfrm>
            </p:grpSpPr>
            {shapes_clean}
        </p:spTree>
    </p:cSld>
    <p:clrMapOvr>
        <a:masterClrMapping/>
    </p:clrMapOvr>
</p:sld>'''
        
        return slide_xml
    
    def _zip_pptx_structure(self, temp_path: Path, output_path: str):
        """Create ZIP archive from PPTX directory structure."""
        with zipfile.ZipFile(output_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for file_path in temp_path.rglob('*'):
                if file_path.is_file():
                    arcname = str(file_path.relative_to(temp_path))
                    zipf.write(file_path, arcname)


class SVGToPPTXTestbench:
    """Complete testbench for SVG to PPTX conversion."""
    
    def __init__(self):
        self.svg_converter = SVGToDrawingMLConverter()
        self.pptx_builder = PPTXBuilder()
    
    def test_simple_conversion(self):
        """Test conversion with simple SVG shapes."""
        print("=== Testing Simple SVG to PPTX Conversion ===")
        
        simple_svg = '''<?xml version="1.0"?>
<svg width="400" height="300" xmlns="http://www.w3.org/2000/svg">
    <rect x="50" y="50" width="100" height="80" fill="#ff0000" stroke="#000000" stroke-width="2"/>
    <circle cx="250" cy="100" r="40" fill="#00ff00" stroke="#0000ff" stroke-width="3"/>
    <ellipse cx="150" cy="200" rx="60" ry="30" fill="#0000ff"/>
    <line x1="50" y1="250" x2="350" y2="250" stroke="#ff00ff" stroke-width="4"/>
</svg>'''
        
        # Convert SVG to DrawingML
        print("1. Converting SVG to DrawingML...")
        drawingml = self.svg_converter.convert(simple_svg)
        
        # Count shapes
        rectangles = drawingml.count('<p:sp>')
        lines = drawingml.count('<p:cxnSp>')
        print(f"   Generated {rectangles} shapes and {lines} lines")
        
        # Create PPTX
        print("2. Creating PPTX file...")
        output_file = "test_simple.pptx"
        self.pptx_builder.create_minimal_pptx(drawingml, output_file)
        
        # Verify file
        if os.path.exists(output_file):
            size = os.path.getsize(output_file)
            print(f"   ✓ Created {output_file} ({size:,} bytes)")
            return True
        else:
            print(f"   ✗ Failed to create {output_file}")
            return False
    
    def test_file_conversion(self, svg_file: str):
        """Test conversion with an actual SVG file."""
        print(f"\n=== Testing File Conversion: {svg_file} ===")
        
        if not os.path.exists(svg_file):
            print(f"   ✗ SVG file not found: {svg_file}")
            return False
        
        try:
            # Convert SVG to DrawingML  
            print("1. Converting SVG file to DrawingML...")
            drawingml = self.svg_converter.convert_file(svg_file)
            
            # Count elements
            shapes = drawingml.count('<p:sp>')
            lines = drawingml.count('<p:cxnSp>')
            paths = drawingml.count('SVG Path:')
            print(f"   Found {shapes} shapes, {lines} lines, {paths} paths")
            
            # Create PPTX
            print("2. Creating PPTX file...")
            svg_name = Path(svg_file).stem
            output_file = f"test_{svg_name}.pptx"
            self.pptx_builder.create_minimal_pptx(drawingml, output_file)
            
            # Verify file
            if os.path.exists(output_file):
                size = os.path.getsize(output_file)
                print(f"   ✓ Created {output_file} ({size:,} bytes)")
                return True
            else:
                print(f"   ✗ Failed to create {output_file}")
                return False
                
        except Exception as e:
            print(f"   ✗ Error: {e}")
            return False
    
    def validate_pptx_structure(self, pptx_file: str):
        """Validate the internal structure of generated PPTX."""
        print(f"\n=== Validating PPTX Structure: {pptx_file} ===")
        
        try:
            with zipfile.ZipFile(pptx_file, 'r') as zipf:
                files = zipf.namelist()
                
                # Check required files
                required_files = [
                    '[Content_Types].xml',
                    '_rels/.rels',
                    'ppt/presentation.xml',
                    'ppt/slides/slide1.xml'
                ]
                
                missing_files = []
                for req_file in required_files:
                    if req_file not in files:
                        missing_files.append(req_file)
                
                if missing_files:
                    print(f"   ✗ Missing required files: {missing_files}")
                    return False
                
                # Check slide content
                slide_content = zipf.read('ppt/slides/slide1.xml').decode('utf-8')
                if '<p:spTree>' in slide_content and '<p:sp>' in slide_content:
                    shape_count = slide_content.count('<p:sp>')
                    print(f"   ✓ Valid PPTX structure with {shape_count} shapes")
                    
                    # Show a sample of the slide XML
                    print("   Sample slide XML:")
                    lines = slide_content.split('\n')[:15]
                    for line in lines:
                        if line.strip():
                            print(f"     {line.strip()}")
                    print("     ...")
                    
                    return True
                else:
                    print("   ✗ Invalid slide structure - missing shapes")
                    return False
                    
        except Exception as e:
            print(f"   ✗ Error validating PPTX: {e}")
            return False
    
    def run_all_tests(self):
        """Run complete test suite."""
        print("SVG to PPTX Direct Integration Testbench")
        print("=" * 50)
        
        results = []
        
        # Test 1: Simple shapes
        results.append(self.test_simple_conversion())
        
        # Test 2: Example SVG file
        if os.path.exists('examples/input.svg'):
            results.append(self.test_file_conversion('examples/input.svg'))
        
        # Validation tests
        if os.path.exists('test_simple.pptx'):
            results.append(self.validate_pptx_structure('test_simple.pptx'))
        
        # Summary
        print(f"\n=== Test Results ===")
        passed = sum(results)
        total = len(results)
        print(f"Passed: {passed}/{total} tests")
        
        if passed == total:
            print("🎉 All tests passed! SVG to PPTX conversion is working!")
        else:
            print("❌ Some tests failed. Check the output above.")
        
        return passed == total


def main():
    """Run the testbench."""
    testbench = SVGToPPTXTestbench()
    success = testbench.run_all_tests()
    
    if success:
        print("\n✅ Testbench completed successfully!")
        print("You can now open the generated .pptx files in PowerPoint!")
    else:
        print("\n❌ Testbench had failures.")


if __name__ == "__main__":
    main()