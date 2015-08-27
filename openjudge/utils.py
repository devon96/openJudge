import os
import logging
import signal
import subprocess
from random import sample
from . import config, errors
from urllib.request import urlretrieve, urlopen
from urllib.error import URLError
from json import loads


class bcolors:  # for printing in terminal with colours
    """
    Simple coloured output in the terminal to help distinguish between
    things
    """
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'

logging.basicConfig(filename=config.logfile,
                    level=logging.DEBUG)
judge_log = logging.getLogger('utils')


def get_result(return_val, out, out_recieved):
    """
    Based on return value provided,
             output recieved,
             output expected
    return a result which is in
            [Timeout, Correct, Incorrect, Error, <catchall>]
    along with a remark pertaining to the case.
    """
    result = 'Contact a volunteer'
    if return_val is None:
        result = 'Timeout'
        judge_log.info(result)
    elif isinstance(return_val, int):
        if return_val != 0:
            judge_log.info('ERROR: Return value non zero: ' + str(return_val))
            result = 'Error'
            judge_log.info(result)
        else:
            if check_execution(out, out_recieved):
                result = 'Correct'
                judge_log.info(result)
            else:
                result = 'Incorrect'
                judge_log.info(result)
    return result


def get_random_string(l=10):
    "Returns a string of random alphabets of 'l' length"
    alpha = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz'
    if l > 26*2:
        alpha = alpha * (int(l/(26*2)) + 1)
    return ''.join(sample(alpha, l))


def get_file_from_url(url, folder, overwrite=False):
    "Get file from url. Overwrite if overwrite=True"
    # create storage path
    path = os.path.join(config.check_data_folder, folder)
    if not os.path.exists(path):
        os.makedirs(path)
    # get file name
    filename = url.split('/')[-1]
    filepath = os.path.join(path, filename)
    if not overwrite and os.path.exists(filepath):
        salt = get_random_string()
        filename = salt + filename
    # get resources
    complete_path = os.path.join(path, filename)
    try:
        fl_name, _ = urlretrieve(url, complete_path)
    except URLError:
        raise errors.InterfaceNotRunning('URL unavailable: {}'.format(url))
    return os.path.join(os.getcwd(), fl_name)


def get_json(url):
    "Get json from url and return dict"
    try:
        page = urlopen(url)
    except URLError:
        raise errors.InterfaceNotRunning('URL unavailable: {}'.format(url))
    text = page.read().decode()
    data = loads(text)
    return data


def check_execution(out_expected, out_recieved, check_error=None):
    """Check if output is correct.
    Output is checked against expected output.
    There are two methods of checking.
        - Exact      : String comparison is made
        - Error range: Difference must be within error range
    """
    # get output files
    with open(out_expected, 'r') as f:
        lines_expected = f.readlines()
    lines_got = out_recieved.split('\n')
    # check line by line
    for got, exp in zip(lines_got, lines_expected):
        if check_error is None:  # exact checking
            if exp.strip() != got.strip():
                return False
        else:  # error range checking
            if abs(eval(exp.strip()) - eval(got.strip())) > check_error:
                return False
    return True


def run_command(cmd, timeout=config.timeout_limit):
    """
    Run the command in a subprocess and wait for timeout
    time before killing it.
    Errors are recorded and output is recorded"""
    def alarm_handler(signum, frame):
        "Raise the alarm of timeout"
        raise errors.Timeout

    proc = subprocess.Popen(cmd,
                            stderr=subprocess.PIPE,
                            stdout=subprocess.PIPE,
                            shell=True
                            )

    signal.signal(signal.SIGALRM, alarm_handler)
    signal.alarm(timeout)
    try:
        stdoutdata, stderrdata = proc.communicate()
        signal.alarm(0)  # reset the alarm
    except errors.Timeout:
        proc.terminate()
        ret_val = None
        stderrdata = b''
        stdoutdata = b''
    else:
        ret_val = proc.returncode
    return ret_val, stdoutdata.decode(), stderrdata.decode()
