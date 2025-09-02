#!/usr/bin/env python3
"""
Fixed Mock EMR Cluster for Testing EMR Monitoring Tool

This creates mock Spark History Server (port 18080) and YARN ResourceManager (port 8088)
endpoints with realistic test data to simulate a real EMR cluster.

Usage:
    python mock_emr_cluster_fixed.py
"""

import json
import threading
import time
from datetime import datetime, timedelta
from flask import Flask, jsonify, request
from werkzeug.serving import make_server
import random
import uuid


# Mock data generators
def generate_app_id():
    timestamp = int(time.time())
    return f"application_{timestamp}_{random.randint(1000, 9999)}"


def generate_container_id(app_id):
    return app_id.replace('application_', 'container_') + f"_01_{random.randint(100000, 999999)}"


def generate_mock_log_content(app_type="spark"):
    base_logs = {
        "driver": """24/01/15 10:30:45 INFO SparkContext: Running Spark version 3.2.1
24/01/15 10:30:45 INFO ResourceUtils: ==============================================================
24/01/15 10:30:45 INFO ResourceUtils: No custom resources configured for spark.driver.
24/01/15 10:30:45 INFO SparkContext: Submitted application: Mock Spark Application
24/01/15 10:30:46 INFO SecurityManager: Changing view acls to: hadoop
24/01/15 10:30:46 INFO SecurityManager: Changing modify acls to: hadoop
24/01/15 10:30:46 INFO SecurityManager: SecurityManager: authentication disabled; ui acls disabled
24/01/15 10:30:47 INFO Utils: Successfully started service 'sparkDriver' on port 35757.
24/01/15 10:30:47 INFO SparkEnv: Registering MapOutputTracker
24/01/15 10:30:47 INFO SparkContext: Starting job: collect at MockJob.scala:25
24/01/15 10:30:47 INFO DAGScheduler: Got job 0 (collect at MockJob.scala:25) with 2 output partitions
24/01/15 10:30:47 INFO DAGScheduler: Final stage: ResultStage 0 (collect at MockJob.scala:25)
24/01/15 10:30:47 INFO DAGScheduler: Job 0 finished: collect at MockJob.scala:25, took 1.234567 s
24/01/15 10:30:48 INFO SparkContext: Successfully stopped SparkContext""",

        "executor": """24/01/15 10:30:48 INFO CoarseGrainedExecutorBackend: Started daemon with process name: 12345@ip-172-31-1-100
24/01/15 10:30:48 INFO SignalUtils: Registered signal handler for TERM
24/01/15 10:30:48 INFO SignalUtils: Registered signal handler for HUP  
24/01/15 10:30:48 INFO SignalUtils: Registered signal handler for INT
24/01/15 10:30:49 INFO SecurityManager: Changing view acls to: hadoop
24/01/15 10:30:49 INFO SecurityManager: SecurityManager: authentication disabled; ui acls disabled
24/01/15 10:30:49 INFO TransportClientFactory: Successfully created connection to /172.31.1.50:35757 after 45 ms
24/01/15 10:30:49 INFO CoarseGrainedExecutorBackend: Successfully registered with driver
24/01/15 10:30:49 INFO Executor: Starting executor ID 1 on host 172.31.1.100
24/01/15 10:30:49 INFO Utils: Successfully started service 'org.apache.spark.network.netty.NettyBlockTransferService' on port 33333.
24/01/15 10:30:50 INFO Executor: Using REPL class URI: spark://172.31.1.50:35757/classes
24/01/15 10:30:50 INFO TaskSetManager: Starting task 0.0 in stage 0.0 (TID 0, 172.31.1.100, executor 1, partition 0, PROCESS_LOCAL, 4916 bytes)
24/01/15 10:30:50 INFO Executor: Running task 0.0 in stage 0.0 (TID 0)
24/01/15 10:30:51 INFO Executor: Finished task 0.0 in stage 0.0 (TID 0). 1024 bytes result sent to driver""",

        "container": """Log Type: stdout
Log Length: 15420

24/01/15 10:30:45 INFO YarnCoarseGrainedExecutorBackend: YARN executor launch context:
  env:
    CLASSPATH -> {{PWD}}<CPS>{{PWD}}/__spark_conf__<CPS>/usr/lib/hadoop/lib/*<CPS>/usr/lib/hadoop/*
    SPARK_YARN_STAGING_DIR -> .sparkStaging/application_1705310445123_0001
    SPARK_USER -> hadoop
  command:
    {{JAVA_HOME}}/bin/java -server -Xmx2048m -Djava.io.tmpdir={{PWD}}/tmp org.apache.spark.executor.YarnCoarseGrainedExecutorBackend --driver-url spark://CoarseGrainedScheduler@172.31.1.50:35757 --executor-id 1 --hostname 172.31.1.100 --cores 2 --app-id application_1705310445123_0001 --resourceProfileId 0 --user-class-path file:{{PWD}}/__app__.jar

Container exited with a non-zero exit code 0. Last 4096 bytes of stderr :
SLF4J: Class path contains multiple SLF4J bindings.""",

        "yarn": """2024-01-15 10:30:45,123 INFO org.apache.hadoop.yarn.server.resourcemanager.ApplicationMasterService: Registering app attempt : appattempt_1705310445123_0001_000001
2024-01-15 10:30:45,124 INFO org.apache.hadoop.yarn.server.resourcemanager.rmapp.attempt.RMAppAttemptImpl: appattempt_1705310445123_0001_000001 State change from NEW to SUBMITTED
2024-01-15 10:30:45,125 INFO org.apache.hadoop.yarn.server.resourcemanager.scheduler.capacity.CapacityScheduler: Application Attempt appattempt_1705310445123_0001_000001 is done. finalState=FINISHED
2024-01-15 10:30:45,126 INFO org.apache.hadoop.yarn.server.resourcemanager.rmapp.RMAppImpl: Application application_1705310445123_0001 finished with state FINISHED"""
    }

    return base_logs.get(app_type, base_logs["driver"])


