Create a flask, html5, python app to monitor EMR . EMR's to be monitored are in a emr_config.yaml
```markdown

```

use the spark history url to get and monitor resources used by completed for failed jobs user yarn url to get and
monitor running, acepted, submitted jobs Get the count of the task nodes * running or LOST', 'UNHEALTHY', '
DECOMMISSIONED easy to maintain,
The threshold values are mainained in the config file, see below:

```
memory_warning: 80          # Memory usage % to trigger warning
memory_critical: 90         # Memory usage % to trigger critical alert
cpu_warning: 80             # CPU usage % to trigger warning
cpu_critical: 90            # CPU usage % to trigger critical alert
unhealthy_nodes_warning: 1  # Number of unhealthy nodes for warning
unhealthy_nodes_critical: 3 # Number of unhealthy nodes for critical alert

When the cluster hits the critical threshold level for memeory, cpu and unhealthy nodes
Add to a record tot he table , this is visible on the  view port and is  saved as a pickle file.Each clustrered monitored is represented as a windows showing its characteristics and the critcal error counts.
 clear button resets the windows and clears the pickle file and monitoring starts fresh
```
