```text
Build a EMR monitoring tool for our modellers - using pyFlask and html5, allowing them to view their completed,
submitted, accepted , failed and runinng jobs . They shoudl be able view how much resource each job is consuming, how
long it has been running, view possible errors, this is to help them manage their EMR server identify which jobs may be
hogging resources and possibly why, those jobs which are not closing the spark context alothough thei job is complete.
This is because the modeller use jupyter notebook to run their jobs and do not clean up resources, sometimes they
allocate more resources that that they need, sometimes a job is allocated all the resources at the start, but they may
not need it until the middle of the process or may not need all the resources at all. We can provide config.json or yaml
like this to list out the available
emr's: `"staging": { "name": "Staging EMR", "spark_url": "http://staging-master:18080", "yarn_url": "http://staging-master:8088", "description": "Staging EMR cluster" } `
User should be able to select his/her EMR cluster and monitor their emr, jobs, possible download application logs. Make
simple to use but all the details that will be handly for the modellers adn infra support team to help modllers
```