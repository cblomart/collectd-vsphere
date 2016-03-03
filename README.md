# Collectd vSphere Python plugin

Python collectd plugin to collect vsphere statistics.
The module depends on [pyvmomi](https://github.com/vmware/pyvmomi).

## Configuration

Put the script in the collectd python script path and include it.
An example configuration file is provided.

### General Option

  - Logverbose: true|false

Enable or disable verbose logging, disabled by default.

  - Interval: seconds

Interval to interogate vcenters and report values, 60 seconds by default.

  - Domain: string
  
Domain string to remove from object names (avoids long stats name), empty by default.

  - Consolidate: comma separated values in ['min', 'avg', 'max', 'sum', 'lat']
  
    - min: consolidate values per minimum in the interval
    - avg: consolidate values per average in the interval
    - max: consolidate values per maximum in the interval
    - sum: consolidate values by summing the interval
    - lat: take latest value.
    
### HostSystem and VirtualMachine

  - Metric:
  
  The metrics to collect in the form group.name.rollup (i.e.: mem.vmmemctl.average)

  The second argument is a boolean (default to false) indicating to get metric at instance level
  
### vCenter(s)

... Username, Password, Hostname
