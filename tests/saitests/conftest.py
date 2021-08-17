import logging

import pytest
import pdb

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
SERVICES_LIST = ["syncd", "radv", "lldp", "dhcp_relay", "teamd", "swss", "bgp", "pmon"]
DB_SERVICE = "database"


@pytest.fixture(scope="module")
def start_saiserver(duthost, creds, deploy_saiserver):
    """
        Starts SAIServer docker on DUT.
    """
    _start_saiserver(duthost)
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


def _start_saiserver(duthost):
    logging.info("Starting SAIServer docker for testing")      
    duthost.shell(OPT_DIR + "/" + SAISERVER_SCRIPT + " start")


def _stop_saiserver(duthost):
    logger.info("Stopping the container '{}'...".format(container_name))
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


def _stop_dockers(duthost):
    """
        Stops all the services in SONiC dut.
    """
    for service in SERVICES_LIST:
        logger.info("Stopping service '{}' ...".format(service))
        duthost.stop_service(service)
    
    logger.info("Stopping service '{}' ...".format(DB_SERVICE))
    duthost.stop_service(DB_SERVICE)
    _perform_services_shutdown_check(duthost)


def _recover_dockers(duthost):
    logger.info("Starting service '{}' ...".format(DB_SERVICE))
    duthost.start_service(DB_SERVICE)
    
    logger.info("Reloading config and restarting swss...")
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
    result = duthost.shell("docker inspect -f \{{\{{.State.Running\}}\}} {}".format(container_name))
    return result["stdout_lines"][0].strip() == "true"


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