# Mock applications data
def generate_mock_applications():
    apps = []
    statuses = ["FINISHED", "RUNNING", "FAILED", "KILLED"]
    app_types = ["Spark", "Jupyter Notebook", "PySpark Shell", "Scala Application"]
    users = ["data-scientist-1", "analyst-2", "ml-engineer-3", "hadoop"]

    for i in range(12):  # Generate 12 mock applications
        app_id = generate_app_id()
        status = random.choice(statuses)
        start_time = datetime.now() - timedelta(hours=random.randint(1, 48))

        if status == "FINISHED":
            end_time = start_time + timedelta(minutes=random.randint(5, 120))
            duration = int((end_time - start_time).total_seconds() * 1000)
        elif status == "FAILED":
            end_time = start_time + timedelta(minutes=random.randint(1, 30))
            duration = int((end_time - start_time).total_seconds() * 1000)
        else:
            end_time = None
            duration = int((datetime.now() - start_time).total_seconds() * 1000)

        app = {
            "id": app_id,
            "name": f"{random.choice(app_types)} - {random.choice(['Data Processing', 'ML Training', 'ETL Job', 'Analytics'])}",
            "sparkVersion": "3.2.1",
            "sparkUser": random.choice(users),
            "startTime": start_time.strftime("%Y-%m-%dT%H:%M:%S.%fZ"),
            "endTime": end_time.strftime("%Y-%m-%dT%H:%M:%S.%fZ") if end_time else None,
            "duration": duration,
            "attempts": [{
                "startTime": start_time.strftime("%Y-%m-%dT%H:%M:%S.%fZ"),
                "endTime": end_time.strftime("%Y-%m-%dT%H:%M:%S.%fZ") if end_time else None,
                "duration": duration,
                "sparkUser": random.choice(users),
                "completed": status in ["FINISHED", "FAILED", "KILLED"]
            }]
        }
        apps.append(app)

    return apps


