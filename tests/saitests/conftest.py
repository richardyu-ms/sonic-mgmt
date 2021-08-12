import logging

import pytest
import pdb

from thrift.transport import TSocket
from thrift.transport import TTransport
from thrift.protocol import TBinaryProtocol

from tests.common import config_reload
from tests.common.utilities import wait_until
from tests.common.helpers.assertions import pytest_assert as pt_assert
from tests.common.broadcom_data import is_broadcom_device
from tests.common.mellanox_data import is_mellanox_device
from tests.common.system_utils.docker import load_docker_registry_info
from tests.common.system_utils.docker import download_image
from tests.common.system_utils.docker import tag_image

logger = logging.getLogger(__name__)

OPT_DIR = "/opt"
SAISERVER_SCRIPT = "saiserver.sh"
SCRIPTS_SRC_DIR = "scripts/"
SERVICES_LIST = ["swss", "syncd", "radv", "lldp", "dhcp_relay", "teamd", "bgp", "pmon"]


@pytest.fixture(scope="module")
def start_saiserver(duthost, creds, deploy_saiserver):
    """
        Starts SAIServer docker on DUT.
    """
    _start_saiserver_with_retry(duthost)
    yield
    _stop_saiserver(duthost)


@pytest.fixture(scope="module")
def deploy_saiserver(duthost, creds, stop_other_services, prepare_saiserver_script):
    _deploy_saiserver(duthost, creds)
    yield
    _remove_saiserver_deploy(duthost, creds)


@pytest.fixture(scope="module")
def stop_other_services(duthost):
    _stop_dockers(duthost)
    yield
    _recover_dockers(duthost)


@pytest.fixture(scope="module")
def prepare_saiserver_script(duthost):
    _copy_saiserver_script(duthost)
    yield
    _delete_saiserver_script(duthost)


def _start_saiserver_with_retry(duthost):
    logger.info("Try to start saiserver.")
    sai_ready = wait_until(140, 35, _is_saiserver_restarted, duthost)
    pt_assert(sai_ready, "SaiServer failed to start in 140s")


def _is_saiserver_restarted(duthost):
    dut_ip = duthost.host.options['inventory_manager'].get_host(duthost.hostname).vars['ansible_host']
    if _is_container_running(duthost, 'saiserver'):
        logger.info("SAIServer already running, stop it for a restart")
        _stop_saiserver(duthost)
        duthost.shell("docker rm saiserver")
    _start_saiserver(duthost)
    rpc_ready = wait_until(32, 4, _is_rpc_server_ready, dut_ip)
    if not rpc_ready:
        logger.info("Failed to start up SAIServer, stop it for a restart")
    return rpc_ready


def _is_rpc_server_ready(dut_ip):
    try:
        transport = TSocket.TSocket(dut_ip, 9092)
        transport = TTransport.TBufferedTransport(transport)
        protocol  = TBinaryProtocol.TBinaryProtocol(transport)
        logger.info("Checking rpc connection : {}:{}".format(dut_ip, 9002))
        transport.open()
        return True
    except Exception as e: 
        logger.info("Cannot open rpc connection : {}".format(e))
        return False
    finally:
        transport.close()


def _start_saiserver(duthost):
    logger.info("Starting SAIServer docker for testing")      
    duthost.shell(OPT_DIR + "/" + SAISERVER_SCRIPT + " start")


def _stop_saiserver(duthost):
    logger.info("Stopping the container 'saiserver'...")
    duthost.shell(OPT_DIR + "/" + SAISERVER_SCRIPT + " stop")


def _deploy_saiserver(duthost, creds):
    """Deploy a saiserver docker for SAI testing.

    This will stop the swss and syncd, then download a new Docker image to the duthost.

    Args:
        duthost (SonicHost): The target device.
        creds (dict): Credentials used to access the docker registry.
    """
    vendor_id = _get_vendor_id(duthost)

    docker_saiserver_name = "docker-saiserver-{}".format(vendor_id)
    docker_saiserver_image = docker_saiserver_name

    logger.info("Loading docker image: {} ...".format(docker_saiserver_image))
    registry = load_docker_registry_info(duthost, creds)
    download_image(duthost, registry, docker_saiserver_image, duthost.os_version)

    tag_image(
    duthost,
    "{}:latest".format(docker_saiserver_name),
    "{}/{}".format(registry.host, docker_saiserver_image),
    duthost.os_version
    )

