"""
Base classes for test cases

Tests will usually inherit from one of these classes to have the controller
and/or dataplane automatically set up.
"""

import os
import logging
import unittest


import ptf
from ptf.base_tests import BaseTest
from ptf import config
import ptf.dataplane as dataplane
import ptf.testutils as testutils

################################################################
#
# Thrift interface base tests
#
################################################################

import switch_sai_thrift.switch_sai_rpc as switch_sai_rpc
from thrift.transport import TSocket
from thrift.transport import TTransport
from thrift.protocol import TBinaryProtocol

interface_to_front_mapping = {}
port_map_loaded=0

class ThriftInterface():

    def __init__(self, dut_ip, ports_list):
        self.dut_ip = dut_ip
        self.ports_list = ports_list

    def createRpcClient(self):
        # Set up thrift client and contact server

        if self.dut_ip:
            server = self.dut_ip
        else:
            server = 'localhost'
        
        self.transport = TSocket.TSocket(server, 9092)
        self.transport = TTransport.TBufferedTransport(self.transport)
        self.protocol = TBinaryProtocol.TBinaryProtocol(self.transport)

        self.client = switch_sai_rpc.Client(self.protocol)
        self.transport.open()
        return
 
    def setUp(self):
        self.createRpcClient()
        return

    def tearDown(self):
        self.transport.close()