# Generate mock YARN applications
def generate_mock_yarn_applications():
    yarn_apps = []
    states = ["FINISHED", "RUNNING", "FAILED", "KILLED", "ACCEPTED"]

    for i in range(8):
        app_id = generate_app_id()
        state = random.choice(states)
        start_time = int((datetime.now() - timedelta(hours=random.randint(1, 24))).timestamp() * 1000)

        yarn_app = {
            "id": app_id,
            "user": random.choice(["hadoop", "data-scientist-1", "analyst-2"]),
            "name": f"Spark Application {i + 1}",
            "queue": "default",
            "state": state,
            "finalStatus": "SUCCEEDED" if state == "FINISHED" else ("FAILED" if state == "FAILED" else "UNDEFINED"),
            "progress": 100.0 if state == "FINISHED" else (0.0 if state == "ACCEPTED" else random.uniform(10.0, 95.0)),
            "trackingUI": "History" if state == "FINISHED" else "ApplicationMaster",
            "trackingUrl": f"http://localhost:18080/history/{app_id}",
            "applicationType": "SPARK",
            "applicationTags": "",
            "startedTime": start_time,
            "finishedTime": start_time + random.randint(300000, 7200000) if state == "FINISHED" else 0,
            "elapsedTime": random.randint(300000, 7200000),
            "amContainerLogs": f"http://localhost:8042/node/containerlogs/container_{app_id.split('_')[1]}_{app_id.split('_')[2]}_01_000001/hadoop",
            "amHostHttpAddress": "172.31.1.50:8042",
            "allocatedMB": random.randint(2048, 16384),
            "allocatedVCores": random.randint(2, 8),
            "runningContainers": random.randint(0, 5) if state == "RUNNING" else 0,
            "memorySeconds": random.randint(1000000, 10000000),
            "vcoreSeconds": random.randint(5000, 50000),
            "preemptedResourceMB": 0,
            "preemptedResourceVCores": 0,
            "numNonAMContainerPreempted": 0,
            "numAMContainerPreempted": 0
        }
        yarn_apps.append(yarn_app)

    return yarn_apps


