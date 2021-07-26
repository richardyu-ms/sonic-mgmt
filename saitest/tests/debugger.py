import pytest

pytest.main([
    "--inventory", "../ansible/str,../ansible/veos", 
    "--host-pattern", "str-s6000-acs-12", 
    "--module-path", "../ansible", 
    "--testbed", "vms13-4-t0", 
    "--testbed_file", "../ansible/testbed.csv", 
    "--junit-xml=tr.xml", 
    "--log-cli-level info", 
    "--collect", "techsupport=False", 
    "--topology=t0,any,util", 
    "-k 'not test_fast_reboot'", "saithrift/stptest/test_sail3.py"])