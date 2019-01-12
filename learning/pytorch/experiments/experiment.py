#!/usr/bin/env python

import argparse
import datetime
import os
import subprocess
import sys
import urlparse
from typing import Any, Dict, List, NamedTuple, Optional
import time
import traceback

_DIRNAME = os.path.abspath(os.path.dirname(__file__))
PYTHON = sys.executable

try:
    ITHEMAL_HOME = os.environ['ITHEMAL_HOME']
except:
    # as a backup (e.g. on Alex's computer) set ITHEMAL_HOME as a function of the gitroot
    ITHEMAL_HOME = subprocess.check_output(['git', 'rev-parse', '--show-toplevel'], cwd=_DIRNAME).strip()

PYTORCH_HOME = os.path.join(ITHEMAL_HOME, 'learning', 'pytorch')

EXPERIMENT_BUCKET = 'ithemal-experiments'
DATASET_BUCKET = 'ithemal-datasets'
CHECKPOINT_QUEUE = 'checkpoint_queue'

DEBUG = False

def debug_print(params):
    if DEBUG:
        print(' '.join(params))

def get_s3_url(bucket, path):
    # type: (str, str) -> str
    return urlparse.urlunsplit(['s3', bucket, path, '', ''])

class Experiment(object):
    def __init__(self, name, time, data, params):
        # type: (str, str, str, List[str]) -> None
        self.name = name
        self.time = time
        self.data = os.path.basename(data)
        self.params = params
        self.proc = None # type: Optional[subprocess.Popen]

    def experiment_root_path(self):
        # type: () -> str
        return os.path.join(PYTORCH_HOME, 'saved', self.name, self.time)

    def checkpoint_file_dir(self):
        # type: () -> str
        return os.path.join(self.experiment_root_path(), 'checkpoints')

    def checkpoint_file_name(self, run_time):
        # type: (float) -> str
        return os.path.join(self.checkpoint_file_dir(), '{}.mdl'.format(run_time))

    def get_ithemal_command_root(self):
        # type: () -> List[str]
        return [
            PYTHON, os.path.join(PYTORCH_HOME, 'ithemal', 'run_ithemal.py'),
            '--data', os.path.join(PYTORCH_HOME, 'saved', self.data),
        ]

    def get_params(self):
        # type: () -> List[str]
        base_args = self.get_ithemal_command_root() + [
            'train',
            '--experiment-name', self.name,
            '--experiment-time', self.time,
        ]
        params = base_args + self.params
        return params

    def download_data(self):
        # type: () -> None
        # download the data if not present on this machine
        data_url = get_s3_url(DATASET_BUCKET, '')
        # sync is smarter than cp, but only works on directories: tell it to only sync that one file
        sync_args = ['aws', 's3', 'sync', data_url, os.path.join(PYTORCH_HOME, 'saved'), '--exclude', '*', '--include', self.data]
        debug_print(sync_args)
        subprocess.check_call(sync_args)

    def start_experiment(self):
        # type: () -> None
        self.download_data()
        root = self.experiment_root_path()

        try:
            os.makedirs(root)
        except OSError:
            pass

        params = self.get_params()
        with open(os.path.join(root, 'cmdline'), 'w') as f:
            f.write(' '.join(params))

        debug_print(params)
        self.proc = subprocess.Popen(params, stdout=open(os.path.join(root, 'stdout'), 'w'))

    def enqueue_checkpoints(self, checkpoint_times):
        # type: (List[str]) -> None
        benchmark_checkpoint = os.path.join(
            '${ITHEMAL_HOME}', # whatever ITHEMAL_HOME is on remote machine
            'learning', 'pytorch', 'experiments', 'benchmark_checkpoint.py'
        )

        for checkpoint_time in checkpoint_times:
            command_param = ' '.join([benchmark_checkpoint, self.name, self.time, self.data, checkpoint_time] + self.params)
            params = [
                os.path.join(ITHEMAL_HOME, 'aws', 'command_queue.py'),
                'send', CHECKPOINT_QUEUE, command_param
            ]

            debug_print(params)
            subprocess.call(params, stdout=open('/dev/null', 'w'))

    def run_and_sync(self):
        # type: () -> None

        self.start_experiment()
        proc = self.proc
        if proc is None:
            raise Exception('Process not created!')

        s3_bucket_path_root = os.path.join(self.name, self.time)
        s3_bucket_checkpoint_path = os.path.join(s3_bucket_path_root, 'checkpoints')
        checkpoint_path = self.checkpoint_file_dir()

        try:
            os.makedirs(checkpoint_path)
        except OSError:
            pass

        def sync():
            # type: () -> None

            # sync checkpoints, capturing the new checkpoints and enqueuing them for validation
            params = ['aws', 's3', 'sync', '--no-progress', checkpoint_path, get_s3_url(EXPERIMENT_BUCKET, s3_bucket_checkpoint_path)]
            debug_print(params)
            checkpoints_output = subprocess.check_output(params).strip()
            if checkpoints_output:
                print('Checkpoints Output: "{}", split: "{}"'.format(checkpoints_output, checkpoints_output.strip().split('\n')))
                checkpoint_files = [line.split()[1] for line in checkpoints_output.split('\n')]
                checkpoint_times = [os.path.basename(fname)[:-len('.mdl')] for fname in checkpoint_files]
                self.enqueue_checkpoints(checkpoint_times)

            params = ['aws', 's3', 'sync', self.experiment_root_path(), get_s3_url(EXPERIMENT_BUCKET, s3_bucket_path_root)]
            debug_print(params)
            subprocess.check_call(params)

        while proc.poll() is None:
            sync()
            time.sleep(60)
        sync()

        params = [os.path.join(ITHEMAL_HOME, 'aws', 'ping_slack.py'), 'Experiment {}_{} finished with exit code {}'.format(
            self.name,
            self.time,
            proc.returncode,
        )]
        debug_print(params)
        subprocess.check_call()

def main():
    # type: () -> None
    parser = argparse.ArgumentParser(description='Run experiments, syncing with AWS', prefix_chars='?')
    parser.add_argument('name', help='Name of the experiment to run')
    parser.add_argument('data', help='Datafile to run with (must be on S3)')
    parser.add_argument('rest', nargs='*', help='Remaining arguments passed to Ithemal')
    args = parser.parse_args()

    start_time = datetime.datetime.fromtimestamp(time.time()).isoformat()
    experiment = Experiment(args.name, start_time, args.data, args.rest)
    try:
        experiment.run_and_sync()
    except:
        traceback.print_exc()

        if experiment.proc is not None:
            try:
                print('Terminating Ithemal process!')
                experiment.proc.terminate()
                experiment.proc.wait()
            except KeyboardInterrupt:
                print('Force killing Ithemal')
                experiment.proc.kill()

if __name__ == '__main__':
    main()