# Create Flask apps for mock services
def create_spark_history_server():
    app = Flask(__name__)
    mock_applications = generate_mock_applications()

    @app.route('/api/v1/applications')
    def get_applications():
        status_filter = request.args.get('status')
        if status_filter == 'running':
            running_apps = [app for app in mock_applications if not app['attempts'][0]['completed']]
            return jsonify(running_apps)
        return jsonify(mock_applications)

    @app.route('/api/v1/applications/<app_id>')
    def get_application(app_id):
        app = next((app for app in mock_applications if app['id'] == app_id), None)
        if app:
            return jsonify(app)
        return jsonify({"error": "Application not found"}), 404

    @app.route('/api/v1/applications/<app_id>/executors')
    def get_executors(app_id):
        # Generate mock executors
        num_executors = random.randint(2, 6)
        executors = []

        # Driver executor
        executors.append({
            "id": "driver",
            "hostPort": "172.31.1.50:35757",
            "isActive": True,
            "rddBlocks": 0,
            "memoryUsed": random.randint(100, 500) * 1024 * 1024,  # MB in bytes
            "diskUsed": 0,
            "totalCores": 2,
            "maxTasks": 2,
            "activeTasks": 0,
            "failedTasks": 0,
            "completedTasks": random.randint(10, 50),
            "totalTasks": random.randint(10, 50),
            "totalDuration": random.randint(10000, 60000),
            "totalGCTime": random.randint(1000, 5000),
            "totalInputBytes": random.randint(1024 * 1024, 100 * 1024 * 1024),
            "totalShuffleRead": random.randint(0, 50 * 1024 * 1024),
            "totalShuffleWrite": random.randint(0, 50 * 1024 * 1024),
            "maxMemory": 2 * 1024 * 1024 * 1024,  # 2GB
            "addTime": "2024-01-15T10:30:45.123GMT",
            "executorLogs": {}
        })

        # Regular executors
        for i in range(1, num_executors):
            executors.append({
                "id": str(i),
                "hostPort": f"172.31.1.{100 + i}:33333",
                "isActive": random.choice([True, False]),
                "rddBlocks": random.randint(0, 10),
                "memoryUsed": random.randint(200, 800) * 1024 * 1024,
                "diskUsed": random.randint(0, 100) * 1024 * 1024,
                "totalCores": random.randint(2, 4),
                "maxTasks": random.randint(2, 4),
                "activeTasks": random.randint(0, 2),
                "failedTasks": random.randint(0, 3),
                "completedTasks": random.randint(20, 100),
                "totalTasks": random.randint(20, 100),
                "totalDuration": random.randint(30000, 180000),
                "totalGCTime": random.randint(2000, 10000),
                "totalInputBytes": random.randint(10 * 1024 * 1024, 500 * 1024 * 1024),
                "totalShuffleRead": random.randint(0, 100 * 1024 * 1024),
                "totalShuffleWrite": random.randint(0, 100 * 1024 * 1024),
                "maxMemory": random.randint(2, 8) * 1024 * 1024 * 1024,
                "addTime": "2024-01-15T10:30:45.123GMT",
                "executorLogs": {}
            })

        return jsonify(executors)

    @app.route('/api/v1/applications/<app_id>/executors/<executor_id>/logs')
    def get_executor_logs(app_id, executor_id):
        log_type = "driver" if executor_id == "driver" else "executor"
        return generate_mock_log_content(log_type)

    @app.route('/api/v1/applications/<app_id>/jobs')
    def get_jobs(app_id):
        jobs = []
        for i in range(random.randint(1, 5)):
            jobs.append({
                "jobId": i,
                "name": f"Job {i}",
                "description": f"Mock job {i} for application {app_id}",
                "submissionTime": "2024-01-15T10:30:45.123GMT",
                "completionTime": "2024-01-15T10:31:45.123GMT",
                "stageIds": [i * 2, i * 2 + 1],
                "status": random.choice(["SUCCEEDED", "FAILED", "RUNNING"]),
                "numTasks": random.randint(10, 100),
                "numActiveTasks": 0,
                "numCompletedTasks": random.randint(10, 100),
                "numSkippedTasks": 0,
                "numFailedTasks": random.randint(0, 5),
                "numKilledTasks": 0,
                "numActiveStages": 0,
                "numCompletedStages": 2,
                "numSkippedStages": 0,
                "numFailedStages": 0
            })
        return jsonify(jobs)

    @app.route('/api/v1/applications/<app_id>/stages')
    def get_stages(app_id):
        stages = []
        for i in range(random.randint(2, 8)):
            stages.append({
                "status": random.choice(["COMPLETE", "ACTIVE", "FAILED"]),
                "stageId": i,
                "attemptId": 0,
                "numTasks": random.randint(1, 20),
                "numActiveTasks": 0,
                "numCompleteTasks": random.randint(1, 20),
                "numFailedTasks": 0,
                "numKilledTasks": 0,
                "numCompletedIndices": random.randint(1, 20),
                "executorRunTime": random.randint(1000, 30000),
                "executorCpuTime": random.randint(500, 15000),
                "submissionTime": "2024-01-15T10:30:45.123GMT",
                "firstTaskLaunchedTime": "2024-01-15T10:30:45.456GMT",
                "completionTime": "2024-01-15T10:31:15.789GMT",
                "inputBytes": random.randint(1024 * 1024, 100 * 1024 * 1024),
                "inputRecords": random.randint(1000, 1000000),
                "outputBytes": random.randint(1024 * 1024, 100 * 1024 * 1024),
                "outputRecords": random.randint(1000, 1000000),
                "shuffleReadBytes": random.randint(0, 50 * 1024 * 1024),
                "shuffleReadRecords": random.randint(0, 500000),
                "shuffleWriteBytes": random.randint(0, 50 * 1024 * 1024),
                "shuffleWriteRecords": random.randint(0, 500000),
                "memoryBytesSpilled": random.randint(0, 10 * 1024 * 1024),
                "diskBytesSpilled": random.randint(0, 10 * 1024 * 1024),
                "name": f"Stage {i}",
                "details": f"Mock stage {i} details",
                "schedulingPool": "default",
                "rddIds": [i, i + 1],
                "accumulatorUpdates": [],
                "tasks": None,
                "executorSummary": {}
            })
        return jsonify(stages)

    @app.route('/api/v1/applications/<app_id>/environment')
    def get_environment(app_id):
        return jsonify({
            "runtime": {
                "javaVersion": "1.8.0_372 (Amazon.com Inc.)",
                "javaHome": "/usr/lib/jvm/java-1.8.0-amazon-corretto.x86_64",
                "scalaVersion": "version 2.12.15"
            },
            "sparkProperties": [
                ["spark.serializer", "org.apache.spark.serializer.KryoSerializer"],
                ["spark.driver.host", "172.31.1.50"],
                ["spark.eventLog.enabled", "true"],
                ["spark.driver.port", "35757"],
                ["spark.app.name", "Mock Spark Application"],
                ["spark.master", "yarn"],
                ["spark.driver.memory", "2g"],
                ["spark.executor.memory", "4g"],
                ["spark.executor.cores", "2"],
                ["spark.sql.adaptive.enabled", "true"]
            ],
            "systemProperties": [
                ["java.runtime.name", "OpenJDK Runtime Environment"],
                ["java.vm.version", "25.372-b07"],
                ["java.vm.vendor", "Amazon.com Inc."],
                ["os.name", "Linux"],
                ["user.name", "hadoop"]
            ],
            "classpathEntries": [
                ["/usr/lib/spark/conf/", "System Classpath"],
                ["/usr/lib/spark/jars/spark-core_2.12-3.2.1.jar", "System Classpath"]
            ]
        })

    return app


