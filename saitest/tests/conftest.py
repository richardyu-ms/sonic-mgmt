import pytest
import pdb

@pytest.fixture(scope="module")
def dut_ip(duthosts, rand_one_dut_hostname):
    duthost = duthosts[rand_one_dut_hostname]
    dutIp = duthost.host.options['inventory_manager'].get_host(duthost.hostname).vars['ansible_host']
    return dutIp

@pytest.fixture(scope="module")
def cfg_facts(duthosts, rand_one_dut_hostname):
    duthost = duthosts[rand_one_dut_hostname]
    return duthost.config_facts(host=duthost.hostname, source="persistent")['ansible_facts']

    

@pytest.fixture(scope="module")
def ports_list(cfg_facts, ptfhost):
    ports_list = []
    config_ports = cfg_facts['PORT']
    config_portchannels = cfg_facts.get('PORTCHANNEL', {})
    config_port_indices = cfg_facts['port_index_map']
    ptf_ports_available_in_topo = ptfhost.host.options['variable_manager'].extra_vars.get("ifaces_map")

    config_port_channel_members = [port_channel[1]['members'] for port_channel in config_portchannels.items()]
    config_port_channel_member_ports = list(itertools.chain.from_iterable(config_port_channel_members))

    ports = [port for port in config_ports
        if config_port_indices[port] in ptf_ports_available_in_topo
        and config_ports[port].get('admin_status', 'down') == 'up'
        and port not in config_port_channel_member_ports]

    for port in ports:
        ports_list.append({
            'dev' : port, #port name in DUT
            'port_index' : [config_port_indices[port]] #mapped port index in PTF
        })
    return ports_list

@pytest.fixture(scope="module")
def saiserver_interface(ports_list, ptfhost):
    interface = ThriftInterface(dut_ip, ports_list)
    interface.setUp()
    switch_init(interface)
    return interface
