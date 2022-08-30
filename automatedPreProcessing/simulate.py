from __future__ import print_function

import errno
import json
from os import path

import paramiko


def exists(sftp, path):
    """
    os.path.exists for paramiko's SCP object
    """
    try:
        sftp.stat(path)
    except IOError as e:
        if e.errno == errno.ENOENT:
            return False
    else:
        return True


def run_simulation(config_path, local_dir, case_name):
    """
    Run simulation of case on a remote ssh server with
    given input configuration.

    Args:
        config_path (str): Path to configuration file
        local_dir (str): Path to case folder
        case_name (str): Case name
    """
    client = paramiko.SSHClient()
    client.load_system_host_keys()

    config = json.load(open(config_path))

    try:
        hostname = config['hostname']
        username = config['username']
        password = config['password']
        remote_folder = config['remoteDataDir']
        local_folder = config["localDataDir"]
        job_script = config["job_script"]
    except KeyError:
        raise ValueError('Invalid configuration file')

    # Use case folder if local folder is blank
    local_dir = local_dir if local_folder == '' else local_folder

    # Get path to home folder on remote
    client.connect(hostname, username=username, password=password)
    stdin, stdout, stderr = client.exec_command('echo $HOME')
    home = str(stdout.read().strip().decode("utf-8"))

    sftp = client.open_sftp()
    remote_folder = path.join(home, remote_folder)

    # Upload run script
    sftp.chdir(remote_folder)
    if not exists(sftp, job_script):
        sftp.put(path.join(local_dir, job_script), job_script)

    # Upload mesh, probe points and info
    sftp.chdir(path.join(remote_folder, "oasis/mesh"))
    if not exists(sftp, case_name + ".xml.gz"):
        sftp.put(path.join(local_dir, case_name + ".xml.gz"), case_name + ".xml.gz")
    if not exists(sftp, case_name + "_probe_point"):
        sftp.put(path.join(local_dir, case_name + "_probe_point"), case_name + "_probe_point")
    if not exists(sftp, case_name + "_info.json"):
        sftp.put(path.join(local_dir, case_name + "_info.json"), case_name + "_info.json")

    if not exists(sftp, path.join(remote_folder, "results_{}".format(case_name))):
        sftp.mkdir(path.join(remote_folder, "results_{}".format(case_name)))

    sftp.close()

    # Run script
    stdin, stdout, stderr = client.exec_command('sbatch {}'.format(path.join(remote_folder, job_script)))

    for msg in stdout:
        print(msg)

    for msg in stderr:
        print(msg)

    client.close()