def create_yarn_resource_manager():
    app = Flask(__name__)
    mock_yarn_apps = generate_mock_yarn_applications()

    @app.route('/ws/v1/cluster/info')
    def get_cluster_info():
        return jsonify({
            "clusterInfo": {
                "id": 1705310445123,
                "startedOn": int((datetime.now() - timedelta(days=7)).timestamp() * 1000),
                "state": "STARTED",
                "haState": "ACTIVE",
                "resourceManagerVersion": "3.3.1-amzn-1",
                "resourceManagerBuildVersion": "3.3.1-amzn-1 from unknown by ec2-user on 2023-06-15T10:13Z",
                "resourceManagerVersionBuiltOn": "2023-06-15T10:13Z",
                "hadoopVersion": "3.3.1-amzn-1",
                "hadoopBuildVersion": "3.3.1-amzn-1 from unknown by ec2-user on 2023-06-15T10:13Z",
                "hadoopVersionBuiltOn": "2023-06-15T10:13Z",
                "haZooKeeperConnectionState": "ResourceManager HA is not enabled.",
                "rmStateStoreName": "org.apache.hadoop.yarn.server.resourcemanager.recovery.FileSystemRMStateStore",
                "crossPlatform": True
            }
        })

    @app.route('/ws/v1/cluster/metrics')
    def get_cluster_metrics():
        total_mb = 32768
        used_mb = random.randint(8192, 24576)
        available_mb = total_mb - used_mb
        allocated_mb = random.randint(used_mb - 2048, used_mb)
        reserved_mb = random.randint(0, 1024)

        total_cores = 16
        used_cores = random.randint(4, 12)
        available_cores = total_cores - used_cores
        allocated_cores = random.randint(used_cores - 2, used_cores)
        reserved_cores = random.randint(0, 2)

        running_apps = random.randint(2, 8)
        pending_apps = random.randint(0, 3)
        completed_apps = random.randint(50, 200)
        failed_apps = random.randint(2, 15)
        killed_apps = random.randint(0, 5)

        return jsonify({
            "clusterMetrics": {
                "appsSubmitted": completed_apps + failed_apps + killed_apps + running_apps,
                "appsCompleted": completed_apps,
                "appsPending": pending_apps,
                "appsRunning": running_apps,
                "appsFailed": failed_apps,
                "appsKilled": killed_apps,
                "reservedMB": reserved_mb,
                "availableMB": available_mb,
                "allocatedMB": allocated_mb,
                "reservedVirtualCores": reserved_cores,
                "availableVirtualCores": available_cores,
                "allocatedVirtualCores": allocated_cores,
                "containersAllocated": random.randint(5, 20),
                "containersReserved": reserved_cores,
                "containersPending": random.randint(0, 3),
                "totalMB": total_mb,
                "totalVirtualCores": total_cores,
                "totalNodes": 4,
                "lostNodes": random.randint(0, 1),
                "unhealthyNodes": random.randint(0, 1),
                "decommissioningNodes": 0,
                "decommissionedNodes": 0,
                "rebootedNodes": 0,
                "activeNodes": 4 - random.randint(0, 1)
            }
        })

    @app.route('/ws/v1/cluster/nodes')
    def get_cluster_nodes():
        nodes = []
        node_types = [
            {"hostname": "ip-172-31-1-50", "type": "master", "cores": 4, "memory": 16384},
            {"hostname": "ip-172-31-1-51", "type": "core", "cores": 4, "memory": 8192},
            {"hostname": "ip-172-31-1-52", "type": "core", "cores": 4, "memory": 8192},
            {"hostname": "ip-172-31-1-53", "type": "task", "cores": 2, "memory": 4096}
        ]

        for i, node_info in enumerate(node_types):
            used_memory = random.randint(1024, node_info["memory"] - 1024)
            used_cores = random.randint(0, node_info["cores"] - 1)

            nodes.append({
                "rack": f"/rack-{i + 1}",
                "state": random.choice(["RUNNING", "RUNNING", "RUNNING", "UNHEALTHY"]) if i > 0 else "RUNNING",
                "id": f"{node_info['hostname']}:8041",
                "nodeId": f"{node_info['hostname']}:8041",
                "nodeHostName": node_info["hostname"],
                "nodeHTTPAddress": f"{node_info['hostname']}:8042",
                "lastHealthUpdate": int(time.time() * 1000),
                "version": "3.3.1",
                "healthReport": "",
                "numContainers": random.randint(1, 5),
                "usedMemoryMB": used_memory,
                "availMemoryMB": node_info["memory"] - used_memory,
                "usedVirtualCores": used_cores,
                "availVirtualCores": node_info["cores"] - used_cores,
                "resourceUtilization": {
                    "nodePhysicalMemoryMB": node_info["memory"],
                    "nodeVirtualMemoryMB": node_info["memory"] * 2,
                    "nodeCPUUsage": random.uniform(10.0, 80.0),
                    "aggregatedContainersPhysicalMemoryMB": used_memory,
                    "aggregatedContainersVirtualMemoryMB": used_memory * 1.2
                }
            })

        return jsonify({
            "nodes": {
                "node": nodes
            }
        })

    @app.route('/ws/v1/cluster/scheduler')
    def get_scheduler_info():
        return jsonify({
            "scheduler": {
                "schedulerInfo": {
                    "type": "capacityScheduler",
                    "capacity": 100.0,
                    "usedCapacity": random.uniform(30.0, 80.0),
                    "maxCapacity": 100.0,
                    "queueName": "root",
                    "queues": {
                        "queue": [
                            {
                                "queueName": "default",
                                "capacity": 100.0,
                                "usedCapacity": random.uniform(20.0, 70.0),
                                "maxCapacity": 100.0,
                                "absoluteCapacity": 100.0,
                                "absoluteUsedCapacity": random.uniform(20.0, 70.0),
                                "absoluteMaxCapacity": 100.0,
                                "maxApplications": 10000,
                                "maxApplicationsPerUser": 10000,
                                "maxActiveApplications": 1,
                                "maxActiveApplicationsPerUser": 1,
                                "numApplications": random.randint(2, 10),
                                "numPendingApplications": random.randint(0, 2),
                                "numContainers": random.randint(5, 20),
                                "users": {
                                    "user": [
                                        {
                                            "username": "hadoop",
                                            "resourcesUsed": {
                                                "memory": random.randint(2048, 8192),
                                                "vCores": random.randint(2, 8)
                                            },
                                            "numPendingApplications": 0,
                                            "numActiveApplications": random.randint(1, 3)
                                        }
                                    ]
                                },
                                "resourcesUsed": {
                                    "memory": random.randint(8192, 16384),
                                    "vCores": random.randint(4, 12)
                                },
                                "state": "RUNNING",
                                "type": "capacitySchedulerLeafQueueInfo"
                            }
                        ]
                    }
                }
            }
        })

    @app.route('/ws/v1/cluster/apps')
    def get_applications():
        states = request.args.get('states', '').split(',') if request.args.get('states') else []
        limit = int(request.args.get('limit', 100))

        apps = mock_yarn_apps
        if states and states != ['']:
            apps = [app for app in apps if app['state'] in states]

        apps = apps[:limit]

        return jsonify({
            "apps": {
                "app": apps
            }
        })

    @app.route('/ws/v1/cluster/apps/<app_id>')
    def get_application(app_id):
        app = next((app for app in mock_yarn_apps if app['id'] == app_id), None)
        if app:
            return jsonify({"app": app})
        return jsonify({"error": "Application not found"}), 404

    @app.route('/ws/v1/cluster/apps/<app_id>/appattempts')
    def get_app_attempts(app_id):
        attempt_id = f"appattempt_{app_id.split('_')[1]}_{app_id.split('_')[2]}_000001"
        return jsonify({
            "appAttempts": {
                "appAttempt": [{
                    "id": 1,
                    "nodeId": "172.31.1.50:8041",
                    "nodeHttpAddress": "172.31.1.50:8042",
                    "logsLink": f"http://172.31.1.50:8042/node/containerlogs/container_{app_id.split('_')[1]}_{app_id.split('_')[2]}_01_000001/hadoop",
                    "containerId": f"container_{app_id.split('_')[1]}_{app_id.split('_')[2]}_01_000001",
                    "startTime": int((datetime.now() - timedelta(hours=2)).timestamp() * 1000),
                    "finishedTime": int((datetime.now() - timedelta(hours=1)).timestamp() * 1000),
                    "appAttemptId": attempt_id
                }]
            }
        })

    @app.route('/ws/v1/cluster/apps/<app_id>/appattempts/<attempt_id>/containers')
    def get_containers(app_id, attempt_id):
        containers = []
        num_containers = random.randint(2, 5)

        for i in range(num_containers):
            container_id = f"container_{app_id.split('_')[1]}_{app_id.split('_')[2]}_01_{str(i + 1).zfill(6)}"
            containers.append({
                "containerId": container_id,
                "allocatedMB": random.randint(2048, 8192),
                "allocatedVCores": random.randint(1, 4),
                "assignedNodeId": f"172.31.1.{50 + i}:8041",
                "priority": 0,
                "startedTime": int((datetime.now() - timedelta(hours=2)).timestamp() * 1000),
                "finishedTime": int((datetime.now() - timedelta(hours=1)).timestamp() * 1000),
                "elapsedTime": random.randint(300000, 3600000),
                "logUrl": f"http://172.31.1.{50 + i}:8042/node/containerlogs/{container_id}/hadoop",
                "containerExitStatus": 0,
                "containerState": "COMPLETE",
                "nodeHttpAddress": f"172.31.1.{50 + i}:8042"
            })

        return jsonify({
            "containers": {
                "container": containers
            }
        })

    @app.route('/ws/v1/cluster/apps/<app_id>/state', methods=['PUT'])
    def kill_application(app_id):
        # Mock killing an application
        app = next((app for app in mock_yarn_apps if app['id'] == app_id), None)
        if app:
            app['state'] = 'KILLED'
            app['finalStatus'] = 'KILLED'
            return jsonify({"state": "KILLED"})
        return jsonify({"error": "Application not found"}), 404

    return app


