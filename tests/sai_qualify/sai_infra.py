"""
    SAI testing test bed setup.

    Notes:
        This test is used to setup the SAI testing environment, and start the SAI test cases
        from the PTF.
        For running this tests, please specify the sai test case folder via the parameters --sai_test_folder.

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


def test_sai_from_ptf(sai_testbed):
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
    logger.info("Set up SAI tests.")
    sai_test_folder = request.config.option.sai_test_folder
    if not sai_test_folder:
        raise AttributeError("Needs to specify parameter: --sai_test_folder")
    logger.info("Runs for SAI tests at {}.".format(sai_test_folder))


def _teardown_dut(duthost, creds):
    """
        Tears down the SAI test.
    """
    logger.info("Teardown SAI tests.")
    