import lttngust
import logging
import time
import argparse

parser = argparse.ArgumentParser(description='Python tracing example.')
parser.add_argument('-i', '--iterations', type=int, help='The number of loop iterations', required=True)

args = parser.parse_args()
args.iterations

def example(iteration):
    ch = logging.StreamHandler()
    ch.setLevel(logging.DEBUG)

    logger = logging.getLogger('pello')
    logger.addHandler(ch)

    for i in range(iteration):
        logger.debug('debug message')
        logger.info('info message')
        logger.warn('warn message')
        logger.error('error message')
        logger.critical('critical message')


if __name__ == '__main__':
    example(args.iterations)