def create_node_manager():
    """Create mock NodeManager for container logs"""
    app = Flask(__name__)

    @app.route('/ws/v1/node/containers/<container_id>/logs/stdout')
    def get_container_stdout(container_id):
        return generate_mock_log_content("container")

    @app.route('/ws/v1/node/containers/<container_id>/logs/stderr')
    def get_container_stderr(container_id):
        stderr_content = """24/01/15 10:30:45 WARN YarnSchedulerBackend$YarnSchedulerEndpoint: Attempted to request executors before the AM has registered!
24/01/15 10:30:46 WARN ObjectStore: Failed to get database global_temp, returning NoSuchObjectException
24/01/15 10:30:47 WARN ObjectStore: Version information not found in metastore. hive.metastore.schema.verification is not enabled so recording the schema version 2.3.0
24/01/15 10:30:48 WARN SessionState: METASTORE_FILTER_HOOK will be ignored, since hive.security.authorization.manager is set to instance of HiveAuthorizerFactory.
SLF4J: Class path contains multiple SLF4J bindings.
SLF4J: Found binding in [jar:file:/usr/lib/spark/jars/slf4j-log4j12-1.7.30.jar!/org/slf4j/impl/StaticLoggerBinder.class]
SLF4J: Found binding in [jar:file:/usr/lib/hadoop/lib/slf4j-log4j12-1.7.25.jar!/org/slf4j/impl/StaticLoggerBinder.class]
SLF4J: See http://www.slf4j.org/codes.html#multiple_bindings for an explanation."""
        return stderr_content

    return app


