# Copyright 2013-present Barefoot Networks, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""
Thrift SAI interface L3 tests
"""
import pytest
import socket
import sys
from struct import pack, unpack
import itertools
import logging
from ptf.mask import Mask
import ptf.packet as scapy

from switch import *

import debugpy
import pdb
logger = logging.getLogger(__name__)

pytestmark = [
    pytest.mark.topology('t0')
]

def test_router_interface(ptfadapter, ports_list, cfg_facts, ptfhost, dut_ip):
    print
    print "Sending packet port 1 -> port 2 (192.168.0.1 -> 10.10.10.1 [id = 101])"
    interface = ThriftInterface(dut_ip, ports_list)
    interface.setUp()
    switch_init(interface)

    port1 = ports_list[0]
    port2 = ports_list[1]
    v4_enabled = 1
    v6_enabled = 1
    mac_valid = 0
    mac = ''

    vr_id = sai_thrift_create_virtual_router(interface.client, v4_enabled, v6_enabled)

    rif_id1 = sai_thrift_create_router_interface(interface.client, vr_id, SAI_ROUTER_INTERFACE_TYPE_PORT, port1['sai_port_id'], 0, v4_enabled, v6_enabled, mac)
    rif_id2 = sai_thrift_create_router_interface(interface.client, vr_id, SAI_ROUTER_INTERFACE_TYPE_PORT, port2['sai_port_id'], 0, v4_enabled, v6_enabled, mac)

    addr_family = SAI_IP_ADDR_FAMILY_IPV4
    ip_addr1 = '10.10.10.1'
    ip_addr1_subnet = '10.10.10.0'
    ip_mask1 = '255.255.255.0'
    dmac1 = '00:11:22:33:44:55'
    sai_thrift_create_neighbor(interface.client, addr_family, rif_id1, ip_addr1, dmac1)
    nhop1 = sai_thrift_create_nhop(interface.client, addr_family, ip_addr1, rif_id1)
    sai_thrift_create_route(interface.client, vr_id, addr_family, ip_addr1_subnet, ip_mask1, rif_id1)

    # send the test packet(s)
    pkt = simple_tcp_packet(eth_dst=router_mac,
                            eth_src='00:22:22:22:22:22',
                            ip_dst='10.10.10.1',
                            ip_src='192.168.0.1',
                            ip_id=105,
                            ip_ttl=64)
    exp_pkt = simple_tcp_packet(
                            eth_dst='00:11:22:33:44:55',
                            eth_src=router_mac,
                            ip_dst='10.10.10.1',
                            ip_src='192.168.0.1',
                            ip_id=105,
                            ip_ttl=63)
    

    try:
        testutils.send(ptfadapter, port2["port_index"][0], str(pkt))
        testutils.verify_packets(ptfadapter, exp_pkt, [port1["port_index"][0]])
    finally:
        sai_thrift_remove_route(interface.client, vr_id, addr_family, ip_addr1_subnet, ip_mask1, rif_id1)
        interface.client.sai_thrift_remove_next_hop(nhop1)
        sai_thrift_remove_neighbor(interface.client, addr_family, rif_id1, ip_addr1, dmac1)

        interface.client.sai_thrift_remove_router_interface(rif_id1)
        interface.client.sai_thrift_remove_router_interface(rif_id2)

        interface.client.sai_thrift_remove_virtual_router(vr_id)
