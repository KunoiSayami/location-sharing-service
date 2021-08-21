#!/usr/bin/env python3
import base64
import dataclasses
import json
import logging
import signal
import subprocess
import time

logger = logging.getLogger('test')
logger.setLevel(logging.DEBUG)

INTERVAL = 300
STEP_TIMEOUT = 60
running = True


def handler(*args) -> None:
    global running
    logger.info('Receive exit command, please wait current process done')
    running = False


@dataclasses.dataclass
class Row:
    status_code: int
    time_spend: int
    output: str
    request_type: str

    def __str__(self) -> str:
        return f'{self.status_code},{self.time_spend},' \
               f'{base64.b64encode(self.output.encode()).decode()},{self.request_type}\n'


def run_command(arg: list[str]) -> Row:
    time_spend = 0
    p = subprocess.Popen(arg, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    while p.poll() is None and time_spend <= STEP_TIMEOUT:
        time_spend += 1
        time.sleep(1)
    if p.poll() is None:
        # time out
        p.terminate()
        p.kill()
        return Row(130, STEP_TIMEOUT, '', arg[2])
    stdin, stderr = p.communicate()
    return Row(p.returncode, time_spend,
               json.dumps({'stdin': base64.b64encode(stdin).decode(), 'stderr': base64.b64encode(stderr).decode()}),
               arg[2])


def main() -> None:
    signal.signal(signal.SIGINT, handler)
    real_spend = 0
    with open('result.csv', 'a') as fout:
        while running:
            logger.debug('Get gps location')
            fout.write(str(result := run_command(['termux-location', '-p', 'gps'])))
            logger.info('Get gps location done, spend %d, return code %d', result.time_spend, result.status_code)
            real_spend += result.time_spend
            logger.debug('Get network location')
            fout.write(str(result := run_command(['termux-location', '-p', 'network'])))
            logger.info('Get network location done, spend %d, return code %d', result.time_spend, result.status_code)
            real_spend += result.time_spend
            logger.debug('Get passive location')
            fout.write(str(result := run_command(['termux-location', '-p', 'passive'])))
            logger.info('Get passive location done, spend %d, return code %d', result.time_spend, result.status_code)
            if not running:
                break
            need_break = INTERVAL - real_spend - result.time_spend
            logger.info('Should wait %d, sleeping...', need_break)
            real_spend = 0
            while running and need_break > 0:
                need_break -= 1
                time.sleep(1)


if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG,
                        format='%(asctime)s - %(levelname)s - %(funcName)s - %(lineno)d - %(message)s')
    main()


