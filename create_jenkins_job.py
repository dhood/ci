#!/usr/bin/env python3

# Copyright 2015 Open Source Robotics Foundation, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import argparse
import collections
import os
import sys

try:
    import ros_buildfarm  # noqa
except ImportError:
    sys.exit("Could not import ros_buildfarm, please add to the PYTHONPATH.")

try:
    import jenkinsapi  # noqa
except ImportError:
    sys.exit("Could not import jenkinsapi, please install it with pip or apt-get.")

from ros_buildfarm.jenkins import configure_job
from ros_buildfarm.jenkins import connect
from ros_buildfarm.templates import expand_template
try:
    from ros_buildfarm.templates import template_prefix_path
except ImportError:
    sys.exit("Could not import symbol from ros_buildfarm, please update ros_buildfarm.")

DEFAULT_REPOS_URL = 'https://raw.githubusercontent.com/ros2/ros2/master/ros2.repos'

template_prefix_path[:] = \
    [os.path.join(os.path.abspath(os.path.dirname(__file__)), 'job_templates')]


def main(argv=None):
    if argv is None:
        argv = sys.argv[1:]
    parser = argparse.ArgumentParser(description="Creates the ros2 jobs on Jenkins")
    parser.add_argument(
        '--jenkins-url', '-u', default='http://ci.ros2.org',
        help="Url of the jenkins server to which the job should be added")
    parser.add_argument(
        '--ci-scripts-repository', default='git@github.com:ros2/ci.git',
        help="repository from which ci scripts should be cloned"
    )
    parser.add_argument(
        '--ci-scripts-default-branch', default='master',
        help="default branch of the ci repository to get ci scripts from (this is a job parameter)"
    )
    parser.add_argument(
        '--commit', action='store_true',
        help='Actually modify the Jenkis jobs instead of only doing a dry run',
    )
    args = parser.parse_args(argv)

    data = {
        'ci_scripts_repository': args.ci_scripts_repository,
        'ci_scripts_default_branch': args.ci_scripts_default_branch,
        'default_repos_url': DEFAULT_REPOS_URL,
        'supplemental_repos_url': '',
        'time_trigger_spec': '',
        'mailer_recipients': '',
        'use_connext_default': 'true',
        'disable_connext_static_default': 'false',
        'disable_connext_dynamic_default': 'true',
        'use_osrf_connext_debs_default': 'false',
        'use_fastrtps_default': 'true',
        'use_opensplice_default': 'false',
        'ament_build_args_default': '--parallel --cmake-args -DSECURITY=ON --',
        'ament_test_args_default': '--retest-until-pass 10',
        'enable_c_coverage_default': 'false',
        'dont_notify_every_unstable_build': 'false',
        'turtlebot_demo': False,
        'build_timeout_mins': 0,
    }

    jenkins = connect(args.jenkins_url)

    os_configs = {
        'linux': {
            'label_expression': 'linux',
            'shell_type': 'Shell',
        },
        'osx': {
            'label_expression': 'osx_slave',
            'shell_type': 'Shell',
            # the current OS X slave can't handle  git@github urls
            'ci_scripts_repository': args.ci_scripts_repository.replace(
                'git@github.com:', 'https://github.com/'),
        },
        'windows': {
            'label_expression': 'windows_slave',
            'shell_type': 'BatchFile',
        },
        'linux-aarch64': {
            'label_expression': 'linux_aarch64',
            'shell_type': 'Shell',
            'use_connext_default': 'false',
        },
    }

    jenkins_kwargs = {}
    if not args.commit:
        jenkins_kwargs['dry_run'] = True

    # configure os specific jobs
    for os_name in sorted(os_configs.keys()):
        job_data = dict(data)
        job_data['os_name'] = os_name
        job_data.update(os_configs[os_name])

        # configure manual triggered job
        job_name = 'ci_' + os_name
        job_data['cmake_build_type'] = 'None'
        job_config = expand_template('ci_job.xml.em', job_data)
        configure_job(jenkins, job_name, job_config, **jenkins_kwargs)

        # configure a manual version of the packaging job
        job_name = 'ci_packaging_' + os_name
        job_data['cmake_build_type'] = 'RelWithDebInfo'
        job_data['test_bridge_default'] = 'true'
        job_config = expand_template('packaging_job.xml.em', job_data)
        configure_job(jenkins, job_name, job_config, **jenkins_kwargs)

        # all following jobs are triggered nightly with email notification
        job_data['time_trigger_spec'] = '30 7 * * *'
        # for now, skip emailing about Windows failures
        job_data['mailer_recipients'] = 'ros2-buildfarm@googlegroups.com'

        # configure packaging job
        job_name = 'packaging_' + os_name
        job_data['cmake_build_type'] = 'RelWithDebInfo'
        job_data['test_bridge_default'] = 'true'
        job_config = expand_template('packaging_job.xml.em', job_data)
        configure_job(jenkins, job_name, job_config, **jenkins_kwargs)

        # keeping the paths on Windows shorter
        os_name = os_name.replace('windows', 'win')
        # configure nightly triggered job
        job_name = 'nightly_' + os_name + '_debug'
        if os_name == 'win':
            job_name = job_name[0:-2]
        job_data['cmake_build_type'] = 'Debug'
        job_config = expand_template('ci_job.xml.em', job_data)
        configure_job(jenkins, job_name, job_config, **jenkins_kwargs)

        # configure nightly coverage job on x86 Linux only
        if os_name == 'linux':
            job_name = 'nightly_' + os_name + '_coverage'
            job_data['cmake_build_type'] = 'Debug'
            job_data['enable_c_coverage_default'] = 'true'
            job_config = expand_template('ci_job.xml.em', job_data)
            configure_job(jenkins, job_name, job_config, **jenkins_kwargs)
            job_data['enable_c_coverage_default'] = 'false'

        # configure nightly triggered job
        job_name = 'nightly_' + os_name + '_release'
        if os_name == 'win':
            job_name = job_name[0:-4]
        job_data['cmake_build_type'] = 'Release'
        job_config = expand_template('ci_job.xml.em', job_data)
        configure_job(jenkins, job_name, job_config, **jenkins_kwargs)

        # configure nightly triggered job with repeated testing
        job_name = 'nightly_' + os_name + '_repeated'
        if os_name == 'win':
            job_name = job_name[0:-5]
        job_data['time_trigger_spec'] = '30 7 * * *'
        job_data['cmake_build_type'] = 'None'
        job_data['ament_test_args_default'] = '--retest-until-fail 20 --ctest-args -LE linter --'
        job_config = expand_template('ci_job.xml.em', job_data)
        configure_job(jenkins, job_name, job_config, **jenkins_kwargs)

    # configure the launch job
    os_specific_data = collections.OrderedDict()
    for os_name in sorted(os_configs.keys()):
        os_specific_data[os_name] = dict(data)
        os_specific_data[os_name].update(os_configs[os_name])
        os_specific_data[os_name]['job_name'] = 'ci_' + os_name
    job_data = dict(data)
    job_data['ci_scripts_default_branch'] = args.ci_scripts_default_branch
    job_data['label_expression'] = 'master'
    job_data['os_specific_data'] = os_specific_data
    job_data['cmake_build_type'] = 'None'
    job_config = expand_template('ci_launcher_job.xml.em', job_data)
    configure_job(jenkins, 'ci_launcher', job_config, **jenkins_kwargs)

    # Run the turtlebot job on Linux only for now.
    for os_name in ['linux', 'linux-aarch64']:
        turtlebot_job_data = dict(data)
        turtlebot_job_data['os_name'] = os_name
        turtlebot_job_data.update(os_configs[os_name])
        turtlebot_job_data['turtlebot_demo'] = True
        # Use a turtlebot2_demo-specific repos file by default.
        turtlebot_job_data['supplemental_repos_url'] = 'https://raw.githubusercontent.com/ros2/turtlebot2_demo/master/turtlebot2_demo.repos'
        turtlebot_job_data['cmake_build_type'] = 'None'
        job_config = expand_template('ci_job.xml.em', turtlebot_job_data)
        configure_job(jenkins, 'ci_turtlebot-demo_%s'%(os_name), job_config, **jenkins_kwargs)


if __name__ == '__main__':
    main()
