import collectd
from pyVim.connect import SmartConnect, Disconnect
from pyVmomi import vim, vmodl
import requests
from threading import Thread
from datetime import timedelta, datetime

VERBOSE_LOGGING = False
INTERVAL = 60
DOMAIN = ''
CONSOLIDATE= []
VCENTERS_INFO={}
METRICS_INFO={}
VCENTERS=[]
METRICS={}
METRICS_BY_ID={}

requests.packages.urllib3.disable_warnings()

def config(conf):
  global VCENTERS_INFO,VERBOSE_LOGGING,METRICS_INFO,INTERVAL,CONSOLIDATE,DOMAIN
  """get the configuration"""
  verbose("Get Configuration")
  for node in conf.children:
    key = node.key.lower()
    val = None
    if len(node.values) > 0:
      val = node.values[0]
    verbose("config %s=%s" % (key, val))
    if key == 'logverbose':
      if val == "True":
        VERBOSE_LOGGING = True
    elif key == 'interval':
      INTERVAL = int(val)
    elif key == 'domain':
      DOMAIN = val 
    elif key == 'consolidate':
      for tmp in val.split(','):
        if tmp in ['min', 'avg', 'max', 'sum', 'lat']:
          CONSOLIDATE.append(tmp)
    elif key == 'vsphere':
      VCENTERS_INFO[val]={}
      for subnode in node.children:
        subkey = subnode.key.lower()
        subval = None
        if len(subnode.values) > 0:
          subval = subnode.values[0]
        verbose("config %s.%s=%s" % (key,subkey,subval))
        VCENTERS_INFO[val][subkey]=subval
    elif key in [ 'virtualmachine', 'hostsystem'] and len(node.children) > 0:
      for subnode in node.children:
        subkey = subnode.key.lower()
        subval = None
        if len(subnode.values) > 0:
          subval = subnode.values[0]
        if subkey=='metric':
          verbose("config %s.%s=%s" % (key,subkey,subval))
          if key not in METRICS_INFO.keys():
            METRICS_INFO[key]=[]
          METRICS_INFO[key].append(subval)
  #remove invalid vcenters
  invalids = []
  for vcenter in VCENTERS_INFO.keys():
    if "username" not in VCENTERS_INFO[vcenter].keys() and "password" not in VCENTERS_INFO[vcenter].keys():
      invalid.append(vcenter)
  for invalid in invalids:
    verbose("remove invalid vcenter (no username or password): %s" % invalid)
    del(VCENTERS_INFO[invalid])
  #add hostname if not provided
  for vcenter in VCENTERS_INFO.keys():
    if "hostname" not in VCENTERS_INFO[vcenter].keys():
      VCENTERS_INFO[vcenter]["hostname"]=vcenter
  #show vcenters
  if VERBOSE_LOGGING:
    for vcenter in VCENTERS_INFO.keys():
      for key in VCENTERS_INFO[vcenter].keys():
        verbose("vcenter: %s.%s=%s" %(vcenter,key,VCENTERS_INFO[vcenter][key]))
  #show metrics
  if VERBOSE_LOGGING:
    for vitype in METRICS_INFO.keys():
        verbose("metrics: %s=%s" % (vitype, METRICS_INFO[vitype]))
  verbose("register read function")
  collectd.register_read(read,INTERVAL)


def init():
  global VCENTERS, METRICS_INFO, METRICS, METRICS_BY_ID
  """initialise the module"""
  verbose("Initilise the module")
  verbose("Identifying required metrics")
  allmetrics = []
  for vitype in METRICS_INFO.keys():
    for metric in METRICS_INFO[vitype]:
      if metric not in allmetrics:
        allmetrics.append(metric)
  verbose("Required metrics: %s" % allmetrics)
  verbose("Connecting to vcenters")
  for vcenter in VCENTERS_INFO.keys():
    if vcenter not in METRICS_BY_ID.keys():
      METRICS_BY_ID[vcenter]={}
    hostname = VCENTERS_INFO[vcenter]["hostname"]
    username = VCENTERS_INFO[vcenter]["username"]
    password = VCENTERS_INFO[vcenter]["password"]
    vc = {}
    si = None
    try:
      si = SmartConnect(host=hostname,user=username,pwd=password)
    except IOError, e:
      collectd.warning("vsphere plugin: could not connect to vcenter %s with fault '%s'" % (vcenter,e.msg))
      pass
    if not si:
      collectd.warning("vsphere plugin: could not connect to vcenter %s" % vcenter)
      continue
    vc["name"]=vcenter
    vc["si"]=si
    vc["content"]=si.RetrieveContent()
    VCENTERS.append(vc)
    verbose("connected to vcenter %s" % vcenter)
    perfManager = vc["content"].perfManager
    perf_dict = {}
    perfList = perfManager.perfCounter
    for perf in perfList:
      counter_full = "{}.{}.{}".format(perf.groupInfo.key, perf.nameInfo.key, perf.rollupType)
      if counter_full in allmetrics:
        perf_dict[counter_full] = perf.key
        METRICS_BY_ID[vcenter][perf.key]=counter_full
    if vcenter not in METRICS.keys():
      METRICS[vcenter] = {}
    for vitype in METRICS_INFO.keys():
      METRICS[vcenter][vitype]=[]
      for metric in METRICS_INFO[vitype]:
        if metric in perf_dict:
          METRICS[vcenter][vitype].append(perf_dict[metric])
        else:
          collectd.warning("vsphere plugin: Requested metric %s for %s in %s not found." % (metric, vitype, vcenter))
      verbose("metrics ids for %s in %s: %s" % (vitype,vcenter,METRICS[vcenter][vitype]))

