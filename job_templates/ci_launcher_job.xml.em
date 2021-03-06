<?xml version='1.0' encoding='UTF-8'?>
<project>
  <actions/>
  <description>
    Note: The Windows jobs ignore the middleware selection flags.
  </description>
  <keepDependencies>false</keepDependencies>
  <properties>
    <com.sonyericsson.rebuild.RebuildSettings plugin="rebuild@@1.25">
      <autoRebuild>false</autoRebuild>
      <rebuildDisabled>false</rebuildDisabled>
    </com.sonyericsson.rebuild.RebuildSettings>
    <org.jenkinsci.plugins.requeuejob.RequeueJobProperty plugin="jobrequeue@@1.1">
      <requeueJob>true</requeueJob>
    </org.jenkinsci.plugins.requeuejob.RequeueJobProperty>
@(SNIPPET(
    'property_parameter-definition',
    ci_scripts_default_branch=ci_scripts_default_branch,
    default_repos_url=default_repos_url,
    supplemental_repos_url=supplemental_repos_url,
    use_connext_default=use_connext_default,
    disable_connext_static_default=disable_connext_static_default,
    disable_connext_dynamic_default=disable_connext_dynamic_default,
    use_osrf_connext_debs_default=use_osrf_connext_debs_default,
    use_fastrtps_default=use_fastrtps_default,
    use_opensplice_default=use_opensplice_default,
    cmake_build_type=cmake_build_type,
    ament_build_args_default=ament_build_args_default,
    ament_test_args_default=ament_test_args_default,
    enable_c_coverage_default=enable_c_coverage_default,
))@
  </properties>
  <scm class="hudson.scm.NullSCM"/>
  <assignedNode>@(label_expression)</assignedNode>
  <canRoam>false</canRoam>
  <disabled>false</disabled>
  <blockBuildWhenDownstreamBuilding>false</blockBuildWhenDownstreamBuilding>
  <blockBuildWhenUpstreamBuilding>false</blockBuildWhenUpstreamBuilding>
  <triggers/>
  <concurrentBuild>false</concurrentBuild>
  <builders>
    <hudson.plugins.groovy.SystemGroovy plugin="groovy@@2.0">
      <source class="hudson.plugins.groovy.StringSystemScriptSource">
        <script plugin="script-security@@1.27">
          <script>// PREDICT TRIGGERED BUILDS AND GENERATE MARKDOWN FOR BUILD STATUS

import jenkins.model.Jenkins

def predict_build_number(job_name) {
  p = Jenkins.instance.getItemByFullName(job_name)
  if (!p) {
    return 0
  }
  build_number = p.getNextBuildNumber()
  if (p.isInQueue()) {
    // assuming the queued builds don't get cancelled
    for (item in Jenkins.instance.getQueue().getItems()) {
      if (item.task.getName() == job_name) {
        build_number += 1
      }
    }
  }
  return build_number
}

build_numbers = [:]
@[for os_name in os_specific_data.keys()]@
build_numbers["@(os_name)"] = predict_build_number("ci_@(os_name)")
@[end for]@

for (item in build_numbers) {
  name = item.key[0].toUpperCase() + item.key[1..-1].toLowerCase()
  if (name == "Osx") {
    name = "macOS"
  }
  job_name = "ci_${item.key}"
  build_number = item.value
  println "* ${name} [![Build Status](http://ci.ros2.org/buildStatus/icon?job=${job_name}&amp;build=${build_number})](http://ci.ros2.org/job/${job_name}/${build_number}/)"
}
</script>
          <sandbox>false</sandbox>
        </script>
      </source>
    </hudson.plugins.groovy.SystemGroovy>
  </builders>
  <publishers>
@[for os_name, os_data in os_specific_data.items()]@
    <hudson.plugins.parameterizedtrigger.BuildTrigger plugin="parameterized-trigger@@2.33">
      <configs>
        <hudson.plugins.parameterizedtrigger.BuildTriggerConfig>
          <configs>
            <hudson.plugins.parameterizedtrigger.CurrentBuildParameters/>
@[if os_name == 'linux-aarch64']@
            <hudson.plugins.parameterizedtrigger.BooleanParameters>
              <configs>
                <hudson.plugins.parameterizedtrigger.BooleanParameterConfig>
                  <name>CI_USE_CONNEXT</name>
                  <value>false</value>
                </hudson.plugins.parameterizedtrigger.BooleanParameterConfig>
              </configs>
            </hudson.plugins.parameterizedtrigger.BooleanParameters>
@[end if]@
          </configs>
          <projects>@(os_data['job_name'])</projects>
          <condition>SUCCESS</condition>
          <triggerWithNoParameters>false</triggerWithNoParameters>
          <triggerFromChildProjects>false</triggerFromChildProjects>
        </hudson.plugins.parameterizedtrigger.BuildTriggerConfig>
      </configs>
    </hudson.plugins.parameterizedtrigger.BuildTrigger>
@[end for]@
  </publishers>
  <buildWrappers/>
</project>
