#!/usr/bin/env python3
"""Run the failing E2E test with full stack trace."""
import sys
import traceback
import logging

# Set up detailed logging
logging.basicConfig(level=logging.DEBUG, format='%(name)s:%(lineno)d - %(message)s')

try:
    from tests.e2e.test_clean_slate_e2e import TestCleanSlateE2E

    test = TestCleanSlateE2E()
    test.test_complex_svg_features()
    print("✅ Test passed!")

except Exception as e:
    print(f"\n❌ Test failed with: {e}")
    print(f"\nFull traceback:")
    traceback.print_exc()

    # Get the actual exception chain
    print(f"\n\nException type: {type(e)}")
    print(f"Exception args: {e.args}")

    # Try to get more context
    tb = sys.exc_info()[2]
    print(f"\n\nTraceback details:")
    while tb:
        frame = tb.tb_frame
        print(f"  File: {frame.f_code.co_filename}:{tb.tb_lineno}")
        print(f"  Function: {frame.f_code.co_name}")
        print(f"  Locals: {list(frame.f_locals.keys())[:10]}")  # First 10 locals
        tb = tb.tb_next