def read(data=None):
  global VCENTERS, METRICS
  """read information from vCenters"""
  verbose("Read informations from vCenters")
  threads = []
  for vcenter in VCENTERS:
    vcname = vcenter['name']
    for vitype in METRICS[vcname].keys():
      threads.append(Thread(target=getstats, args=[vcenter,vitype,METRICS[vcname][vitype]]))
  verbose("initialised %d getstats threads." % len(threads))
  tinit = datetime.now()
  for thread in threads:
    thread.start()
  verbose("read threads started.")
  for thread in threads:
    thread.join()
  tfinish = datetime.now()
  trun = tfinish - tinit
  trun_sec = trun.total_seconds()
  verbose("read threads completed and ran for %f seconds." % trun_sec)

def shutdown():
  global VCENTERS
  """stop the module"""
  verbose("Stop the module")
  for vcenter in VCENTERS:
    Disconnect(vcenter["si"])
    verbose("disconnected from vcenter %s" % vcenter["name"])

def verbose(msg):
    """Logs a message to collectd if verbose mode"""
    if not VERBOSE_LOGGING:
        return
    collectd.info('vsphere plugin [verbose]: %s' % msg)

def getstats(vcenter,vitype,metrics):
  global INTERVAL,DOMAIN, METRICS_BY_ID,CONSOLIDATE
  si = vcenter["si"]
  content = vcenter["content"]
  perfmanager = content.perfManager
  end_time = si.CurrentTime() - timedelta(seconds=1)
  start_time = end_time - timedelta(seconds=INTERVAL)
  metricids = []
  for metric in metrics:
    metricid = vim.PerformanceManager.MetricId(counterId = metric, instance = "")
    metricids.append(metricid)
  viclass = None
  if vitype=="virtualmachine":
    viclass = vim.VirtualMachine
  elif vitype=="hostsystem":
    viclass = vim.HostSystem
  view = content.viewManager.CreateContainerView(content.rootFolder, [viclass], True)
  objs = view.view
  verbose("found %d %s." % (len(objs),vitype)) 
  #get objects name
  pc = content.propertyCollector
  filterspec = vmodl.query.PropertyCollector.FilterSpec()
  filterspec.objectSet = [vmodl.query.PropertyCollector.ObjectSpec(obj=tmp) for tmp in objs]
  filterspec.propSet = [vmodl.query.PropertyCollector.PropertySpec(type=viclass,pathSet=['name'], all=False)]
  tmp = []
  result = pc.RetrievePropertiesEx([filterspec], vim.RetrieveOptions())
  tmp += result.objects
  while result.token is not None:
    result = pc.ContinueRetrievePropertiesEx(result.token)
    tmp += result.objects
  verbose("retrieved %d names for %s objects." % (len(tmp),vitype))
  threads = []
  for item in tmp:
    query = vim.PerformanceManager.QuerySpec(intervalId=20, entity=item.obj, metricId=metricids, startTime=start_time, endTime=end_time)
    for prop in item.propSet:
      if prop.name == 'name':
        name=prop.val.replace('.'+DOMAIN,'')
    threads.append(Thread(target=getstat, args=[perfmanager,query,name,vcenter,vitype]))
    threads[-1].start()
  verbose('started %d getstat threads' % (len(threads)))
  for thread in threads:
    thread.join()

def getstat(perfmanager,query,name,vcenter,vitype):
  global METRICS_BY_ID, CONSOLIDATE, INTERVAL
  perfresults = []
  try:
    perfresults = perfmanager.QueryPerf(querySpec=[query])
  except:
    collectd.warning("vspere plugin: connection to vcenter %s issue", % (vcenter["name"]))
    init()
    return
  if perfresults is None:
    collectd.warning("vsphere plugin: no performance result for %s in %s" % (vitype, vcenter["name"]))
    return
  metricbyid = {}
  for perfresult in perfresults:
    for perf in perfresult.value:
      metric = METRICS_BY_ID[vcenter["name"]][perf.id.counterId].replace("\.[a-z]+$","")
      metric = '.'.join(metric.split('.')[:2])
      instance = perf.id.instance
      values = perf.value
      if values is None or len(values) == 0:
        collectd.warning("vsphere plugin: no values returned for %s of %s %s in %s." % (metric, vitype, name, vcenter['name']))
        continue
      value = None
      plugin_instance = "%s.%s" % (vitype,name)
      for cons in CONSOLIDATE:
        type_instance = metric
        if instance is not None and instance != "":
          type_instance += "." + instance 
        type_instance += "." + cons
        tmp = None
        if cons == "min": tmp = min(values)
        elif cons == "avg": tmp = sum(values)/len(values)
        elif cons == "max": tmp = max(values)
        elif cons == "sum": tmp = sum(values)
        elif cons == "lat": tmp = values[-1]
        verbose("got values for %s %s %s %s %s %s: %d" % (vcenter["name"], vitype, name, metric, instance, cons,  tmp))
        value = collectd.Values(type="gauge",values=[tmp],plugin_instance=plugin_instance,type_instance=type_instance,plugin="vsphere",host=vcenter["name"],time=0,interval=INTERVAL)
        value.dispatch()

collectd.register_config(config)
collectd.register_init(init)
collectd.register_shutdown(shutdown)