def run_server(app, port, name):
    """Run a Flask app on specified port"""
    server = make_server('0.0.0.0', port, app, threaded=True)
    print(f"Starting {name} on http://localhost:{port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print(f"\nShutting down {name}")
        server.shutdown()


def main():
    """Start all mock services"""
    print("🚀 Starting Mock EMR Cluster Services...")
    print("=" * 50)

    # Create mock services
    spark_app = create_spark_history_server()
    yarn_app = create_yarn_resource_manager()
    node_app = create_node_manager()

    # Start services in separate threads
    threads = []

    # Spark History Server (port 18080)
    spark_thread = threading.Thread(
        target=run_server,
        args=(spark_app, 18080, "Spark History Server"),
        daemon=True
    )
    threads.append(spark_thread)
    spark_thread.start()

    # YARN ResourceManager (port 8088)
    yarn_thread = threading.Thread(
        target=run_server,
        args=(yarn_app, 8088, "YARN ResourceManager"),
        daemon=True
    )
    threads.append(yarn_thread)
    yarn_thread.start()

    # NodeManager (port 8042) - for container logs
    node_thread = threading.Thread(
        target=run_server,
        args=(node_app, 8042, "YARN NodeManager"),
        daemon=True
    )
    threads.append(node_thread)
    node_thread.start()

    # Give servers time to start
    time.sleep(2)

    print("\n✅ Mock EMR Cluster is running!")
    print("=" * 50)
    print("📊 Available Services:")
    print("   • Spark History Server: http://localhost:18080")
    print("   • YARN ResourceManager:  http://localhost:8088")
    print("   • YARN NodeManager:      http://localhost:8042")
    print()
    print("🔧 Update your config.yaml:")
    print('   mock_cluster:')
    print('     name: "Mock EMR Cluster"')
    print('     spark_url: "http://localhost:18080"')
    print('     yarn_url: "http://localhost:8088"')
    print('     description: "Local mock cluster for testing"')
    print()
    print("📝 Available Test Endpoints:")
    print("   • GET /api/v1/applications")
    print("   • GET /api/v1/applications/<app_id>")
    print("   • GET /api/v1/applications/<app_id>/executors")
    print("   • GET /api/v1/applications/<app_id>/jobs")
    print("   • GET /ws/v1/cluster/apps")
    print("   • GET /ws/v1/cluster/metrics")
    print("   • GET /ws/v1/cluster/nodes")
    print("   • GET /ws/v1/cluster/scheduler")
    print()
    print("Press Ctrl+C to stop all services")
    print("=" * 50)

    try:
        # Keep main thread alive
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n🛑 Stopping Mock EMR Cluster...")
        print("All services have been shut down.")


if __name__ == "__main__":
    main()