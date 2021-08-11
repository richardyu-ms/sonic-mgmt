"""
    SAI testing test bed setup.

    Notes:
        This test is used to setup the SAI testing environment, and start the SAI test cases
        from the PTF.

"""

import pytest
import socket
import sys
from struct import pack, unpack
import itertools
import logging

from ptf.mask import Mask
import ptf.packet as scapy
import tests.common.system_utils.docker as docker
import tests.common.fixtures.ptfhost_utils as ptfhost_utils

logger = logging.getLogger(__name__)


pytestmark = [
    pytest.mark.topology("ptf")
]


def test_ptf_setup(sai_testbed):
    """
        trigger the test here
    """
                     
@pytest.fixture(scope="module")
def sai_testbed(
    duthosts,
    rand_one_dut_hostname,
    creds,
    request,
    start_saiserver):
    """
        Pytest fixture to handle setup and cleanup for the SAI tests.
    """
    duthost = duthosts[rand_one_dut_hostname]
    try:        
        _setup_dut(duthost, creds, request)
        yield  
    finally:  
        _teardown_dut(duthost, creds)
        
def _setup_dut(dut, creds, request):
    """
        Sets up the SAI tests.
    """
    logging.info("Set up SAI tests.")


def _teardown_dut(duthost, creds):
    """
        Tears down the SAI test.
    """
    logging.info("Teardown SAI tests.")



    

