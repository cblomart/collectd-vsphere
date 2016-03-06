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

# License

The MIT License (MIT)

Copyright (c) 2016 cblomart

Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation files (the "Software"), to deal in the Software without restriction, including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and to permit persons to whom the Software is furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