def _stop_database(duthost):
    logger.info("Stopping service '{}' ...".format(DB_SERVICE))
    duthost.stop_service(DB_SERVICE)


def _recover_database(duthost):
    logger.info("Starting service '{}' ...".format(DB_SERVICE))
    duthost.start_service(DB_SERVICE)


def _stop_dockers(duthost):
    """
        Stops all the services in SONiC dut.
    """
    for service in SERVICES_LIST:
        logger.info("Stopping service '{}' ...".format(service))
        duthost.stop_service(service)    

    _perform_services_shutdown_check(duthost)


def _recover_dockers(duthost):   
    logger.info("Reloading config and restarting other services ...")
    config_reload(duthost)


def _remove_saiserver_deploy(duthost, creds):
    """Reverts the saiserver docker's deployment.

    This will stop and remove the saiserver docker, then restart the swss and syncd.

    Args:
        duthost (SonicHost): The target device.
    """
    logger.info("Delete saiserver docker from DUT host '{0}'".format(duthost.hostname))
    vendor_id = _get_vendor_id(duthost)
    container_name = "saiserver"

    docker_saiserver_name = "docker-{}-{}".format(container_name, vendor_id)
    docker_saiserver_image = docker_saiserver_name

    logger.info("Cleaning the SAI Testing env ...")
    registry = load_docker_registry_info(duthost, creds)
    duthost.delete_container(container_name)    

    logger.info("Removing the image '{}'...".format(docker_saiserver_image))
    duthost.shell("docker image rm {}".format(docker_saiserver_image))
    duthost.command(
        "docker rmi {}/{}:{}".format(registry.host, docker_saiserver_image, duthost.os_version),
        module_ignore_errors=True
    )


def _copy_saiserver_script(duthost):
    """
        Copys script for controlling saiserver docker.

        Args:
            duthost (AnsibleHost): device under test

        Returns:
            None
    """
    logger.info("Copy saiserver script to DUT: '{0}'".format(duthost.hostname))
    duthost.copy(src=os.path.join(SCRIPTS_SRC_DIR, SAISERVER_SCRIPT), dest=OPT_DIR)
    duthost.shell("sudo chmod +x " + OPT_DIR + "/" + SAISERVER_SCRIPT)


def _delete_saiserver_script(duthost):
    logger.info("Delete saiserver script from DUT host '{0}'".format(duthost.hostname))
    duthost.file(path=os.path.join(OPT_DIR, SAISERVER_SCRIPT), state="absent")


def _perform_services_shutdown_check(duthost):
    running_services = []
    def ready_for_saiserver():
        for service in SERVICES_LIST:
            if _is_container_running(duthost, service):
                running_services.append(service)
        if running_services:
            return False
        return True
    
    shutdown_check = wait_until(10, 2, ready_for_saiserver)
    if running_services:
        format_list = ['{:>1}' for item in running_services] 
        servers = ','.join(format_list)
        pt_assert(shutdown_check, "Docker {} failed to shut down in 10s".format(servers.format(*running_services)))


def _is_container_running(duthost, container_name):
    try:
        result = duthost.shell("docker inspect -f \{{\{{.State.Running\}}\}} {}".format(container_name))
        return result["stdout_lines"][0].strip() == "true"
    except:
        logger.info("Cannot get container '{0}' running state".format(duthost.hostname))
    return False
    


def _get_vendor_id(duthost):
    if is_broadcom_device(duthost):
        vendor_id = "brcm"
    elif is_mellanox_device(duthost):
        vendor_id = "mlnx"
    else:
        error_message = '"{}" does not currently support saitest'.format(duthost.facts["asic_type"])
        logger.error(error_message)
        raise ValueError(error_message)

    return vendor_id





    

