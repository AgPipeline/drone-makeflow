#!/usr/bin/env python3
"""Fetches code from a git repository, performs a quality check, and executes it
"""

import argparse
import logging
import os
import shutil
import subprocess
import tempfile

REPO_DIR = os.environ.get('SCIF_APPDATA_git_plot_rgb', os.path.abspath(os.path.dirname(__file__)))
PLOT_BASE_BRANCH = os.environ.get('PLOT_BASE_BRANCH', 'v1.10')
PLOT_BASE_REPO = os.environ.get('PLOT_BASE_REPO', 'https://github.com/AgPipeline/plot-base-rgb.git')


def _check_install_requirements(requirements_file: str) -> None:
    """Attempts to  install requirements in the specified file
    Arguments:
        requirements_file: the file containing the requirements
    """
    if os.path.exists(requirements_file):
        cmd = ('python3', '-m', 'pip', 'install', '--upgrade', '--no-cache-dir', '-r', requirements_file)
        #  We don't want an exception thrown, so we silence pylint
        # pylint: disable=subprocess-run-check
        res = subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        if res.returncode != 0:
            logging.warning('Unable to pip install requirements file "%s"', os.path.basename(requirements_file))
    elif requirements_file is not None:
        logging.warning('Specified requirements file was not found "%s"', requirements_file)
    else:
        logging.info('No requirements file specified for repository')


def _check_install_packages(source_file: str, working_dir: str, requirements_file: str = None) -> None:
    """Checks for missing Python packages in the specified file
    Arguments:
        source_file: the source file to check
        working_dir: folder where to place temporary files
        requirements_file: optional file containing requires Python modules
    """
    # Check for a requirements file and try to install those packages
    _check_install_requirements(requirements_file)

    with open(source_file, 'r', encoding='utf-8') as in_file:
        all_lines = in_file.read()

    # Perform a simple check on imports
    check_file = os.path.join(working_dir, '__check_import.py')
    module_lines = []
    module_names = []
    with open(check_file, 'w', encoding='utf-8') as out_file:
        for one_line in all_lines:
            if one_line.startswith('import ') or one_line.startswith('from '):
                out_file.write(one_line + '\n')
                line_chunks = one_line.split()
                if len(line_chunks) >= 2:
                    module_names.append(line_chunks[1])
                module_lines.append(one_line)

    # If there's nothing to do, just return
    if len(module_lines) <= 0:
        return

    num_tries = 0
    while True:
        # Try to run the file to catch missing includes
        cmd = ('python3', check_file)
        #  We don't want an exception thrown, so we silence pylint
        # pylint: disable=subprocess-run-check
        res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        if res.returncode == 0:
            break
        num_tries += 1
        if num_tries >= 2:
            break
        logging.info('Initial module check failed for "%s"', os.path.basename(check_file))
        logging.debug(res.stdout)

        # Try installing the modules
        if module_names:
            logging.debug('Trying to install modules %s', str(module_names))
            cmd = ('python3', '-m', 'pip', 'install', '--no-cache-dir', ' '.join(module_names))
            #  We don't want an exception thrown, so we silence pylint
            # pylint: disable=subprocess-run-check
            res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
            if res.returncode != 0:
                logging.warning('Unable to install all modules %s', ' '.join(module_names))
                logging.debug(res.stdout)

    if num_tries == 2:
        logging.warning('Not all modules may be available for running script "%s"',  os.path.basename(check_file))


def get_args() -> tuple:
    """Returns the command line arguments
    Returns:
        A tuple containing the git repo URI, the git branch or tag to use, and the command line
        arguments for the code
    """
    parser = argparse.ArgumentParser('Run Plot-level-RGB image code from a git repo')

    parser.add_argument('--requires', help='the file containing required Python packages')
    parser.add_argument('git_repo', help='git repository containing the plot-level RGB algorithm')
    parser.add_argument('git_branch', help='branch or tag of the git repository to use')
    parser.add_argument('arguments', help='arguments to pass to  the algorithm', nargs=argparse.REMAINDER)

    args = parser.parse_args()

    return args.git_repo, args.git_branch, args.requires, args.arguments


def run_git_code() -> None:
    """Fetches, checks, and runs code from a  git repository
    """
    git_repo, git_branch, requirements_file, run_args = get_args()

    # Get our working path
    working_dir = tempfile.mkdtemp(dir=REPO_DIR)
    os.makedirs(working_dir, exist_ok=True)

    try:
        base_dir = tempfile.mkdtemp(dir=REPO_DIR)
        os.makedirs(base_dir, exist_ok=True)
        # Get the base code from the repo
        cmd = ('git', 'clone', '--depth', '1', '--quiet', '--branch', PLOT_BASE_BRANCH, PLOT_BASE_REPO, base_dir)
        _ = subprocess.run(cmd, stdin=subprocess.PIPE, stderr=subprocess.STDOUT, check=True)

        # Install basic packages
        req_file = os.path.join(base_dir, 'requirements.txt')
        cmd = ('python3', '-m', 'pip', 'install', '--no-cache-dir', '-r', req_file)
        _ = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, check=True)

        # Get the code from the repo
        cmd = ('git', 'clone', '--depth', '1', '--quiet', '--branch', git_branch, git_repo, working_dir)
        _ = subprocess.run(cmd, stdin=subprocess.PIPE, stderr=subprocess.STDOUT, check=True)

        # Check the repo for validity
        check_file = os.path.join(working_dir, 'algorithm_rgb.py')
        if not os.path.exists(check_file):
            msg = 'Missing required file: algorithm_rgb.py in repo %s branch %s' % (git_repo, git_branch)
            logging.warning(msg)
            raise RuntimeError(msg)

        # Install packages
        req_file = requirements_file if requirements_file else os.path.join(working_dir, 'requirements.txt')
        _check_install_packages(check_file, working_dir, req_file)

        # Copy the base python files over
        for one_file in os.listdir(base_dir):
            if one_file.endswith('.py'):
                shutil.move(os.path.join(base_dir, one_file), os.path.join(working_dir, one_file))
        shutil.rmtree(base_dir)

        # Run the algorithm
        run_file = os.path.join(working_dir, 'transformer.py')
        cmd = ['python3', run_file]
        cmd = cmd + run_args
        _ = subprocess.run(cmd, stdin=subprocess.PIPE, stderr=subprocess.STDOUT, check=True)

    except Exception as ex:
        if logging.getLogger().level == logging.DEBUG:
            logging.exception('GIT repo %s branch/tag %s', git_repo, git_branch)
        else:
            logging.error('Exception caught for repo %s branch/tag %s', git_repo, git_branch)
            logging.error(ex)
    finally:
        shutil.rmtree(working_dir)


if __name__ == '__main__':
    run_git_code()
